// =============================================================================
// IPA Platform — App Service Module
//
// Creates App Service Plans + Web Apps for Backend and Frontend.
// Sprint 122, Story 122-1
// =============================================================================

@description('Azure region')
param location string

@description('Resource naming prefix')
param resourcePrefix string

@description('Resource tags')
param tags object

// --- Container Registry ---
@description('ACR login server URL')
param acrLoginServer string

@description('ACR name')
param acrName string

// --- Database ---
@description('PostgreSQL FQDN')
param dbHost string

@description('Database name')
param dbName string

@description('Database user')
@secure()
param dbUser string

@description('Database password')
@secure()
param dbPassword string

// --- Redis ---
@description('Redis hostname')
param redisHost string

@description('Redis port')
param redisPort int

@description('Redis access key')
@secure()
param redisPassword string

// --- Observability ---
@description('Application Insights connection string')
param appInsightsConnectionString string

// --- Azure OpenAI ---
@description('Azure OpenAI endpoint')
param azureOpenAIEndpoint string

@description('Azure OpenAI API key')
@secure()
param azureOpenAIApiKey string

@description('Azure OpenAI deployment name')
param azureOpenAIDeploymentName string

// --- Security ---
@description('JWT secret key')
@secure()
param jwtSecretKey string

@description('Application secret key')
@secure()
param appSecretKey string

// =============================================================================
// Backend App Service Plan (B2)
// =============================================================================

resource backendPlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: 'asp-${resourcePrefix}-backend'
  location: location
  tags: tags
  kind: 'linux'
  sku: {
    name: 'B2'
    tier: 'Basic'
    capacity: 1
  }
  properties: {
    reserved: true // Required for Linux
  }
}

// =============================================================================
// Backend Web App
// =============================================================================

resource backendApp 'Microsoft.Web/sites@2023-01-01' = {
  name: 'app-${resourcePrefix}-backend'
  location: location
  tags: tags
  kind: 'app,linux,container'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: backendPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${acrLoginServer}/ipa-platform:latest'
      alwaysOn: true
      ftpsState: 'Disabled'
      http20Enabled: true
      minTlsVersion: '1.2'
      healthCheckPath: '/health'
      appSettings: [
        { name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE', value: 'false' }
        { name: 'DOCKER_REGISTRY_SERVER_URL', value: 'https://${acrLoginServer}' }
        // --- Application ---
        { name: 'APP_ENV', value: 'production' }
        { name: 'LOG_LEVEL', value: 'INFO' }
        { name: 'SECRET_KEY', value: appSecretKey }
        // --- Database ---
        { name: 'DB_HOST', value: dbHost }
        { name: 'DB_PORT', value: '5432' }
        { name: 'DB_NAME', value: dbName }
        { name: 'DB_USER', value: dbUser }
        { name: 'DB_PASSWORD', value: dbPassword }
        // --- Redis ---
        { name: 'REDIS_HOST', value: redisHost }
        { name: 'REDIS_PORT', value: string(redisPort) }
        { name: 'REDIS_PASSWORD', value: redisPassword }
        { name: 'REDIS_SSL', value: 'true' }
        // --- Azure OpenAI ---
        { name: 'AZURE_OPENAI_ENDPOINT', value: azureOpenAIEndpoint }
        { name: 'AZURE_OPENAI_API_KEY', value: azureOpenAIApiKey }
        { name: 'AZURE_OPENAI_DEPLOYMENT_NAME', value: azureOpenAIDeploymentName }
        // --- JWT ---
        { name: 'JWT_SECRET_KEY', value: jwtSecretKey }
        // --- Observability ---
        { name: 'OTEL_ENABLED', value: 'true' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
        { name: 'OTEL_SERVICE_NAME', value: 'ipa-platform-backend' }
        // --- Structured Logging ---
        { name: 'STRUCTURED_LOGGING_ENABLED', value: 'true' }
        // --- CORS ---
        { name: 'CORS_ORIGINS', value: 'https://app-${resourcePrefix}-frontend.azurewebsites.net' }
      ]
    }
  }
}

// --- Backend Staging Slot ---
resource backendStaging 'Microsoft.Web/sites/slots@2023-01-01' = {
  parent: backendApp
  name: 'staging'
  location: location
  tags: tags
  kind: 'app,linux,container'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: backendPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${acrLoginServer}/ipa-platform:latest'
      alwaysOn: false
      healthCheckPath: '/health'
    }
  }
}

// =============================================================================
// Frontend App Service Plan (B1)
// =============================================================================

resource frontendPlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: 'asp-${resourcePrefix}-frontend'
  location: location
  tags: tags
  kind: 'linux'
  sku: {
    name: 'B1'
    tier: 'Basic'
    capacity: 1
  }
  properties: {
    reserved: true
  }
}

// =============================================================================
// Frontend Web App
// =============================================================================

resource frontendApp 'Microsoft.Web/sites@2023-01-01' = {
  name: 'app-${resourcePrefix}-frontend'
  location: location
  tags: tags
  kind: 'app,linux,container'
  properties: {
    serverFarmId: frontendPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${acrLoginServer}/ipa-frontend:latest'
      alwaysOn: false
      ftpsState: 'Disabled'
      http20Enabled: true
      minTlsVersion: '1.2'
      appSettings: [
        { name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE', value: 'false' }
        { name: 'DOCKER_REGISTRY_SERVER_URL', value: 'https://${acrLoginServer}' }
      ]
    }
  }
}

// --- Frontend Staging Slot ---
resource frontendStaging 'Microsoft.Web/sites/slots@2023-01-01' = {
  parent: frontendApp
  name: 'staging'
  location: location
  tags: tags
  kind: 'app,linux,container'
  properties: {
    serverFarmId: frontendPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${acrLoginServer}/ipa-frontend:latest'
      alwaysOn: false
    }
  }
}

// =============================================================================
// ACR Pull Role Assignment (Backend)
// =============================================================================

// Allow backend to pull images from ACR via Managed Identity
resource acrPullRoleBackend 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(backendApp.id, 'acrpull')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull
    )
    principalId: backendApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// =============================================================================
// Outputs
// =============================================================================

output backendUrl string = 'https://${backendApp.properties.defaultHostName}'
output frontendUrl string = 'https://${frontendApp.properties.defaultHostName}'
output backendPrincipalId string = backendApp.identity.principalId
output backendAppName string = backendApp.name
output frontendAppName string = frontendApp.name
