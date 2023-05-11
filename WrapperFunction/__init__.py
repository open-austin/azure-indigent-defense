import logging

import azure.functions as func
from fastapi.middleware.cors import CORSMiddleware


from fastapi import FastAPI # Main API application
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/sample")
async def index():
    return {
        "info": "Try /hello/Lucia for parameterized route.",
    }


@app.get("/hello/{name}")
async def get_name(name: str):
    return {
        "name": name,
    }


async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    return await func.AsgiMiddleware(app).handle_async(req, context)
