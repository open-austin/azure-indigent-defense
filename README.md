# Indigent Defense Azure Scraper

(and eventually parser.)

### Steps to run locally

- Put environment variables in `local.settings.json` (ask an Open Austin dev for this info)
- To run the azure function app server locally, `cd` to the function app level (same as this README) and run this: `func start --verbose`  
- Then wait for "Host lock lease acquired by instance id #..."  
- Then, to get the timer trigger function to execute on demand, navigate to Azure section of VS Code ("A" logo in sidebar), right click on `scraper` function (under local workspace on bottom) and select "Execute Now" 
- Output should show in the same terminal where you ran `func start` 