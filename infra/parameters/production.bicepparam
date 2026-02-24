// =============================================================================
// IPA Platform — Production Parameters
//
// Sprint 122, Story 122-1
//
// IMPORTANT: Do NOT commit actual secrets to this file.
// Use Azure Key Vault references or pass secrets via CLI:
//   az deployment group create ... \
//     --parameters @infra/parameters/production.bicepparam \
//     --parameters dbAdminPassword=$DB_ADMIN_PASSWORD
// =============================================================================

using '../main.bicep'

param environment = 'production'
param projectName = 'ipa'
param dbName = 'ipa_platform'
param azureOpenAIDeploymentName = 'gpt-5.2'

// --- Secrets (must be provided via CLI or pipeline variables) ---
// param dbAdminLogin = '<from-pipeline>'
// param dbAdminPassword = '<from-pipeline>'
// param azureOpenAIEndpoint = '<from-pipeline>'
// param azureOpenAIApiKey = '<from-pipeline>'
// param jwtSecretKey = '<from-pipeline>'
// param appSecretKey = '<from-pipeline>'
