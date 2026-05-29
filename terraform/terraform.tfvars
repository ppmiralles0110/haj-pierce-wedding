# =============================================================================
# terraform/terraform.tfvars — Active deployment values
# NEVER commit this file to git (already in .gitignore)
# Sensitive values (db_password, gmail_user, gmail_app_password) are passed via
# TF_VAR_* environment variables — not stored here.
# =============================================================================

environment  = "prod"
location     = "southeastasia"
ai_location  = "swedencentral"
project_name = "wedding"
owner_name   = "pierce"

# App Service Plan: B2 (~$25/month) — cheapest plan with always-on + custom domain
app_service_sku_name = "B2"

# PostgreSQL Flexible Server: B_Standard_B1ms (~$12/month)
postgresql_sku_name   = "B_Standard_B1ms"
postgresql_storage_mb = 32768

db_username = "weddingadmin"
db_name     = "wedding_db"

# No custom domain — using default azurewebsites.net URL
custom_domain = null

# Admin access
admin_emails = "pierce.miralles@outlook.com"
