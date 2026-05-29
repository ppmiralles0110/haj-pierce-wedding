output "endpoint"           { value = azurerm_cognitive_account.openai.endpoint }
output "openai_account_id"  { value = azurerm_cognitive_account.openai.id }
output "deployment_name"    { value = azurerm_cognitive_deployment.gpt5_mini.name }
