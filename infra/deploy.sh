#!/usr/bin/env bash
# =============================================================================
# IPA Platform — Azure Infrastructure Deployment Script
#
# Sprint 122, Story 122-1
#
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - Bicep CLI available (az bicep install)
#   - Environment variables set for secrets
#
# Usage:
#   export DB_ADMIN_LOGIN=ipaadmin
#   export DB_ADMIN_PASSWORD='<secure-password>'
#   export AZURE_OPENAI_ENDPOINT='https://<resource>.openai.azure.com/'
#   export AZURE_OPENAI_API_KEY='<key>'
#   export JWT_SECRET_KEY='<secure-random-string>'
#   export APP_SECRET_KEY='<secure-random-string>'
#   bash infra/deploy.sh [production|staging]
# =============================================================================

set -euo pipefail

# --- Configuration ---
ENVIRONMENT="${1:-production}"
RESOURCE_GROUP="rg-ipa-platform-${ENVIRONMENT}"
LOCATION="eastasia"
TEMPLATE_FILE="infra/main.bicep"
PARAMETERS_FILE="infra/parameters/${ENVIRONMENT}.bicepparam"

echo "=========================================="
echo "IPA Platform Infrastructure Deployment"
echo "=========================================="
echo "Environment:    ${ENVIRONMENT}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Location:       ${LOCATION}"
echo "=========================================="

# --- Validate required environment variables ---
required_vars=(
    "DB_ADMIN_LOGIN"
    "DB_ADMIN_PASSWORD"
    "JWT_SECRET_KEY"
    "APP_SECRET_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo "ERROR: Required environment variable ${var} is not set."
        exit 1
    fi
done

# --- Create Resource Group if not exists ---
echo ""
echo "[1/4] Ensuring resource group exists..."
az group create \
    --name "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --tags project=ipa-platform environment="${ENVIRONMENT}" managedBy=bicep \
    --output none

echo "  Resource group: ${RESOURCE_GROUP} (${LOCATION})"

# --- Validate Bicep Template ---
echo ""
echo "[2/4] Validating Bicep template..."
az deployment group validate \
    --resource-group "${RESOURCE_GROUP}" \
    --template-file "${TEMPLATE_FILE}" \
    --parameters "${PARAMETERS_FILE}" \
    --parameters \
        dbAdminLogin="${DB_ADMIN_LOGIN}" \
        dbAdminPassword="${DB_ADMIN_PASSWORD}" \
        azureOpenAIEndpoint="${AZURE_OPENAI_ENDPOINT:-}" \
        azureOpenAIApiKey="${AZURE_OPENAI_API_KEY:-}" \
        jwtSecretKey="${JWT_SECRET_KEY}" \
        appSecretKey="${APP_SECRET_KEY}" \
    --output none

echo "  Template validation passed."

# --- Deploy Infrastructure ---
echo ""
echo "[3/4] Deploying infrastructure (this may take 10-15 minutes)..."
DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group "${RESOURCE_GROUP}" \
    --template-file "${TEMPLATE_FILE}" \
    --parameters "${PARAMETERS_FILE}" \
    --parameters \
        dbAdminLogin="${DB_ADMIN_LOGIN}" \
        dbAdminPassword="${DB_ADMIN_PASSWORD}" \
        azureOpenAIEndpoint="${AZURE_OPENAI_ENDPOINT:-}" \
        azureOpenAIApiKey="${AZURE_OPENAI_API_KEY:-}" \
        jwtSecretKey="${JWT_SECRET_KEY}" \
        appSecretKey="${APP_SECRET_KEY}" \
    --output json)

echo "  Infrastructure deployment completed."

# --- Extract Outputs ---
echo ""
echo "[4/4] Deployment outputs:"
echo "  Backend URL:  $(echo "${DEPLOYMENT_OUTPUT}" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['backendUrl']['value'])" 2>/dev/null || echo 'N/A')"
echo "  Frontend URL: $(echo "${DEPLOYMENT_OUTPUT}" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['frontendUrl']['value'])" 2>/dev/null || echo 'N/A')"
echo "  ACR Server:   $(echo "${DEPLOYMENT_OUTPUT}" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['acrLoginServer']['value'])" 2>/dev/null || echo 'N/A')"
echo "  DB FQDN:      $(echo "${DEPLOYMENT_OUTPUT}" | python3 -c "import sys,json; print(json.load(sys.stdin)['properties']['outputs']['dbFqdn']['value'])" 2>/dev/null || echo 'N/A')"

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Push Docker images to ACR"
echo "  2. Verify health checks"
echo "  3. Run smoke tests"
