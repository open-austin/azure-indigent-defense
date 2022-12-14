# import logging
# import azure.functions as func
# from azure.keyvault.secrets import SecretClient
# from azure.identity from ClientSecretCredential
 
# def main(req: func.HttpRequest) -> func.HttpRequest:
#     logging.info("trigger message here")
 
#     key_vault_url = "key vault url"
#     secret_client = SecretClient(vault_url=key_vault_url, credential=None)
#     credential = ClientSecretCredential(
#         "tenant_id",
#         "client_id",
#         "client_secrets"
#     )
#     secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
 
#     token = credential.get_token()
#     secret_client.set_secret("mysecret", "secret_val", token=token)
 
#     secret = secret_client.get_secret("my_secret")
 
#     """
#     work
#     """
#     return None