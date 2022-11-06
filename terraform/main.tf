# Configure the Azure provider
terraform {
  required_version = ">= 1.3.3"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      # version = "=3.29.1" # last updated 10/29/2022 # You don't actually need this!
    }

    archive = {}
  }

  backend "azurerm" {
    resource_group_name  = "Indigent-Defense-Resource-Group" # "id-dev-resource-group" # "Indigent-Defense-Resource-Group"
    storage_account_name = "indigentdefense"
    container_name       = "dev-terraform-state" # can't use envrionment var here :(
    key                  = "terraform.tfstate" # "function_app/dev/tfstate" # @TODO: make env / subdirectories
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

provider "archive" {}

resource "azurerm_resource_group" "resource_group" {
  name     = "id-${var.environment}-resource-group"
  location = var.location
}

resource "azurerm_storage_account" "storage_account" {
  name                     = "id${var.environment}storage"
  resource_group_name      = azurerm_resource_group.resource_group.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_application_insights" "application_insights" {
  name                = "id-${var.environment}-application-insights"
  location            = var.location
  resource_group_name = azurerm_resource_group.resource_group.name
  application_type    = "other"
}

resource "azurerm_service_plan" "app_service_plan" {
  name                = "id-${var.environment}-app-service-plan"
  location            = var.location
  resource_group_name = azurerm_resource_group.resource_group.name
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_storage_container" "storage_container" {
  name                 = "id-function-app-src"
  storage_account_name = azurerm_storage_account.storage_account.name

}

data "archive_file" "file_scraper_function" {
  type        = "zip"
  source_dir  = "../scraper"
  output_path = "scraper.zip"
}

resource "azurerm_storage_blob" "storage_blob" {
  name                   = "${filesha256(data.archive_file.file_scraper_function.output_path)}"
  storage_account_name   = azurerm_storage_account.storage_account.name
  storage_container_name = azurerm_storage_container.storage_container.name
  type                   = "Block"
  source                 = data.archive_file.file_scraper_function.output_path
}

data "azurerm_storage_account_blob_container_sas" "storage_account_blob_container_sas" {
  connection_string = azurerm_storage_account.storage_account.primary_connection_string
  container_name    = azurerm_storage_container.storage_container.name

  start  = "2022-01-01T00:00:00Z"
  expiry = "2025-01-01T00:00:00Z"

  permissions {
    read   = true
    add    = false
    create = false
    write  = false
    delete = false
    list   = false
  }
}

resource "azurerm_linux_function_app" "function_app" {
  name                = "id-${var.environment}-function-app"
  resource_group_name = azurerm_resource_group.resource_group.name
  location            = var.location
  service_plan_id     = azurerm_service_plan.app_service_plan.id

  builtin_logging_enabled     = true
  functions_extension_version = "~4"
  daily_memory_time_quota     = 100000

  storage_account_name       = azurerm_storage_account.storage_account.name
  storage_account_access_key = azurerm_storage_account.storage_account.primary_access_key

  # this is where we'll merge all of the environment variables
  app_settings = {
   "WEBSITE_RUN_FROM_PACKAGE" = "https://${azurerm_storage_account.storage_account.name}.blob.core.windows.net/${azurerm_storage_container.storage_container.name}/${azurerm_storage_blob.storage_blob.name}${data.azurerm_storage_account_blob_container_sas.storage_account_blob_container_sas.sas}",
  }

  # https://iddevstorage.blob.core.windows.net/id-function-app-src/abb30b9f0181f8e6dd6ff94bd0d9cb7494f7345f68b09bd1d50706e2d59fcc92.zip?sv=2018-11-09&sr=c&st=2022-01-01T00%3A00%3A00Z&se=2025-01-01T00%3A00%3A00Z&sp=r&spr=https&sig=df6%2BWo55D5HsDBDIXM3NBmbOCAkCDQZMjIj8odynVZg%3D

  site_config {
    application_insights_connection_string = azurerm_application_insights.application_insights.connection_string
    application_insights_key               = azurerm_application_insights.application_insights.instrumentation_key
    application_stack {
      python_version = "3.8"
    }
  }

  # lifecycle {
  #   ignore_changes = [
  #     app_settings["WEBSITE_RUN_FROM_PACKAGE"],
  #   ]
  # }
}

resource "azurerm_function_app_function" "hays" {
  name            = "hays"
  function_app_id = azurerm_linux_function_app.function_app.id
  language        = "Python"
  test_data = jsonencode({
    "judicial_officers" = ["Updegrove, Robert"]
  })
  config_json = jsonencode({
    "bindings" = [
      {
        "authLevel" = "function"
        "direction" = "in"
        "methods" = [
          "get",
          "post",
        ]
        "name" = "mytimer"
        "type" = "httpTrigger"
      },
      {
        "direction" = "out"
        "name"      = "$return"
        "type"      = "http"
      },
    ]
  })
}

# end_date
# county
# judicial_officers
# ms_wait
# log_level
# court_calendar_link_text
# location
# test
# overwrite

