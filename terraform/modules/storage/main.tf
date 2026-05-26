# =============================================================================
# terraform/modules/storage/main.tf — Blob Storage for photo gallery
# =============================================================================

locals {
  # Storage account names: 3-24 chars, lowercase + numbers only
  sa_name     = replace("${var.project_name}${var.environment}photos", "-", "")
  name_prefix = "${var.project_name}-${var.environment}"
  tags = {
    project     = "wedding-website"
    environment = var.environment
    owner       = var.owner_name
    managed_by  = "terraform"
  }
}

resource "azurerm_storage_account" "main" {
  name                     = substr(local.sa_name, 0, 24)
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # Block public blob access — App Service reads via managed identity
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"

  blob_properties {
    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["GET"]
      allowed_origins    = ["*"]
      exposed_headers    = ["*"]
      max_age_in_seconds = 3600
    }
  }

  tags = local.tags
}

resource "azurerm_storage_container" "photos" {
  name                  = "photos"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Grant App Service managed identity Storage Blob Data Contributor
resource "azurerm_role_assignment" "app_blob_contributor" {
  scope                = azurerm_storage_container.photos.resource_manager_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.app_service_principal_id
}
