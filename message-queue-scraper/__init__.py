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


def main(msg: func.QueueMessage) -> None:
    queue_message = msg.get_body().decode('utf-8')
    logging.info('Python queue trigger function processed a queue item: %s',
                 queue_message)

    # deserialize json message
    # message has this form: { "case-urls": [str, str], "scrape-params": {"search-url": str, "base-url": str, .... } }
    message_dict = json.loads(queue_message)
    case_urls = message_dict["case-urls"]
    base_url = message_dict["scrape-params"]["base-url"]
    county = message_dict["scrape-params"]["county"]
    odyssey_version = message_dict["scrape-params"]["odyssey-version"]
    search_url = message_dict["scrape-params"]["search-url"]
    notes = message_dict["scrape-params"]["notes"]
    date_string = message_dict["scrape-params"]["date-string"]
    date_string_underscore = date_string.replace("/", "_")
    JO_id = message_dict["scrape-params"]["JO-id"]
    # is this always going to work?
    hidden_values = message_dict["scrape-params"]["hidden-values"]
    # # TODO - get these from message
    # ms_wait = 200
    # location = None
    ms_wait = message_dict["scrape-params"]["ms-wait"]
    location = message_dict["scrape-params"]["location"]
    court_calendar_link_text = "Court Calendar"

    # initialize session
    session = requests.Session()
    # allow bad ssl and turn off warnings
    session.verify = False
    requests.packages.urllib3.disable_warnings(
        requests.packages.urllib3.exceptions.InsecureRequestWarning
    )

    # initialize blob container client for sending html files to
    blob_connection_str = os.getenv("AzureWebJobsStorage")
    container_name_html = os.getenv("blob_container_name_html")
    blob_service_client: BlobServiceClient = BlobServiceClient.from_connection_string(
        blob_connection_str
    )
    container_client = blob_service_client.get_container_client(container_name_html)

    # The following 2 searches' results are not actually used in this function -- only here because 
    # this search is a necessary preliminary step to get the case URLs to load.
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

    # actual scraping of case urls passed in message
    for case_url in case_urls:
        case_id = case_url.split("=")[1]
        logging.info(f"{case_id} - scraping case")
        # make request for the case
        case_html = request_page_with_retry(
            session=session,
            url=case_url,
            verification_text="Date Filed"
        )

        # write html case data
        logging.info(f"{len(case_html)} response string length")
        file_hash_dict = hash_case_html(case_html)
        blob_name = f"{file_hash_dict['case_no']}:{county}:{date_string_underscore}:{file_hash_dict['file_hash']}.html"
        logging.info(f"Sending {blob_name} to {container_name_html} container...")
        write_string_to_blob(file_contents=case_html, blob_name=blob_name, container_client=container_client, container_name=container_name_html)

    logging.info(f"Successfully scraped batch of cases for {JO_id} -- {date_string}")