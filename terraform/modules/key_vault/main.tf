# =============================================================================
# terraform/modules/key_vault/main.tf
# =============================================================================

data "azurerm_client_config" "current" {}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags = {
    project     = "wedding-website"
    environment = var.environment
    owner       = var.owner_name
    managed_by  = "terraform"
  }
}

resource "azurerm_key_vault" "main" {
  name                       = "${local.name_prefix}-kv"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false  # Set true for production hardening

  # Allow App Service to read secrets (policy added in app_service module)
  # Allow Terraform deployer (this service principal) to manage secrets
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get", "List", "Set", "Delete", "Purge", "Recover"
    ]
  }

  tags = local.tags
}
