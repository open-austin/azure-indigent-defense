terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.43.0"
    }

    random = {
      source  = "hashicorp/random"
      version = ">= 3.1"
    }
  }

  required_version = ">= 1.1.0"

  # We are using a remote backend so our distributed team can share terraform state. 
  # Need to pass in container name, key from command line when running terraform init.
  # 1. Be logged in to Azure CLI
  # 2. Set env variables:
  #  export IDS_tfstate_container_name="terraform-state-dev"
  #  export IDS_tfstate_file_name="dev.terraform.tfstate"
  # 3. Run command:
  #   terraform init \
  #   -backend-config="container_name=$IDS_tfstate_container_name" \
  #   -backend-config="key=$IDS_tfstate_file_name"
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "terraformstatestorageids"
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "resource_group" {
  name     = "${var.project}-${var.environment}-resource-group"
  location = var.location
}

# Random string needed for storage account names since they need to be globally unique
resource "random_string" "random" {
  length  = 5
  special = false
  upper   = false
}

# Cosmos DB resources
resource "azurerm_cosmosdb_account" "cosmos_acct" {
  name                      = "${var.project}-${var.environment}-cosmos-acct"
  location                  = azurerm_resource_group.resource_group.location
  resource_group_name       = azurerm_resource_group.resource_group.name
  offer_type                = "Standard"
  kind                      = "GlobalDocumentDB"
  enable_automatic_failover = var.environment == "prod" ? true : false
  capabilities {
    name = "EnableServerless"
  }
  geo_location {
    location          = azurerm_resource_group.resource_group.location
    failover_priority = 0
  }
  consistency_policy {
    consistency_level       = "BoundedStaleness"
    max_interval_in_seconds = 300
    max_staleness_prefix    = 100000
  }
  depends_on = [
    azurerm_resource_group.resource_group
  ]
}

resource "azurerm_cosmosdb_sql_database" "cosmos_db" {
  name                = "cases-json-db"
  resource_group_name = azurerm_resource_group.resource_group.name
  account_name        = azurerm_cosmosdb_account.cosmos_acct.name
}

resource "azurerm_cosmosdb_sql_container" "cosmos_json_container" {
  name                  = "case-json"
  resource_group_name   = azurerm_resource_group.resource_group.name
  account_name          = azurerm_cosmosdb_account.cosmos_acct.name
  database_name         = azurerm_cosmosdb_sql_database.cosmos_db.name
  partition_key_path    = "/definition/id"
  partition_key_version = 1
}

# Raw html, message queue resources
# Azure docs recommend using separate storage accounts for function app backend vs.
# for other resources that the function app interacts with
resource "azurerm_storage_account" "scrape_data_storage_account" {
  name                     = "${var.proj_prefix}${var.environment}data${random_string.random.result}"
  resource_group_name      = azurerm_resource_group.resource_group.name
  location                 = azurerm_resource_group.resource_group.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "html_container" {
  name                  = "case-html"
  storage_account_name  = azurerm_storage_account.scrape_data_storage_account.name
  container_access_type = "private"
}

resource "azurerm_storage_queue" "cases_queue" {
  name                 = "cases-to-scrape"
  storage_account_name = azurerm_storage_account.scrape_data_storage_account.name
}

# Function app resources
resource "azurerm_storage_account" "func_storage_account" {
  name                     = "${var.proj_prefix}${var.environment}func${random_string.random.result}"
  resource_group_name      = azurerm_resource_group.resource_group.name
  location                 = azurerm_resource_group.resource_group.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_application_insights" "application_insights" {
  name                = "${var.project}-${var.environment}-app-insights"
  location            = azurerm_resource_group.resource_group.location
  resource_group_name = azurerm_resource_group.resource_group.name
  application_type    = "other"
}

resource "azurerm_service_plan" "app_service_plan" {
  name                = "${var.project}-${var.environment}-app-service-plan"
  location            = azurerm_resource_group.resource_group.location
  resource_group_name = azurerm_resource_group.resource_group.name
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_linux_function_app" "function_app" {
  name                    = "${var.project}-${var.environment}-function-app"
  resource_group_name     = azurerm_resource_group.resource_group.name
  location                = azurerm_resource_group.resource_group.location
  service_plan_id         = azurerm_service_plan.app_service_plan.id

  builtin_logging_enabled = true
  functions_extension_version = "~4"
  # daily_memory_time_quota = 100000 # TODO - maybe conditionally add a quota for dev/test environments?

  storage_account_name       = azurerm_storage_account.func_storage_account.name
  storage_account_access_key = azurerm_storage_account.func_storage_account.primary_access_key

  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE" = "", # blank bc we are not deploying app changes with terraform
    "ScrapeDataStorage" = azurerm_storage_account.scrape_data_storage_account.primary_connection_string,
    "blob_container_name_html" = azurerm_storage_container.html_container.name,
    "cases_batch_size" = 50,
    "AzureCosmosStorage" = azurerm_cosmosdb_account.cosmos_acct.connection_strings[0],
    "blob_container_name_json" = azurerm_cosmosdb_sql_container.cosmos_json_container.name
  }

  site_config {
    application_insights_connection_string = azurerm_application_insights.application_insights.connection_string
    application_insights_key               = azurerm_application_insights.application_insights.instrumentation_key
    application_stack {
      python_version = "3.9"
    }
  }

  depends_on = [
    azurerm_application_insights.application_insights,
    azurerm_service_plan.app_service_plan,
    azurerm_storage_account.scrape_data_storage_account,
    azurerm_cosmosdb_account.cosmos_acct
  ]

  lifecycle {
    ignore_changes = [
      app_settings["WEBSITE_RUN_FROM_PACKAGE"], # bc we are not deploying app changes with terraform
    ]
  }
}