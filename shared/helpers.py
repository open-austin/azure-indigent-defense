import os, sys
import requests
from time import sleep
import logging
from typing import Dict, Optional, Tuple, Literal
from enum import Enum
import xxhash
from bs4 import BeautifulSoup
from azure.storage.blob import BlobServiceClient


def write_debug_and_quit(
    page_text: str, verification_text: Optional[str] = None
) -> None:
    logging.error(
        (
            f"{verification_text} could not be found in page."
            if verification_text
            else "Failed to load page."
        )
        + f" Aborting. Writing /data/debug.html with response. May not be HTML."
    )
    with open(os.path.join("data", "debug.html"), "w") as file_handle:
        file_handle.write(page_text)
    sys.exit(1)


# helper function to make form data
def create_search_form_data(
    date: str, JO_id: str, hidden_values: Dict[str, str], odyssey_version: int
) -> Dict[str, str]:
    form_data = {}
    form_data.update(hidden_values)
    if odyssey_version < 2017:
        form_data.update(
            {
                "SearchBy": "3",
                "cboJudOffc": JO_id,
                "DateSettingOnAfter": date,
                "DateSettingOnBefore": date,
                "SearchType": "JUDOFFC",  # Search by Judicial Officer
                "SearchMode": "JUDOFFC",
                "CaseCategories": "CR",  # "CR,CV,FAM,PR" criminal, civil, family, probate and mental health - these are the options
            }
        )
    else:
        form_data.update(
            {
                "SearchCriteria.SelectedHearingType": "Criminal Hearing Types",
                "SearchCriteria.SearchByType": "JudicialOfficer",
                "SearchCriteria.SelectedJudicialOfficer": JO_id,
                "SearchCriteria.DateFrom": date,
                "SearchCriteria.DateTo": date,
            }
        )
    return form_data


class HTTPMethod(Enum):
    POST: int = 1
    GET: int = 2


def request_page_with_retry(
    session: requests.Session,
    url: str,
    verification_text: Optional[str] = None,
    http_method: Literal[HTTPMethod.POST, HTTPMethod.GET] = HTTPMethod.POST,
    params: Dict[str, str] = {},
    data: Optional[Dict[str, str]] = None,
    max_retries: int = 5,
    ms_wait: str = 200,
) -> Tuple[str, bool]:
    response = None
    for i in range(max_retries):
        sleep(ms_wait / 1000 * (i + 1))
        failed = False
        try:
            if http_method == HTTPMethod.POST:
                if not data:
                    response = session.post(url, params=params)
                else:
                    response = session.post(url, data=data, params=params)
            elif http_method == HTTPMethod.GET:
                if not data:
                    response = session.get(url, params=params)
                else:
                    response = session.get(url, data=data, params=params)
            response.raise_for_status()
            if verification_text:
                if verification_text not in response.text:
                    failed = True
                    logging.error(
                        f"Verification text {verification_text} not in response"
                    )
        except requests.RequestException as e:
            logging.exception(f"Failed to get url {url}, try {i}")
            failed = True
        if failed:
            write_debug_and_quit(
                verification_text=verification_text,
                page_text=response.text,
            )
    return response.text


# Moving this outside of the function so we don't have to reconnect each time...
# Maybe there's a better way to do this?
blob_connection_str = os.getenv("blob_connection_str")
container_name = os.getenv("blob_container_name")
blob_service_client: BlobServiceClient = BlobServiceClient.from_connection_string(
    blob_connection_str
)
container_client = blob_service_client.get_container_client(container_name)


def write_string_to_blob(
    file_contents: str, blob_name: str, overwrite: bool = False
) -> bool:
    """Write a string to a blob file. If

    Args:
        file_contents (str): String to be written as body of the file
        blob_name (str): name of the file
        overwrite (bool, optional): If False, checks if file exists first. Defaults to False.
    Returns:
        bool: True if file written, False if not written
    """
    blob_client = container_client.get_blob_client(blob_name)
    if blob_client.exists() and not overwrite:
        logging.info(msg=f"{blob_name} already exists in {container_name}, skipping.")
        return False
    blob_client.upload_blob(data=file_contents)
    return True


def hash_file_contents(file_contents: str) -> str:
    """Return the xxhash of a given string, cleaned to relevant parts

    Args:
        file_contents (str): String of the file to be hashed

    Returns:
        str: hash value of relevant contents
    """
    soup = BeautifulSoup(file_contents)
    body = soup.find("body")
    balance_table = body.find_all("table")[-1]
    if "Balance Due" in balance_table.text:
        balance_table.decompose()
    relevant_file_str = str(body)
    filehash = xxhash.xxh64(relevant_file_str).hexdigest()
    return filehash
