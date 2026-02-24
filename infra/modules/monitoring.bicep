// =============================================================================
// IPA Platform — Monitoring Module
//
// Creates Log Analytics Workspace + Application Insights for observability.
// Sprint 122, Story 122-1
// =============================================================================

@description('Azure region')
param location string

@description('Resource naming prefix')
param resourcePrefix string

@description('Resource tags')
param tags object

// =============================================================================
// Log Analytics Workspace
// =============================================================================

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'law-${resourcePrefix}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {
      dailyQuotaGb: 1
    }
  }
}

// =============================================================================
// Application Insights
// =============================================================================

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${resourcePrefix}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    RetentionInDays: 30
    SamplingPercentage: 50
  }
}

// =============================================================================
// Outputs
// =============================================================================

output connectionString string = appInsights.properties.ConnectionString
output instrumentationKey string = appInsights.properties.InstrumentationKey
output logAnalyticsId string = logAnalytics.id
output appInsightsId string = appInsights.id
