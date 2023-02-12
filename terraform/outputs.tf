output "function_app_name" {
  value       = azurerm_linux_function_app.function_app.name
  description = "Deployed function app name"
}

output "function_app_default_hostname" {
  value       = azurerm_linux_function_app.function_app.default_hostname
  description = "Deployed function app hostname"
}

output "function_app_storage_acct_connection_str" {
  value       = azurerm_storage_account.func_storage_account.primary_connection_string
  description = "For local.settings.json - AzureWebJobsStorage"
  sensitive   = true
}

output "function_app_insights_instrumentation_key" {
  value       = azurerm_application_insights.application_insights.instrumentation_key
  description = "For local.settings.json - APPINSIGHTS_INSTRUMENTATIONKEY"
  sensitive   = true
}

output "function_app_insights_connection_str" {
  value       = azurerm_application_insights.application_insights.connection_string
  description = "For local.settings.json - APPLICATIONINSIGHTS_CONNECTION_STRING"
  sensitive   = true
}

output "scrape_data_storage_acct_connection_str" {
  value       = azurerm_storage_account.scrape_data_storage_account.primary_connection_string
  description = "For local.settings.json - ScrapeDataStorage"
  sensitive   = true
}

output "cosmosdb_connection_strings" {
   value = azurerm_cosmosdb_account.cosmos_acct.connection_strings
   description = "For local.settings.json - AzureCosmosStorage"
   sensitive   = true
}