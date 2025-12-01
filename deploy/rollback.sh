#!/bin/bash
# =============================================================================
# IPA Platform - Rollback Script
#
# Quickly rollback to previous deployment using slot swap.
#
# Usage:
#   ./rollback.sh [environment]
#   ./rollback.sh production
#
# Author: IPA Platform Team
# Version: 1.0.0
# =============================================================================

set -e

ENVIRONMENT=${1:-production}
RESOURCE_GROUP="rg-ipa-platform-${ENVIRONMENT}"
APP_NAME="app-ipa-platform-${ENVIRONMENT}"
DEPLOYMENT_SLOT="staging"

echo "=============================================="
echo "IPA Platform Rollback"
echo "=============================================="
echo "Environment: ${ENVIRONMENT}"
echo "Timestamp:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=============================================="

echo "[INFO] Initiating rollback by swapping production with staging..."

az webapp deployment slot swap \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${APP_NAME}" \
    --slot production \
    --target-slot "${DEPLOYMENT_SLOT}"

echo "[INFO] Rollback completed!"

# Health check
echo "[INFO] Verifying rollback..."
sleep 10

PRODUCTION_URL="https://${APP_NAME}.azurewebsites.net/health"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${PRODUCTION_URL}" --max-time 10)

if [ "$HTTP_STATUS" -eq 200 ]; then
    echo "[INFO] Rollback successful - application is healthy"
else
    echo "[WARN] Health check returned ${HTTP_STATUS} - please verify manually"
fi

echo "=============================================="
