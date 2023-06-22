# Developer Guide

## Prerequisites for Developing Locally

This section contains prerequisites to run functions locally.

### Secrets

Create a new file `local.settings.json`.

Contact an Open Austin dev to get Azure credentials and values for required environment variables.
Update the file with this information.
You need this file to deploy and test your code.

Do NOT check this file into git or share it with others, as it contains secret keys with access to our Azure account.

### Python

This project requires `python 3.9`. You **must** use this specific version.

We recommend using `pipenv` to install a specific python version for this repository.
The `Pipfile` is already checked in, so you can run `pipenv install --dev` to install all dependencies with the proper python version.

### Azure Tooling

Install [Azure Function Core Tools 4](https://github.com/Azure/azure-functions-core-tools).
Make sure to install version 4.

### Docker

**Recommended:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) if you want the docker runtime along with a nice UI.

**Alternative:** Install [Docker Engine](https://docs.docker.com/engine/install/) for only the docker runtime.

### Notes for Macbook M1 Users

Skip this section if you're not developing on a [M1 Macbook](https://support.apple.com/en-us/HT211814).

The container runs using amd64 emulation due to Microsoft's lack of Linux
aarch64 binaries for Azure Functions Tools. Emulation causes the container to
run considerably slower than natively.

In order for the emulation to work properly, you must meet the following requirements:

- macOS 13+
  - Rosetta 2 installed
- Docker version 4.16.0+
  - Enable `Use Virtualization framework` in Docker Destkop Settings > General
  - Enable `Use rosetta for x86/amd64` in Docker Desktop Settings > Features in Development

If you see the error `Function not implemented` when you run the app (below),
this likely means you aren't configured properly for emulation.
Ensure the following:

- The above requirements are all met by your machine
- Your macOS terminal is **not** being emulated when you build & run docker compose
  - The `arch` command should print `arm64`
- That you built the container image _after_ installing everything
  - If you adjusted one of these configurations after building the image, try re-building with `docker-compose build --no-cache`

## Running Functions Locally

With those prereqs installed, you can now develop locally.
First we will turn up the development environment, i.e. run all our functions locally.
Build and run the container with `docker-compose` to run the Function App (with all the functions) in your local emulator.

```sh
docker-compose up
```

This will mount the repository as a volume in the container, so you can continue
to edit code as normal. It also enables debug logging by default.

Wait for the functions to start up. Then look for a differently-colored line that looks like this

```txt
http-scraper: [GET,POST] http://localhost:7071/api/http-scraper
``` 

That is the URL you will use in the next step.

## Make Sample Requests

Now that the function is deployed, you can make a request to the function.
Run this command in a new terminal window:

```shell
curl -i -XPOST \
    "http://localhost:7071/api/http-scraper" \
    -d @testdata/payload.json
```

The request data is located in the `./testdata/payload.json` file.
In the file, the `test` argument is not necessary but handy for development,
as it causes the scraper to stop after finding and processing 1 case.

Go back to the terminal window running docker and look at the logs.
You should see the functions processing data.

## Verification

TODO(nareddyt): How do we check everything is functioning in e2e

TODO(nareddyt): Mention running unit tests when we have some

## Deployment to Azure

When you run the function app locally, it will still be talking to blob containers, a message queue, and a Cosmos DB on Azure, so 95% of the time local testing should be fine.

However, it's a good idea to at least verify final code on Azure before opening a pull request.
Changes merged into main will then be published on the prod environment.

Publish to Azure with the command `func azure functionapp publish indigent-defense-stats-dev-function-app`. 
(You need to be logged in to Azure CLI.) That's our dev environment, so deploy there as much as you like;
it's meant to be played with and broken.  
