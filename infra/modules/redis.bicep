// =============================================================================
// IPA Platform — Redis Cache Module
//
// Creates Azure Cache for Redis (Basic C0).
// Sprint 122, Story 122-1
// =============================================================================

@description('Azure region')
param location string

@description('Resource naming prefix')
param resourcePrefix string

@description('Resource tags')
param tags object

// =============================================================================
// Azure Cache for Redis
// =============================================================================

resource redisCache 'Microsoft.Cache/redis@2023-08-01' = {
  name: 'redis-${resourcePrefix}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
    }
  }
}

// =============================================================================
// Outputs
// =============================================================================

output hostname string = redisCache.properties.hostName
output port int = redisCache.properties.sslPort
output primaryKey string = listKeys(redisCache.id, redisCache.apiVersion).primaryKey
output id string = redisCache.id
