# Indigent Defense Data Scraper on Azure

## Development Environment Prerequisites
- Python 3.8 with pip
- Azure Function Core Tools 4
- Contact an Open Austin dev to get Azure credentials, and values for required environment variables, which go in `local.settings.json`

## Steps to run an Azure function locally
### Http trigger function ("http-scraper")
- To run the azure function app server locally, `cd` to the function app project root level (same as this README) and run this: `func start` (add `--verbose` if you like)  
- Then wait for "Host lock lease acquired by instance id #..."  
- Look for a differently-colored line that looks like this: `http-scraper: [GET,POST] http://localhost:7071/api/http-scraper` That is the URL you will use in the next step
- Send a POST request by running `curl -XPOST http://localhost:7071/api/http-scraper -d @path/to/payload.json` where payload.json contains something like the following:
#### Example payload for http-scraper

Be sure to put `judicial_officers` in [] even if you only have one. The `test` argument is not necessary but handy for development, as it causes the scraper to stop after finding and processing 1 case.

```json
{
    "start_date": "2022-11-11",
    "end_date": "2022-11-13",
    "county": "hays",
    "judicial_officers": ["Updegrove, Robert"],
    "test": true
}
```

### Message queue trigger function ("message-queue-scraper")
Azure functions time out after 5-10 min. (exact timeout is configured in `host.json`) For this reason, when the http-scraper function hits a day that has a lot of cases, it will write to a message queue instead of scraping them, thus passing the work to this second function and avoiding a timeout. 

Note that if you are working with this function, you may want to manually clear the message queue in between test runs, because it will attempt to process old messages left over from previous runs. It will try to process a message 5 times before moving it to the poison queue.

### Blob trigger function ("blob-parser")

Note that this function produces a lot of output after starting the function app, because it is continuously checking for its trigger. For this reason, you may want to disable this function during local development if it's not needed. To do this, click the 'A' in VS Code sidebar, find the function at the bottom under Workspace > Local Project > Functions, right-click on it and click Disable. You can use the same menu to re-enable it when you need it again.

### Deployment

- Publish to Azure with the command `func azure functionapp publish indigent-defense-stats-dev-function-app`. (You need to be logged in to Azure CLI.) That's our dev environment, so deploy there as much as you like; it's meant to be played with and broken. When you run the function app locally, it will still be talking to blob containers, a message queue, and a Cosmos DB on Azure, so 95% of the time local testing should be fine. However, it's a good idea to at least verify final code on Azure before opening a pull request. Changes merged into main will then be published on the prod environment.

## Devlopment via Docker

Build and run the container with `docker-compose`

```sh
docker-compose up
```

This will mount the repository as a volume in the container, so you can continue
to edit code as normal.

### Notes for Macbook M1 Users

The container runs using amd64 emulation due to Microsoft's lack of Linux
aarch64 binaries for Azure Functions Tools. Emulation causes the container to
run considerably slower than natively.

In order for the emulation to work properly, you must meet the following requirements:

- macOS 13+
  - Rosetta 2 installed
- Docker version 4.16.0+
  - Enable `Use Virtualization framework` in Docker Destkop Settings > General
  - Enable `Use rosetta for x86/amd64` in Docker Desktop Settings > Features in Development

If you see the error `Function not implemented`, this likely means you aren't
configured properly for emulation. Ensure the following:

- The above requirements are all met by your machine
- Your macOS terminal is **not** being emulated when you build & run docker compose
  - The `arch` command should print `arm64`
- That you built the container image _after_ installing everything
  - If you adjusted one of these configurations after building the image, try re-building with `docker-compose build --no-cache`
