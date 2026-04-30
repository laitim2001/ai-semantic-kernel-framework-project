# IPA Platform - Terraform Variables
# Sprint 0: Infrastructure Foundation

# =============================================================================
# General
# =============================================================================

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "East Asia"
}

# =============================================================================
# App Service
# =============================================================================

variable "app_service_sku" {
  description = "App Service Plan SKU"
  type        = string
  default     = "B1"

  # B1 for MVP/dev, S1 for staging, P1v2+ for production
}

# =============================================================================
# Database (PostgreSQL)
# =============================================================================

variable "db_admin_username" {
  description = "PostgreSQL administrator username"
  type        = string
  default     = "ipaadmin"
}

variable "db_admin_password" {
  description = "PostgreSQL administrator password"
  type        = string
  sensitive   = true
}

variable "db_sku" {
  description = "PostgreSQL Flexible Server SKU"
  type        = string
  default     = "B_Standard_B1ms"

  # B_Standard_B1ms for dev, GP_Standard_D2s_v3 for production
}

variable "db_storage_mb" {
  description = "PostgreSQL storage size in MB"
  type        = number
  default     = 32768  # 32 GB
}

# =============================================================================
# Redis Cache
# =============================================================================

variable "redis_capacity" {
  description = "Redis cache capacity"
  type        = number
  default     = 0  # 250 MB for Basic C0
}

variable "redis_family" {
  description = "Redis cache family"
  type        = string
  default     = "C"  # C for Basic/Standard, P for Premium
}

variable "redis_sku" {
  description = "Redis cache SKU"
  type        = string
  default     = "Basic"

  # Basic for dev, Standard for staging, Premium for production
}

# =============================================================================
# Service Bus
# =============================================================================

variable "service_bus_sku" {
  description = "Service Bus namespace SKU"
  type        = string
  default     = "Basic"

  # Basic for dev, Standard for staging/production
}

# =============================================================================
# Azure OpenAI
# =============================================================================

variable "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint URL"
  type        = string
  default     = ""
}

variable "azure_openai_api_key" {
  description = "Azure OpenAI API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_openai_deployment_name" {
  description = "Azure OpenAI deployment name"
  type        = string
  default     = "gpt-4o"
}
