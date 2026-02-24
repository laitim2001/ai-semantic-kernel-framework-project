// =============================================================================
// IPA Platform — Main Infrastructure Template
//
// Sprint 122, Story 122-1: Azure App Service Deployment
// Orchestrates all Azure resource modules for the IPA Platform.
//
// Usage:
//   az deployment group create \
//     --resource-group rg-ipa-platform \
//     --template-file infra/main.bicep \
//     --parameters infra/parameters/production.bicepparam
// =============================================================================

targetScope = 'resourceGroup'

// =============================================================================
// Parameters
// =============================================================================

@description('Environment name (production, staging)')
@allowed(['production', 'staging'])
param environment string = 'production'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Project name prefix for resource naming')
param projectName string = 'ipa'

@description('PostgreSQL administrator login')
@secure()
param dbAdminLogin string

@description('PostgreSQL administrator password')
@secure()
param dbAdminPassword string

@description('PostgreSQL database name')
param dbName string = 'ipa_platform'

@description('Azure OpenAI endpoint')
param azureOpenAIEndpoint string = ''

@description('Azure OpenAI API key')
@secure()
param azureOpenAIApiKey string = ''

@description('Azure OpenAI deployment name')
param azureOpenAIDeploymentName string = 'gpt-5.2'

@description('JWT secret key for authentication')
@secure()
param jwtSecretKey string

@description('Application secret key')
@secure()
param appSecretKey string

// =============================================================================
// Variables
// =============================================================================

var resourcePrefix = '${projectName}-${environment}'
var tags = {
  project: 'ipa-platform'
  environment: environment
  managedBy: 'bicep'
  sprint: '122'
}

// =============================================================================
// Modules
// =============================================================================

// --- Monitoring (must be deployed first for instrumentation key) ---
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring-${environment}'
  params: {
    location: location
    resourcePrefix: resourcePrefix
    tags: tags
  }
}

// --- Container Registry ---
module containerRegistry 'modules/container-registry.bicep' = {
  name: 'acr-${environment}'
  params: {
    location: location
    resourcePrefix: resourcePrefix
    tags: tags
  }
}

// --- Database ---
module database 'modules/database.bicep' = {
  name: 'database-${environment}'
  params: {
    location: location
    resourcePrefix: resourcePrefix
    tags: tags
    administratorLogin: dbAdminLogin
    administratorPassword: dbAdminPassword
    databaseName: dbName
  }
}

// --- Redis Cache ---
module redis 'modules/redis.bicep' = {
  name: 'redis-${environment}'
  params: {
    location: location
    resourcePrefix: resourcePrefix
    tags: tags
  }
}

// --- App Service (Backend + Frontend) ---
module appService 'modules/app-service.bicep' = {
  name: 'appservice-${environment}'
  params: {
    location: location
    resourcePrefix: resourcePrefix
    tags: tags
    acrLoginServer: containerRegistry.outputs.loginServer
    acrName: containerRegistry.outputs.name
    dbHost: database.outputs.fqdn
    dbName: dbName
    dbUser: dbAdminLogin
    dbPassword: dbAdminPassword
    redisHost: redis.outputs.hostname
    redisPort: redis.outputs.port
    redisPassword: redis.outputs.primaryKey
    appInsightsConnectionString: monitoring.outputs.connectionString
    azureOpenAIEndpoint: azureOpenAIEndpoint
    azureOpenAIApiKey: azureOpenAIApiKey
    azureOpenAIDeploymentName: azureOpenAIDeploymentName
    jwtSecretKey: jwtSecretKey
    appSecretKey: appSecretKey
  }
}

// =============================================================================
// Outputs
// =============================================================================

output backendUrl string = appService.outputs.backendUrl
output frontendUrl string = appService.outputs.frontendUrl
output acrLoginServer string = containerRegistry.outputs.loginServer
output appInsightsConnectionString string = monitoring.outputs.connectionString
output dbFqdn string = database.outputs.fqdn
output redisHostname string = redis.outputs.hostname
