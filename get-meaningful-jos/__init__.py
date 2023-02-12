import logging, os, csv, urllib.parse, json
from typing import List, Optional
from datetime import datetime, timedelta, date
from time import time

from requests import *
from bs4 import BeautifulSoup
import azure.functions as func

from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.identity import DefaultAzureCredential

from shared.helpers import *


container_name_html = os.getenv("blob_container_name_html")
SESSION = None
CONTAINER_CLIENT_HTML = None

def main(req: func.HttpRequest, msg: func.Out[List[str]]) -> func.HttpResponse:
    logging.info("Python HTTP trigger function received a request.")
    global container_name_html

    req_body = req.get_json()
    # Get parameters from request payload
    # TODO - seeing as how this will be running in a context where we want to keep time < 2-15 min,
    # and run many in parallel,
    # do we still need the 'back-up' start/end times (based off today) and 'backup' county ("hays")?
    # May be better to simple require certain parameters?
    # Are we worried about Odyssey noticing a ton of parallel requests?

    # Number of days back to check for JOs
    daysback = 1826

    start_date = date.fromisoformat(
        req_body.get("start_date", (date.today() - timedelta(days=1)).isoformat())
    )
    end_date = date.fromisoformat(req_body.get("end_date", date.today().isoformat()))
    county = req_body.get("county", "hays")
    judicial_officers = req_body.get("judicial_officers", [])
    ms_wait = int(req_body.get("ms_wait", "200"))
    log_level = req_body.get("log_level", "INFO")
    court_calendar_link_text = req_body.get(
        "court_calendar_link_text", "Court Calendar"
    )
    location = req_body.get("location", None)
    test = bool(req_body.get("test", None))
    overwrite = test or bool(req_body.get("overwrite", None))

    # get size of case batches
    cases_batch_size = int(os.getenv("cases_batch_size"))

    # Get/initialize blob container client for sending html files to
    global CONTAINER_CLIENT_HTML
    if CONTAINER_CLIENT_HTML == None:
        CONTAINER_CLIENT_HTML = initialize_blob_container_client(container_name_html)

    # Get/initialize session
    global SESSION
    if SESSION == None:
        SESSION = initialize_session()
    
    # initialize logger
    logger = logging.getLogger(name="pid: " + str(os.getpid()))
    logging.basicConfig()
    logging.root.setLevel(level=log_level)

    # make cache directories if not present
    case_html_path = os.path.join(
        os.path.dirname(__file__), "..", "data", county, "case_html"
    )
    os.makedirs(case_html_path, exist_ok=True)

    # get county portal and version year information from csv file
    base_url = odyssey_version = notes = None
    with open(
        os.path.join(
            os.path.dirname(__file__), "..", "resources", "texas_county_data.csv"
        ),
        mode="r",
    ) as file_handle:
        csv_file = csv.DictReader(file_handle)
        for row in csv_file:
            if row["county"].lower() == county.lower():
                base_url = row["portal"]
                # add trailing slash if not present, otherwise urljoin breaks
                if base_url[-1] != "/":
                    base_url += "/"
                logger.info(f"{base_url} - scraping this url")
                odyssey_version = int(row["version"].split(".")[0])
                notes = row["notes"]
                break
    if not base_url or not odyssey_version:
        raise Exception(
            "The required data to scrape this county is not in ./resources/texas_county_data.csv"
        )

    # if odyssey_version < 2017, scrape main page first to get necessary data
    if odyssey_version < 2017:
        # some sites have a public guest login that must be used
        if "PUBLICLOGIN#" in notes:
            userpass = notes.split("#")[1].split("/")

            data = {
                "UserName": userpass[0],
                "Password": userpass[1],
                "ValidateUser": "1",
                "dbKeyAuth": "Justice",
                "SignOn": "Sign On",
            }

            response = request_page_with_retry(
                session=SESSION,
                url=urllib.parse.urljoin(base_url, "login.aspx"),
                http_method=HTTPMethod.GET,
                ms_wait=ms_wait,
                data=data,
            )

        main_page_html = request_page_with_retry(
            session=SESSION,
            url=base_url,
            verification_text="ssSearchHyperlink",
            http_method=HTTPMethod.GET,
            ms_wait=ms_wait,
        )
        main_soup = BeautifulSoup(main_page_html, "html.parser")
        # build url for court calendar
        search_page_id = None
        for link in main_soup.select("a.ssSearchHyperlink"):
            if court_calendar_link_text in link.text:
                search_page_id = link["href"].split("?ID=")[1].split("'")[0]
        if not search_page_id:
            write_debug_and_quit(
                verification_text="Court Calendar link",
                page_text=main_page_html,
            )
        search_url = base_url + "Search.aspx?ID=" + search_page_id

    # hit the search page to gather initial data
    search_page_html = request_page_with_retry(
        session=SESSION,
        url=search_url
        if odyssey_version < 2017
        else urllib.parse.urljoin(base_url, "Home/Dashboard/26"),
        verification_text="Court Calendar"
        if odyssey_version < 2017
        else "SearchCriteria.SelectedCourt",
        http_method=HTTPMethod.GET,
        ms_wait=ms_wait,
    )
    search_soup = BeautifulSoup(search_page_html, "html.parser")

    # we need these hidden values to POST a search
    hidden_values = {
        hidden["name"]: hidden["value"]
        for hidden in search_soup.select('input[type="hidden"]')
        if hidden.has_attr("name")
    }
    # get nodedesc and nodeid information from main page location select box
    if odyssey_version < 2017:
        location_option = main_soup.findAll("option")[0]
        logger.info(f"location: {location_option.text}")
        hidden_values.update({"NodeDesc": location, "NodeID": location_option["value"]})
    else:
        hidden_values["SearchCriteria.SelectedCourt"] = hidden_values[
            "Settings.DefaultLocation"
        ]  # TODO: Search in default court. Might need to add further logic later to loop through courts.

    # get a list of JOs to their IDs from the search page
    judicial_officer_to_ID = {
        option.text: option["value"]
        for option in search_soup.select(
            'select[labelname="Judicial Officer:"] > option'
            if odyssey_version < 2017
            else 'select[id="selHSJudicialOfficer"] > option'
        )
        if option.text
    }
    # Check all judicial officers
    judicial_officers = list(judicial_officer_to_ID.keys())

    # initialize variables to time script and build a list of already scraped cases
    START_TIME = time()
    today = datetime.strftime(datetime.today(), "%Y-%m-%d"),

    meaningful_jos = []
    # loop through each judicial officer
    for JO_name in judicial_officers:
        if JO_name not in judicial_officer_to_ID:
            logger.error(
                f"judicial officer {JO_name} not found on search page. Continuing."
            )
            continue
        JO_id = judicial_officer_to_ID[JO_name]
        logger.info(f"Searching cases on for {JO_name}")
        # POST a request for search results
        results_page_html = request_page_with_retry(
            session=SESSION,
            url=search_url
            if odyssey_version < 2017
            else urllib.parse.urljoin(base_url, "Hearing/SearchHearings/HearingSearch"),
            verification_text="Record Count"
            if odyssey_version < 2017
            else "Search Results",
            data=create_search_form_data(
                today,
                JO_id,
                hidden_values,
                odyssey_version,
                daysback=daysback,
            ),
            ms_wait=ms_wait,
        )
        results_soup = BeautifulSoup(results_page_html, "html.parser")
        if odyssey_version < 2017:
            case_urls = [
                base_url + anchor["href"]
                for anchor in results_soup.select('a[href^="CaseDetail"]')
            ]

            logger.info(f"{len(case_urls)} cases found for {JO_name}")

            # Search maxes out at 200, so only judges with >200 are "meaningful"
            if len(case_urls) >= 200:
                meaningful_jos.append(JO_name)

    meaningful_jo_str = "\n".join(meaningful_jos)
    blob_name = f"meaningful_jos_{today}.txt"
    write_string_to_blob(file_contents=meaningful_jo_str, blob_name=blob_name, container_client=CONTAINER_CLIENT_HTML, container_name=container_name_html)

    logger.info(f"\nTime to run script: {round(time() - START_TIME, 2)} seconds")

    print("Returning response...")
    return func.HttpResponse(
        f"Finished scraping meaningful JOs",
        status_code=200,
    )