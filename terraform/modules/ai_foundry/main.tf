# =============================================================================
# terraform/modules/ai_foundry/main.tf — Azure OpenAI (GPT-4o-mini)
# Deployed to Sweden Central where GPT-4o-mini quota is available.
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

resource "azurerm_cognitive_account" "openai" {
  name                = "${local.name_prefix}-openai"
  resource_group_name = var.resource_group_name
  location            = var.location  # swedencentral
  kind                = "OpenAI"
  sku_name            = "S0"

  custom_subdomain_name = "${local.name_prefix}-openai"

  tags = local.tags
}

resource "azurerm_cognitive_deployment" "gpt5_mini" {
  name                 = "gpt-5-mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-5-mini"
    version = "2025-08-07"
  }

  scale {
    type     = "GlobalStandard"
    capacity = 10  # TPM in thousands (10k TPM)
  }
}

# Grant App Service managed identity Cognitive Services OpenAI User
resource "azurerm_role_assignment" "app_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = var.app_service_principal_id
}
