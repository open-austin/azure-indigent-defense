# Indigent Defense Azure Scraper

(and eventually parser.)

## Steps to run an Azure function locally

### Timer trigger function ("scraper")
- Put environment variables in `local.settings.json` (ask an Open Austin dev for this info)
- To run the azure function app server locally, `cd` to the function app project root level (same as this README) and run this: `func start --verbose`  
- Then wait for "Host lock lease acquired by instance id #..."  
- Then, to get the timer trigger function to execute on demand, navigate to Azure section of VS Code ("A" logo in sidebar), right click on `scraper` function (under local workspace on bottom) and select "Execute Now" 
- Output should show in the same terminal where you ran `func start` 

### Http trigger function ("http-scraper")
- First, it is recommended to disable the timer trigger function if you are only working with the http trigger function. To do this, navigate to Azure section of VS Code ("A" logo in sidebar), right click on `scraper` function (under local workspace on bottom) and select "Disable"
- To run the azure function app server locally, `cd` to the function app project root level (same as this README) and run this: `func start --verbose`  
- Then wait for "Host lock lease acquired by instance id #..."  
- Look for a differently-colored line that looks like this: `http-scraper: [GET,POST] http://localhost:7071/api/http-scraper` That is the URL you will use in the next step
- Send a POST request by running `curl -XPOST http://localhost:7071/api/http-scraper -d @path/to/payload.json` where payload.json contains something like the following:
#### Example payload for http-scraper

Be sure to put `judicial_officers` in [] even if you only have one.

```json
{
    "start_date": "2022-11-11",
    "end_date": "2022-11-13",
    "county": "hays",
    "judicial_officers": ["Updegrove, Robert"]
}
```