variable "resource_group_name" { type = string }
variable "location"            { type = string }
variable "project_name"        { type = string }
variable "environment"         { type = string }
variable "owner_name"          { type = string }
variable "sku_name" {
  type    = string
  default = "B2"
}
variable "key_vault_id"        { type = string }
variable "key_vault_uri"       { type = string }
variable "app_settings" {
  type    = map(string)
  default = {}
}
variable "app_service_principal_id" {
  type        = string
  default     = ""
  description = "Unused here — provided by caller, placeholder only."
}
