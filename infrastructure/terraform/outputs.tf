# IPA Platform - Terraform Outputs
# Sprint 0: Infrastructure Foundation

# =============================================================================
# Resource Group
# =============================================================================

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = azurerm_resource_group.main.location
}

# =============================================================================
# App Service
# =============================================================================

output "app_service_name" {
  description = "Name of the App Service"
  value       = azurerm_linux_web_app.main.name
}

output "app_service_url" {
  description = "Default URL of the App Service"
  value       = "https://${azurerm_linux_web_app.main.default_hostname}"
}

output "app_service_principal_id" {
  description = "Principal ID of the App Service managed identity"
  value       = azurerm_linux_web_app.main.identity[0].principal_id
}

# =============================================================================
# Database
# =============================================================================

output "postgresql_server_name" {
  description = "Name of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.main.name
}

output "postgresql_server_fqdn" {
  description = "FQDN of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "postgresql_database_name" {
  description = "Name of the PostgreSQL database"
  value       = azurerm_postgresql_flexible_server_database.main.name
}

# =============================================================================
# Redis
# =============================================================================

output "redis_cache_name" {
  description = "Name of the Redis cache"
  value       = azurerm_redis_cache.main.name
}

output "redis_cache_hostname" {
  description = "Hostname of the Redis cache"
  value       = azurerm_redis_cache.main.hostname
}

output "redis_cache_ssl_port" {
  description = "SSL port of the Redis cache"
  value       = azurerm_redis_cache.main.ssl_port
}

# =============================================================================
# Service Bus
# =============================================================================

output "service_bus_namespace" {
  description = "Name of the Service Bus namespace"
  value       = azurerm_servicebus_namespace.main.name
}

output "service_bus_connection_string" {
  description = "Primary connection string for Service Bus"
  value       = azurerm_servicebus_namespace.main.default_primary_connection_string
  sensitive   = true
}

# =============================================================================
# Key Vault
# =============================================================================

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.main.vault_uri
}

# =============================================================================
# Application Insights
# =============================================================================

output "application_insights_name" {
  description = "Name of Application Insights"
  value       = azurerm_application_insights.main.name
}

output "application_insights_instrumentation_key" {
  description = "Instrumentation key for Application Insights"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "application_insights_connection_string" {
  description = "Connection string for Application Insights"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

# =============================================================================
# Summary
# =============================================================================

output "deployment_summary" {
  description = "Summary of deployed resources"
  value = <<-EOT
    IPA Platform Infrastructure Deployment Summary
    ===============================================
    Environment: ${var.environment}
    Location: ${var.location}

    Resources:
    - Resource Group: ${azurerm_resource_group.main.name}
    - App Service: ${azurerm_linux_web_app.main.name}
    - PostgreSQL: ${azurerm_postgresql_flexible_server.main.name}
    - Redis: ${azurerm_redis_cache.main.name}
    - Service Bus: ${azurerm_servicebus_namespace.main.name}
    - Key Vault: ${azurerm_key_vault.main.name}
    - App Insights: ${azurerm_application_insights.main.name}

    URLs:
    - App: https://${azurerm_linux_web_app.main.default_hostname}
    - Health: https://${azurerm_linux_web_app.main.default_hostname}/health
    - API Docs: https://${azurerm_linux_web_app.main.default_hostname}/docs
  EOT
}
