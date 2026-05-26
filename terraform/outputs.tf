# =============================================================================
# terraform/outputs.tf — Key outputs after apply
# =============================================================================

output "app_service_default_hostname" {
  description = "Default App Service hostname (azurewebsites.net)"
  value       = module.app_service.default_hostname
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = module.key_vault.vault_uri
}

output "postgresql_fqdn" {
  description = "FQDN of the PostgreSQL Flexible Server"
  value       = module.postgresql.server_fqdn
  sensitive   = true
}

output "storage_account_name" {
  description = "Name of the Blob Storage account for photos"
  value       = module.storage.storage_account_name
}

output "storage_container_name" {
  description = "Name of the photo blob container"
  value       = module.storage.container_name
}

output "app_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = module.monitoring.instrumentation_key
  sensitive   = true
}

output "app_insights_connection_string" {
  description = "Application Insights connection string"
  value       = module.monitoring.connection_string
  sensitive   = true
}

output "openai_endpoint" {
  description = "Azure OpenAI service endpoint"
  value       = module.ai_foundry.endpoint
}

output "front_door_endpoint_hostname" {
  description = "Front Door endpoint hostname (null if Front Door not deployed)"
  value       = module.front_door.endpoint_hostname
}
