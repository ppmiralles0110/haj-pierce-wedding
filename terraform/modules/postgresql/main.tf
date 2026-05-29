# =============================================================================
# terraform/modules/postgresql/main.tf
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

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${local.name_prefix}-psql"
  resource_group_name    = var.resource_group_name
  location               = var.location
  version                = "16"
  administrator_login    = var.administrator_login
  administrator_password = var.administrator_password
  storage_mb             = var.storage_mb
  sku_name               = var.sku_name

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  # Public access with firewall — for private access add vnet_integration block
  tags = local.tags

  lifecycle {
    ignore_changes = [zone, high_availability]
  }
}

# Allow Azure services (including App Service) to connect
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}
