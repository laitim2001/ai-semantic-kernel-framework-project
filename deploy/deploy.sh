#!/bin/bash
# =============================================================================
# IPA Platform - Production Deployment Script
#
# This script handles deployment to Azure App Service including:
# - Building Docker image
# - Pushing to Azure Container Registry
# - Deploying to App Service
# - Running database migrations
# - Health check verification
#
# Usage:
#   ./deploy.sh [version] [environment]
#   ./deploy.sh v1.0.0 production
#   ./deploy.sh latest staging
#
# Prerequisites:
#   - Azure CLI installed and logged in
#   - Docker installed
#   - Access to Azure Container Registry
#
# Author: IPA Platform Team
# Version: 1.0.0
# =============================================================================

set -e  # Exit on any error

# =============================================================================
# Configuration
# =============================================================================

VERSION=${1:-latest}
ENVIRONMENT=${2:-production}

# Azure resources
RESOURCE_GROUP="rg-ipa-platform-${ENVIRONMENT}"
APP_NAME="app-ipa-platform-${ENVIRONMENT}"
ACR_NAME="ipaplatformacr"
ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"
IMAGE_NAME="ipa-platform"

# Deployment settings
MAX_RETRIES=5
HEALTH_CHECK_TIMEOUT=300
DEPLOYMENT_SLOT="staging"  # Use staging slot for blue-green deployment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed"
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Azure login
    if ! az account show &> /dev/null; then
        log_error "Not logged in to Azure CLI. Run 'az login' first."
        exit 1
    fi

    log_info "Prerequisites check passed"
}

# =============================================================================
# Build Phase
# =============================================================================

build_image() {
    log_info "Building Docker image: ${IMAGE_NAME}:${VERSION}"

    docker build \
        -t "${IMAGE_NAME}:${VERSION}" \
        -t "${IMAGE_NAME}:latest" \
        -f backend/Dockerfile \
        --build-arg BUILD_VERSION="${VERSION}" \
        --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        backend/

    log_info "Docker image built successfully"
}

# =============================================================================
# Push Phase
# =============================================================================

push_to_acr() {
    log_info "Pushing image to Azure Container Registry..."

    # Login to ACR
    az acr login --name "${ACR_NAME}"

    # Tag for ACR
    docker tag "${IMAGE_NAME}:${VERSION}" "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${VERSION}"
    docker tag "${IMAGE_NAME}:latest" "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest"

    # Push images
    docker push "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${VERSION}"
    docker push "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest"

    log_info "Images pushed to ACR successfully"
}

# =============================================================================
# Deploy Phase
# =============================================================================

deploy_to_staging() {
    log_info "Deploying to staging slot..."

    # Update staging slot with new image
    az webapp config container set \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${APP_NAME}" \
        --slot "${DEPLOYMENT_SLOT}" \
        --docker-custom-image-name "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${VERSION}"

    # Configure environment variables
    az webapp config appsettings set \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${APP_NAME}" \
        --slot "${DEPLOYMENT_SLOT}" \
        --settings \
            ENVIRONMENT="${ENVIRONMENT}" \
            VERSION="${VERSION}" \
            RUN_MIGRATIONS=true

    log_info "Staging deployment completed"
}

run_migrations() {
    log_info "Running database migrations..."

    # Trigger migration run on staging
    MIGRATION_URL="https://${APP_NAME}-${DEPLOYMENT_SLOT}.azurewebsites.net/api/v1/admin/migrate"

    # Wait for app to start
    sleep 30

    # Run migrations (with admin key)
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${MIGRATION_URL}" \
        -H "X-Admin-Key: ${ADMIN_KEY:-default_key}")

    if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 404 ]; then
        log_info "Migrations completed or not needed"
    else
        log_warn "Migration returned status ${HTTP_STATUS} - may need manual review"
    fi
}

# =============================================================================
# Verification Phase
# =============================================================================

health_check() {
    log_info "Running health checks..."

    STAGING_URL="https://${APP_NAME}-${DEPLOYMENT_SLOT}.azurewebsites.net/health"
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${STAGING_URL}" --max-time 10)

        if [ "$HTTP_STATUS" -eq 200 ]; then
            log_info "Health check passed!"
            return 0
        fi

        RETRY_COUNT=$((RETRY_COUNT + 1))
        log_warn "Health check attempt ${RETRY_COUNT}/${MAX_RETRIES} failed (status: ${HTTP_STATUS})"
        sleep 10
    done

    log_error "Health check failed after ${MAX_RETRIES} attempts"
    return 1
}

smoke_tests() {
    log_info "Running smoke tests..."

    BASE_URL="https://${APP_NAME}-${DEPLOYMENT_SLOT}.azurewebsites.net"

    # Test critical endpoints
    ENDPOINTS=(
        "/health"
        "/api/v1/workflows/"
        "/api/v1/agents/"
    )

    for endpoint in "${ENDPOINTS[@]}"; do
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${endpoint}" --max-time 10)

        if [ "$HTTP_STATUS" -ge 200 ] && [ "$HTTP_STATUS" -lt 500 ]; then
            log_info "✓ ${endpoint} - ${HTTP_STATUS}"
        else
            log_error "✗ ${endpoint} - ${HTTP_STATUS}"
            return 1
        fi
    done

    log_info "Smoke tests passed!"
}

# =============================================================================
# Swap Phase (Blue-Green Deployment)
# =============================================================================

swap_slots() {
    log_info "Swapping staging to production..."

    az webapp deployment slot swap \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${APP_NAME}" \
        --slot "${DEPLOYMENT_SLOT}" \
        --target-slot production

    log_info "Slot swap completed - new version is now live!"
}

# =============================================================================
# Rollback
# =============================================================================

rollback() {
    log_error "Deployment failed - initiating rollback..."

    # Swap back to previous version
    az webapp deployment slot swap \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${APP_NAME}" \
        --slot production \
        --target-slot "${DEPLOYMENT_SLOT}"

    log_info "Rollback completed"
    exit 1
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo "=============================================="
    echo "IPA Platform Deployment"
    echo "=============================================="
    echo "Version:     ${VERSION}"
    echo "Environment: ${ENVIRONMENT}"
    echo "Timestamp:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "=============================================="

    # Pre-deployment
    check_prerequisites

    # Build and push
    build_image
    push_to_acr

    # Deploy to staging
    deploy_to_staging
    run_migrations

    # Verify
    if ! health_check; then
        rollback
    fi

    if ! smoke_tests; then
        rollback
    fi

    # Swap to production
    swap_slots

    # Final verification
    log_info "Running final health check on production..."
    PRODUCTION_URL="https://${APP_NAME}.azurewebsites.net/health"
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${PRODUCTION_URL}" --max-time 10)

    if [ "$HTTP_STATUS" -eq 200 ]; then
        echo ""
        echo "=============================================="
        log_info "DEPLOYMENT SUCCESSFUL!"
        echo "=============================================="
        echo "Version ${VERSION} is now live at:"
        echo "https://${APP_NAME}.azurewebsites.net"
        echo "=============================================="
    else
        log_error "Final health check failed - manual intervention may be required"
        exit 1
    fi
}

# Run main function
main "$@"
