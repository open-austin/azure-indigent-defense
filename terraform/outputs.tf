output "function_app_name" {
  value       = azurerm_linux_function_app.function_app.name
  description = "Deployed function 'app name'"
}

output "function_app_default_hostname" {
  value       = azurerm_function_app_function.hays.invocation_url
  description = "Deployed function 'app hostname'"
}