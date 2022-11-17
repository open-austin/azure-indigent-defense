

def write_to_blob(file, case_id):
    blob_connection_str = os.getenv("blob_connection_str")
    blob_container_name = os.getenv("blob_container_name")
    blob_service_client: BlobServiceClient = BlobServiceClient.from_connection_string(
        blob_connection_str
    )
    container = blob_service_client.get_container_client(blob_container_name)

    with open(file, "rb") as data:
        container.upload_blob(name=case_id, data=data)