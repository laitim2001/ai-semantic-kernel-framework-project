// =============================================================================
// IPA Platform — Database Module
//
// Creates Azure Database for PostgreSQL Flexible Server.
// Sprint 122, Story 122-1
// =============================================================================

@description('Azure region')
param location string

@description('Resource naming prefix')
param resourcePrefix string

@description('Resource tags')
param tags object

@description('PostgreSQL administrator login')
@secure()
param administratorLogin string

@description('PostgreSQL administrator password')
@secure()
param administratorPassword string

@description('Database name to create')
param databaseName string = 'ipa_platform'

@description('PostgreSQL version')
@allowed(['14', '15', '16'])
param postgresVersion string = '16'

// =============================================================================
// PostgreSQL Flexible Server
// =============================================================================

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: 'psql-${resourcePrefix}'
  location: location
  tags: tags
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: postgresVersion
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    storage: {
      storageSizeGB: 32
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// --- Database ---
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: postgresServer
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// --- Firewall: Allow Azure Services ---
resource firewallAllowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = {
  parent: postgresServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// --- PostgreSQL Extensions ---
resource pgExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-06-01-preview' = {
  parent: postgresServer
  name: 'azure.extensions'
  properties: {
    value: 'UUID-OSSP'
    source: 'user-override'
  }
}

// =============================================================================
// Outputs
// =============================================================================

output fqdn string = postgresServer.properties.fullyQualifiedDomainName
output serverId string = postgresServer.id
output serverName string = postgresServer.name
