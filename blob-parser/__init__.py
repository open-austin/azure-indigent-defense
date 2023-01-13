import logging
import os, csv, json, traceback
from time import time
import xxhash

from bs4 import BeautifulSoup

import azure.functions as func
from azure.cosmos import CosmosClient
from shared import pre2017, post2017
from shared.helpers import *


def main(myblob: func.InputStream):
    logging.info(
        f"Python blob trigger function processed blob \n"
        f"Name: {myblob.name}\n"
        f"Blob Size: {myblob.length} bytes"
    )

    # Get case info from file name, which looks like: case-html/15-1367CR-3:hays:12_13_2022:96316e53a9b706e0.html
    # First strip off case-html/ from beginning and .html from end of blob name
    stripped_name = myblob.name.strip("case-html/.")
    # Then split by : as delimiter
    file_info = stripped_name.split(":")
    case_num = file_info[0]
    county = file_info[1]
    case_date = file_info[2]
    html_file_hash = file_info[3][:-5]
    logging.info(
        f"Retrieved the following metadata: \n"
        f"Case Date: {case_num}\n"
        f"County: {county}\n"
        f"Date Scraped: {case_date}\n"
        f"HTML File Hash: {html_file_hash}"
    )

    # get county version year information to determine which parser to use
    base_url = odyssey_version = None
    with open(
        os.path.join(
            os.path.dirname(__file__), "..", "resources", "texas_county_data.csv"
        ),
        mode="r",
    ) as file_handle:
        csv_file = csv.DictReader(file_handle)
        for row in csv_file:
            if row["county"].lower() == county.lower():
                odyssey_version = int(row["version"].split(".")[0])
                break
    if not odyssey_version:
        raise Exception(
            "The required data to scrape this county is not in ./resources/texas_county_data.csv"
        )

    # call parser
    START_TIME = time()
    logging.info(
        f"Processing {case_num} - {county} with {odyssey_version} Odyssey parser..."
    )
    try:
        case_soup = BeautifulSoup(myblob, "html.parser", from_encoding="UTF-8")

        if odyssey_version < 2017:
            case_data = pre2017.parse(case_soup, case_num)
            logging.info("Pre 2017")
        else:
            logging.info("Post 2017")

        # initialize blob container client for sending json files to
        blob_connection_str = os.getenv("AzureCosmosStorage")
        container_name_json = os.getenv("blob_container_name_json")
        cosmos_service_client: CosmosClient = CosmosClient.from_connection_string(
            blob_connection_str
        )
        cosmos_db_client = cosmos_service_client.get_database_client("cases-json-db")
        container_client = cosmos_db_client.get_container_client(container_name_json)

        # Write case data to cosmos
        blob_id = f"{case_num}:{county}:{case_date}:{html_file_hash}"
        logging.info(f"Sending {blob_id} to {container_name_json} container...")
        case_data["id"] = blob_id
        container_client.create_item(body=case_data)

    except Exception:
        logging.error(traceback.format_exc())

    RUN_TIME = time() - START_TIME
    logging.info(f"Parsing took {RUN_TIME} seconds")
