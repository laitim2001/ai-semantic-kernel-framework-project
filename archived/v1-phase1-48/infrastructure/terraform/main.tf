# IPA Platform - Azure Infrastructure
# Sprint 0: Infrastructure Foundation
#
# This Terraform configuration creates the Azure resources needed for the IPA Platform.
#
# Usage:
#   cd infrastructure/terraform
#   terraform init
#   terraform plan -var-file="dev.tfvars"
#   terraform apply -var-file="dev.tfvars"

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Backend configuration for remote state (uncomment for production)
  # backend "azurerm" {
  #   resource_group_name  = "rg-terraform-state"
  #   storage_account_name = "stterraformstate"
  #   container_name       = "tfstate"
  #   key                  = "ipa-platform.tfstate"
  # }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

# =============================================================================
# Data Sources
# =============================================================================

data "azurerm_client_config" "current" {}

# =============================================================================
# Random Suffix for Unique Names
# =============================================================================

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# =============================================================================
# Resource Group
# =============================================================================

resource "azurerm_resource_group" "main" {
  name     = "rg-ipa-platform-${var.environment}"
  location = var.location

  tags = local.common_tags
}

# =============================================================================
# App Service Plan
# =============================================================================

resource "azurerm_service_plan" "main" {
  name                = "asp-ipa-platform-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku

  tags = local.common_tags
}

# =============================================================================
# App Service (Web App)
# =============================================================================

resource "azurerm_linux_web_app" "main" {
  name                = "app-ipa-platform-${var.environment}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.main.id

  site_config {
    always_on = var.environment == "production" ? true : false

    application_stack {
      python_version = "3.11"
    }

    health_check_path = "/health"
  }

  app_settings = {
    "APP_ENV"                     = var.environment
    "WEBSITES_PORT"               = "8000"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"

    # Database connection (from Key Vault reference)
    "DB_HOST"     = azurerm_postgresql_flexible_server.main.fqdn
    "DB_PORT"     = "5432"
    "DB_NAME"     = azurerm_postgresql_flexible_server_database.main.name
    "DB_USER"     = var.db_admin_username
    "DB_PASSWORD" = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.main.name};SecretName=db-password)"

    # Redis connection
    "REDIS_HOST"     = azurerm_redis_cache.main.hostname
    "REDIS_PORT"     = azurerm_redis_cache.main.ssl_port
    "REDIS_PASSWORD" = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.main.name};SecretName=redis-password)"

    # Azure OpenAI
    "AZURE_OPENAI_ENDPOINT"        = var.azure_openai_endpoint
    "AZURE_OPENAI_API_KEY"         = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.main.name};SecretName=azure-openai-key)"
    "AZURE_OPENAI_DEPLOYMENT_NAME" = var.azure_openai_deployment_name

    # Application Insights
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

# =============================================================================
# PostgreSQL Flexible Server
# =============================================================================

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "psql-ipa-platform-${var.environment}-${random_string.suffix.result}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = "16"
  administrator_login    = var.db_admin_username
  administrator_password = var.db_admin_password
  zone                   = "1"
  storage_mb             = var.db_storage_mb
  sku_name               = var.db_sku

  # Allow Azure services to access the server
  public_network_access_enabled = true

  tags = local.common_tags
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "ipa_platform"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Allow Azure services firewall rule
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# =============================================================================
# Redis Cache
# =============================================================================

resource "azurerm_redis_cache" "main" {
  name                = "redis-ipa-platform-${var.environment}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  capacity            = var.redis_capacity
  family              = var.redis_family
  sku_name            = var.redis_sku
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  redis_configuration {
  }

  tags = local.common_tags
}

# =============================================================================
# Service Bus (Message Queue)
# =============================================================================

resource "azurerm_servicebus_namespace" "main" {
  name                = "sb-ipa-platform-${var.environment}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.service_bus_sku

  tags = local.common_tags
}

resource "azurerm_servicebus_queue" "workflow_tasks" {
  name         = "workflow-tasks"
  namespace_id = azurerm_servicebus_namespace.main.id

  enable_partitioning = false
  max_size_in_megabytes = 1024
}

resource "azurerm_servicebus_queue" "agent_requests" {
  name         = "agent-requests"
  namespace_id = azurerm_servicebus_namespace.main.id

  enable_partitioning = false
  max_size_in_megabytes = 1024
}

# =============================================================================
# Key Vault
# =============================================================================

resource "azurerm_key_vault" "main" {
  name                = "kv-ipa-${var.environment}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  purge_protection_enabled   = var.environment == "production" ? true : false
  soft_delete_retention_days = 7

  # Allow the current user to manage secrets
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get", "List", "Set", "Delete", "Purge", "Recover"
    ]
  }

  tags = local.common_tags
}

# Store secrets in Key Vault
resource "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  value        = var.db_admin_password
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "redis_password" {
  name         = "redis-password"
  value        = azurerm_redis_cache.main.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "azure_openai_key" {
  name         = "azure-openai-key"
  value        = var.azure_openai_api_key
  key_vault_id = azurerm_key_vault.main.id
}

# Grant App Service access to Key Vault
resource "azurerm_key_vault_access_policy" "app_service" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_linux_web_app.main.identity[0].principal_id

  secret_permissions = [
    "Get", "List"
  ]
}

# =============================================================================
# Application Insights
# =============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-ipa-platform-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.common_tags
}

resource "azurerm_application_insights" "main" {
  name                = "appi-ipa-platform-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = local.common_tags
}

# =============================================================================
# Local Values
# =============================================================================

locals {
  common_tags = {
    Environment = var.environment
    Project     = "IPA Platform"
    ManagedBy   = "Terraform"
  }
}
