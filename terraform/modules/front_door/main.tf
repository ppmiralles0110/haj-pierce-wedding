# =============================================================================
# terraform/modules/front_door/main.tf — Azure Front Door Standard
# Includes optional custom domain setup (count = var.custom_domain != null ? 1 : 0)
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

resource "azurerm_cdn_frontdoor_profile" "main" {
  name                = "${local.name_prefix}-afd"
  resource_group_name = var.resource_group_name
  sku_name            = "Standard_AzureFrontDoor"
  tags                = local.tags
}

resource "azurerm_cdn_frontdoor_endpoint" "main" {
  name                     = "${local.name_prefix}-endpoint"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  tags                     = local.tags
}

resource "azurerm_cdn_frontdoor_origin_group" "main" {
  name                     = "${local.name_prefix}-og"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id

  load_balancing {
    sample_size                 = 4
    successful_samples_required = 3
  }

  health_probe {
    path                = "/health"
    request_type        = "GET"
    protocol            = "Https"
    interval_in_seconds = 30
  }
}

resource "azurerm_cdn_frontdoor_origin" "app_service" {
  name                          = "${local.name_prefix}-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  enabled                       = true

  host_name          = var.origin_hostname
  origin_host_header = var.origin_hostname
  https_port         = 443
  priority           = 1
  weight             = 1000

  certificate_name_check_enabled = true
}

resource "azurerm_cdn_frontdoor_route" "main" {
  name                          = "${local.name_prefix}-route"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.main.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.app_service.id]

  forwarding_protocol    = "HttpsOnly"
  https_redirect_enabled = true
  patterns_to_match      = ["/*"]
  supported_protocols    = ["Http", "Https"]

  cdn_frontdoor_custom_domain_ids = var.custom_domain != null ? [
    azurerm_cdn_frontdoor_custom_domain.main[0].id
  ] : []

  link_to_default_domain = true
}

# ---------------------------------------------------------------------------
# Custom domain — only created when var.custom_domain is set
# ---------------------------------------------------------------------------

resource "azurerm_cdn_frontdoor_custom_domain" "main" {
  count = var.custom_domain != null ? 1 : 0

  name                     = replace(var.custom_domain, ".", "-")
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  dns_zone_id              = null  # Set to your Azure DNS zone resource ID if using Azure DNS
  host_name                = var.custom_domain

  tls {
    certificate_type    = "ManagedCertificate"
    minimum_tls_version = "TLS12"
  }
}

resource "azurerm_cdn_frontdoor_custom_domain_association" "main" {
  count = var.custom_domain != null ? 1 : 0

  cdn_frontdoor_custom_domain_id = azurerm_cdn_frontdoor_custom_domain.main[0].id
  cdn_frontdoor_route_ids        = [azurerm_cdn_frontdoor_route.main.id]
}

# ---------------------------------------------------------------------------
# NOTE: After Terraform apply, configure your DNS registrar:
#
#   If using Azure DNS (dns_zone_id set above):
#     Terraform will manage the CNAME/TXT records automatically.
#
#   If using an external DNS registrar:
#     1. Add a CNAME record:
#        Name:  <subdomain or @>
#        Value: <azurerm_cdn_frontdoor_endpoint.main.host_name>
#     2. Add a TXT record for domain validation (shown in Azure Portal under
#        Front Door > Custom Domains > Validation State).
#     3. Wait for "Pending" → "Approved" status (up to 10 minutes).
# ---------------------------------------------------------------------------
