import csv
import json
import logging
import os
import urllib.parse
from datetime import date, datetime, timedelta
from time import time
from typing import List
import azure.functions as func
import requests
from azure.storage.blob import BlobServiceClient, ContainerClient
from shared.helpers import *


def main(mytimer: func.TimerRequest) -> None:
    start_date = date.fromisoformat(
        os.getenv("start_date", (date.today() - timedelta(days=1)).isoformat())
    )
    x = os.environ
    end_date = date.fromisoformat(os.getenv("end_date", date.today().isoformat()))
    county = os.getenv("county", "hays")
    judicial_officers = os.getenv("judicial_officers")
    judicial_officers = judicial_officers.split(":") if judicial_officers else []
    ms_wait = int(os.getenv("ms_wait", "200"))
    log_level = os.getenv("log_level", "INFO")
    court_calendar_link_text = os.getenv("court_calendar_link_text", "Court Calendar")
    location = os.getenv("location")
    test = os.getenv("test", "") == "true"
    overwrite = test or (os.getenv("overwrite", "") == "true")

    scrape(
        start_date,
        end_date,
        county,
        judicial_officers,
        ms_wait,
        log_level,
        court_calendar_link_text,
        location,
        test,
        overwrite,
    )


def scrape(
    start_date: date,
    end_date: date,
    county: str,
    judicial_officers: List[str],
    ms_wait: int,
    log_level: str,
    court_calendar_link_text: str,
    location: Optional[str],
    test: bool,
    overwrite: bool,
):

    session = requests.Session()
    # allow bad ssl and turn off warnings
    session.verify = False
    requests.packages.urllib3.disable_warnings(
        requests.packages.urllib3.exceptions.InsecureRequestWarning
    )

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
                session=session,
                url=urllib.parse.urljoin(base_url, "login.aspx"),
                http_method=HTTPMethod.GET,
                ms_wait=ms_wait,
                data=data,
            )

        main_page_html = request_page_with_retry(
            session=session,
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
        session=session,
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
    # if judicial_officers param is not specified, use all of them
    if not judicial_officers:
        judicial_officers = list(judicial_officer_to_ID.keys())

    # initialize variables to time script and build a list of already scraped cases
    START_TIME = time()

    # loop through each day
    for date in (
        start_date + timedelta(n) for n in range((end_date - start_date).days + 1)
    ):
        date_string = datetime.strftime(date, "%m/%d/%Y")
        # Need underscore since azure treats slashes as new files
        date_string_underscore = datetime.strftime(date, "%m_%d_%Y")

        # loop through each judicial officer
        for JO_name in judicial_officers:
            if JO_name not in judicial_officer_to_ID:
                logger.error(
                    f"judicial officer {JO_name} not found on search page. Continuing."
                )
                continue
            JO_id = judicial_officer_to_ID[JO_name]
            logger.info(f"Searching cases on {date_string} for {JO_name}")
            # POST a request for search results
            results_page_html = request_page_with_retry(
                session=session,
                url=search_url
                if odyssey_version < 2017
                else urllib.parse.urljoin(
                    base_url, "Hearing/SearchHearings/HearingSearch"
                ),
                verification_text="Record Count"
                if odyssey_version < 2017
                else "Search Results",
                data=create_search_form_data(
                    date_string, JO_id, hidden_values, odyssey_version
                ),
                ms_wait=ms_wait,
            )
            results_soup = BeautifulSoup(results_page_html, "html.parser")

            # different process for getting case data for pre and post 2017 Odyssey versions
            if odyssey_version < 2017:
                case_urls = [
                    base_url + anchor["href"]
                    for anchor in results_soup.select('a[href^="CaseDetail"]')
                ]

                logger.info(f"{len(case_urls)} cases found")

                for case_url in case_urls:
                    case_id = case_url.split("=")[1]
                    logger.info(f"{case_id} - scraping case")
                    # make request for the case
                    case_html = request_page_with_retry(
                        session=session,
                        url=case_url,
                        verification_text="Date Filed",
                        ms_wait=ms_wait,
                    )
                    # write html case data
                    logger.info(f"{len(case_html)} response string length")
                    # write to blob
                    file_hash_dict = hash_file_contents(case_html)
                    blob_name = f"{file_hash_dict['case_no']}:{county}:{date_string_underscore}:{file_hash_dict['file_hash']}.html"
                    logger.info(f"Sending {blob_name} to blob...")
                    write_string_to_blob(file_contents=case_html, blob_name=blob_name)
                    if test:
                        logger.info("Testing, stopping after first case")
                        # bail
                        return
            else:
                # Need to POST this page to get a JSON of the search results after the initial POST
                case_list_json = request_page_with_retry(
                    session=session,
                    url=urllib.parse.urljoin(base_url, "Hearing/HearingResults/Read"),
                    verification_text="AggregateResults",
                )
                case_list_json = json.loads(case_list_json)
                logger.info(f"{case_list_json['Total']} cases found")
                for case_json in case_list_json["Data"]:
                    case_id = str(case_json["CaseId"])
                    logger.info(f"{case_id} scraping case")
                    # make request for the case
                    case_html = request_page_with_retry(
                        session=session,
                        url=urllib.parse.urljoin(base_url, "Case/CaseDetail"),
                        verification_text="Case Information",
                        ms_wait=ms_wait,
                        params={
                            "eid": case_json["EncryptedCaseId"],
                            "CaseNumber": case_json["CaseNumber"],
                        },
                    )
                    # make request for financial info
                    case_html += request_page_with_retry(
                        session=session,
                        url=urllib.parse.urljoin(
                            base_url, "Case/CaseDetail/LoadFinancialInformation"
                        ),
                        verification_text="Financial",
                        ms_wait=ms_wait,
                        params={
                            "caseId": case_json["CaseId"],
                        },
                    )
                    # write case html data
                    logger.info(f"{len(case_html)} response string length")
                    # write to blob
                    file_hash_dict = hash_file_contents(case_html)
                    blob_name = f"{file_hash_dict['case_no']}:{county}:{date_string_underscore}:{file_hash_dict['file_hash']}.html"
                    logger.info(f"Sending {blob_name} to blob...")
                    write_string_to_blob(file_contents=case_html, blob_name=blob_name)
                    if test:
                        logger.info("Testing, stopping after first case")
                        return

    logger.info(f"\nTime to run script: {round(time() - START_TIME, 2)} seconds")


if __name__ == "__main__":
    main(None)
