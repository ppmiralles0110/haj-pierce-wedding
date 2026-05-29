# =============================================================================
# terraform/main.tf — Root module: orchestrates all sub-modules
# =============================================================================

# ---------------------------------------------------------------------------
# Resource Group
# ---------------------------------------------------------------------------
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location

  tags = {
    project    = "wedding-website"
    environment = var.environment
    owner      = var.owner_name
    managed_by = "terraform"
  }
}

# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------

module "key_vault" {
  source              = "./modules/key_vault"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  project_name        = var.project_name
  environment         = var.environment
  owner_name          = var.owner_name
  app_service_principal_id = module.app_service.principal_id
}

module "monitoring" {
  source              = "./modules/monitoring"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  project_name        = var.project_name
  environment         = var.environment
  owner_name          = var.owner_name
}

module "storage" {
  source              = "./modules/storage"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  project_name        = var.project_name
  environment         = var.environment
  owner_name          = var.owner_name
  app_service_principal_id = module.app_service.principal_id
}

module "postgresql" {
  source                = "./modules/postgresql"
  resource_group_name   = azurerm_resource_group.main.name
  location              = var.location
  project_name          = var.project_name
  environment           = var.environment
  owner_name            = var.owner_name
  administrator_login   = var.db_username
  administrator_password = var.db_password
  database_name         = var.db_name
  sku_name              = var.postgresql_sku_name
  storage_mb            = var.postgresql_storage_mb
}

module "ai_foundry" {
  source              = "./modules/ai_foundry"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.ai_location  # Sweden Central for GPT-4o-mini quota
  project_name        = var.project_name
  environment         = var.environment
  owner_name          = var.owner_name
  app_service_principal_id = module.app_service.principal_id
}

module "app_service" {
  source              = "./modules/app_service"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  project_name        = var.project_name
  environment         = var.environment
  owner_name          = var.owner_name
  sku_name            = var.app_service_sku_name

  # Key Vault references — these are resolved by App Service at runtime
  key_vault_id  = module.key_vault.vault_id
  key_vault_uri = module.key_vault.vault_uri

  # App settings (non-sensitive are passed directly; secrets via KV references)
  app_settings = {
    APPINSIGHTS_INSTRUMENTATIONKEY        = "@Microsoft.KeyVault(SecretUri=${module.key_vault.vault_uri}secrets/appinsights-key/)"
    APPLICATIONINSIGHTS_CONNECTION_STRING = module.monitoring.connection_string
    AZURE_OPENAI_ENDPOINT                 = module.ai_foundry.endpoint
    AZURE_OPENAI_DEPLOYMENT               = "gpt-4o-mini"
    BLOB_STORAGE_URL                      = module.storage.blob_service_url
    BLOB_CONTAINER_NAME                   = module.storage.container_name
    DATABASE_URL                          = "@Microsoft.KeyVault(SecretUri=${module.key_vault.vault_uri}secrets/database-url/)"
    GMAIL_USER                            = "@Microsoft.KeyVault(SecretUri=${module.key_vault.vault_uri}secrets/gmail-user/)"
    GMAIL_APP_PASSWORD                    = "@Microsoft.KeyVault(SecretUri=${module.key_vault.vault_uri}secrets/gmail-app-password/)"
    ADMIN_EMAILS                          = "@Microsoft.KeyVault(SecretUri=${module.key_vault.vault_uri}secrets/admin-emails/)"
    SECRET_KEY                            = "@Microsoft.KeyVault(SecretUri=${module.key_vault.vault_uri}secrets/flask-secret-key/)"
    FLASK_ENV                             = var.environment == "prod" ? "production" : "development"
    WEBSITES_PORT                         = "8000"
    SCM_DO_BUILD_DURING_DEPLOYMENT        = "true"
  }

  depends_on = [module.key_vault, module.postgresql, module.monitoring]
}

module "front_door" {
  source              = "./modules/front_door"
  resource_group_name = azurerm_resource_group.main.name
  location            = "global"
  project_name        = var.project_name
  environment         = var.environment
  owner_name          = var.owner_name
  origin_hostname     = module.app_service.default_hostname
  custom_domain       = var.custom_domain
}

# ---------------------------------------------------------------------------
# Store secrets in Key Vault after resources are created
# ---------------------------------------------------------------------------

resource "azurerm_key_vault_secret" "database_url" {
  name         = "database-url"
  value        = "postgresql://${var.db_username}:${var.db_password}@${module.postgresql.server_fqdn}:5432/${var.db_name}?sslmode=require"
  key_vault_id = module.key_vault.vault_id
  depends_on   = [module.key_vault, module.postgresql]
}

resource "azurerm_key_vault_secret" "gmail_user" {
  name         = "gmail-user"
  value        = var.gmail_user
  key_vault_id = module.key_vault.vault_id
  depends_on   = [module.key_vault]
}

resource "azurerm_key_vault_secret" "gmail_app_password" {
  name         = "gmail-app-password"
  value        = var.gmail_app_password
  key_vault_id = module.key_vault.vault_id
  depends_on   = [module.key_vault]
}

resource "azurerm_key_vault_secret" "admin_emails" {
  name         = "admin-emails"
  value        = var.admin_emails
  key_vault_id = module.key_vault.vault_id
  depends_on   = [module.key_vault]
}

resource "random_password" "flask_secret_key" {
  length  = 64
  special = true
}

resource "azurerm_key_vault_secret" "flask_secret_key" {
  name         = "flask-secret-key"
  value        = random_password.flask_secret_key.result
  key_vault_id = module.key_vault.vault_id
  depends_on   = [module.key_vault]
}

resource "azurerm_key_vault_secret" "appinsights_key" {
  name         = "appinsights-key"
  value        = module.monitoring.instrumentation_key
  key_vault_id = module.key_vault.vault_id
  depends_on   = [module.key_vault, module.monitoring]
}
