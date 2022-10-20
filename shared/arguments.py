import argparse
from datetime import date, timedelta, datetime


def arg_parser():

    argp = argparse.ArgumentParser()
    argp.add_argument(
        "-start_date",
        "-s",
        type=lambda d: datetime.strptime(d, "%Y-%m-%d"),
        default=str(date.today() - timedelta(days=30)),
        help="The day to start scraping, default today - 30 days. YYYY-mm-dd",
    )
    argp.add_argument(
        "-end_date",
        "-e",
        type=lambda d: datetime.strptime(d, "%Y-%m-%d"),
        default=str(date.today()),
        help="The day to end scraping, default today. YYYY-mm-dd",
    )
    argp.add_argument(
        "-county",
        "-c",
        type=str,
        default="hays",
        help="The name of the county, the main page for their Odyssey install will be grabbed from resources/text_county_data.csv",
    )
    argp.add_argument(
        "-ms_wait",
        "-w",
        type=int,
        default=200,
        help="Number of ms to wait between requests.",
    )
    argp.add_argument(
        "-judicial_officers",
        "-j",
        nargs="*",
        type=str,
        default=[],
        help="Judicial Officers to scrape. For example, -j 'mr. something' 'Rob, Albert'. By default, it will scrape all JOs.",
    )
    argp.add_argument(
        "-overwrite",
        "-o",
        action="store_true",
        help="Switch to overwrite cached case html, use this when updating your data from a small date range to grab new information.",
    )
    argp.add_argument(
        "-log",
        type=str,
        default="INFO",
        help="Set the level to log at.",
    )
    argp.add_argument(
        "-court_calendar_link_text",
        "-cclt",
        type=str,
        default="Court Calendar",
        help="This is the link to the Court Calendar search page at default.aspx, usually it will be 'Court Calendar', but some sites have multiple calendars e.g. Williamson",
    )
    argp.add_argument(
        "-location",
        "-l",
        type=str,
        help="'Select a location' select box on the main page. Default to the the first entry, which is usually all courts.",
    )
    argp.add_argument(
        "-test",
        "-t",
        action="store_true",
        help="If this parameter is present, the script will stop after the first case is scraped.",
    )
    argp.description = "Scrape data for list of judicial officers in date range."
    args = argp.parse_args()

    # If we are testing, make sure we are scraping things that have already been scraped
    if args.test:
        args.overwrite = True

    return argp
