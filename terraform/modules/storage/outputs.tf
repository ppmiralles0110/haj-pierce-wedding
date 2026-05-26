output "storage_account_name" { value = azurerm_storage_account.main.name }
output "blob_service_url"     { value = azurerm_storage_account.main.primary_blob_endpoint }
output "container_name"       { value = azurerm_storage_container.photos.name }
