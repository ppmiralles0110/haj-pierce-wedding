variable "resource_group_name" { type = string }
variable "location"            { type = string }
variable "project_name"        { type = string }
variable "environment"         { type = string }
variable "owner_name"          { type = string }
variable "origin_hostname" {
  type        = string
  description = "App Service default hostname"
}
variable "custom_domain" {
  type        = string
  default     = null
  description = "Optional custom domain. Set to null to skip."
}
