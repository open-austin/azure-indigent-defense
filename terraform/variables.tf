variable "project" {
  type        = string
  default     = "indigent-defense-stats"
  description = "Project name"
}

variable "proj_prefix" {
  type        = string
  default     = "ids"
  description = "Project name abbreviation for use as prefix in short fields"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment (dev / test / prod)"
  validation {
    condition     = var.environment == "dev" || var.environment == "test" || var.environment == "prod"
    error_message = "Environment must be either dev, test, or prod"
  }
}

variable "location" {
  type        = string
  default     = "South Central US"
  description = "location location location"
}
