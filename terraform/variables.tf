# =============================================================================
# terraform/variables.tf — Input variable declarations
# =============================================================================

# ---- General ----------------------------------------------------------------

variable "environment" {
  description = "Deployment environment (dev / staging / prod)"
  type        = string
  default     = "prod"
}

variable "location" {
  description = "Primary Azure region for all resources (except AI)"
  type        = string
  default     = "southeastasia"
}

variable "ai_location" {
  description = "Azure region for Azure OpenAI (must have gpt-4o-mini quota)"
  type        = string
  default     = "swedencentral"
}

variable "project_name" {
  description = "Short project identifier used in resource naming"
  type        = string
  default     = "wedding"
}

variable "owner_name" {
  description = "Owner tag value applied to all resources"
  type        = string
  default     = "pierce"  # EDIT THIS
}

# ---- App Service ------------------------------------------------------------

variable "app_service_sku_name" {
  description = "App Service plan SKU (B2 for dev, P1v3 for prod)"
  type        = string
  default     = "B2"
}

# ---- PostgreSQL -------------------------------------------------------------

variable "postgresql_sku_name" {
  description = "PostgreSQL Flexible Server SKU"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "postgresql_storage_mb" {
  description = "PostgreSQL storage size in MB"
  type        = number
  default     = 32768
}

variable "db_username" {
  description = "PostgreSQL administrator username"
  type        = string
  default     = "weddingadmin"
}

variable "db_password" {
  description = "PostgreSQL administrator password (store in tfvars, NOT in git)"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "Name of the application database"
  type        = string
  default     = "wedding_db"
}

# ---- Front Door / Custom Domain ---------------------------------------------

variable "custom_domain" {
  description = "Custom domain for the website. Set to null to skip DNS/cert setup."
  type        = string
  default     = null  # e.g. "haj-and-pierce.wedding"
}

# ---- Security ---------------------------------------------------------------

variable "admin_emails" {
  description = "Comma-separated list of admin email addresses"
  type        = string
  sensitive   = true
}

variable "sendgrid_api_key" {
  description = "SendGrid API key for OTP email delivery"
  type        = string
  sensitive   = true
}
