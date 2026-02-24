// =============================================================================
// IPA Platform — Container Registry Module
//
// Creates Azure Container Registry for Docker images.
// Sprint 122, Story 122-1
// =============================================================================

@description('Azure region')
param location string

@description('Resource naming prefix')
param resourcePrefix string

@description('Resource tags')
param tags object

// =============================================================================
// Azure Container Registry
// =============================================================================

// ACR names must be alphanumeric only, 5-50 characters
var acrName = replace('acr${resourcePrefix}', '-', '')

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
}

// =============================================================================
// Outputs
// =============================================================================

output name string = acr.name
output loginServer string = acr.properties.loginServer
output id string = acr.id
