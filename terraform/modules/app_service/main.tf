# =============================================================================
# terraform/modules/app_service/main.tf
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags = {
    project     = "wedding-website"
    environment = var.environment
    owner       = var.owner_name
    managed_by  = "terraform"
  }
}

resource "azurerm_service_plan" "main" {
  name                = "${local.name_prefix}-plan"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku_name
  tags                = local.tags
}

resource "azurerm_linux_web_app" "main" {
  name                = "${local.name_prefix}-app"
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.main.id

  https_only = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on        = var.sku_name != "F1" && var.sku_name != "D1"
    ftps_state       = "Disabled"
    http2_enabled    = true
    minimum_tls_version = "1.2"

    application_stack {
      python_version = "3.12"
    }

    # Startup command
    app_command_line = "gunicorn --bind=0.0.0.0:8000 --timeout=120 --workers=2 wsgi:application"
  }

  app_settings = var.app_settings

  logs {
    detailed_error_messages = true
    failed_request_tracing  = true

    http_logs {
      retention_in_days = 7
    }
  }

  tags = local.tags
}

# Grant the App Service identity access to Key Vault
resource "azurerm_key_vault_access_policy" "app_service" {
  key_vault_id = var.key_vault_id
  tenant_id    = azurerm_linux_web_app.main.identity[0].tenant_id
  object_id    = azurerm_linux_web_app.main.identity[0].principal_id

  secret_permissions = ["Get", "List"]
}
