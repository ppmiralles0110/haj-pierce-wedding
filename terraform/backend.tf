# =============================================================================
# terraform/backend.tf — Remote state in Azure Blob Storage
# =============================================================================
# Before running terraform init, create the storage account manually:
#
#   az group create --name tfstate-rg --location southeastasia
#   az storage account create \
#     --name <UNIQUE_SA_NAME> \
#     --resource-group tfstate-rg \
#     --location southeastasia \
#     --sku Standard_LRS
#   az storage container create \
#     --name tfstate \
#     --account-name <UNIQUE_SA_NAME>
#
# Then replace the placeholder values below.
# =============================================================================

terraform {
  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "wdtfstate2026"
    container_name       = "tfstate"
    key                  = "wedding-website.tfstate"
  }
}
