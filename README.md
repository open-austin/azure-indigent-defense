# Indigent Defense Azure Scraper

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

### Deployment

- Publish final app with the command `func azure functionapp publish indigent-defense-stats`. It's a good idea to verify code both locally and deployed before merging.