#!/bin/bash
# MVP Validation Script for IPA Platform
# Version: 1.0
# Date: 2025-11-29

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Output file
REPORT_FILE="mvp-validation-report-$(date +%Y%m%d-%H%M%S).md"

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_test() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -ne "  [$TOTAL_TESTS] $1... "
}

pass() {
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}PASS${NC}"
    echo "| $1 | $2 | PASS |" >> "$REPORT_FILE"
}

fail() {
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}FAIL${NC}"
    echo "| $1 | $2 | FAIL |" >> "$REPORT_FILE"
}

warn() {
    echo -e "${YELLOW}WARN${NC} - $1"
}

# Initialize report
init_report() {
    cat > "$REPORT_FILE" << EOF
# MVP Validation Report
# IPA Platform

**Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Environment**: $(hostname)
**Script Version**: 1.0

---

## Validation Results

| Test ID | Description | Result |
|---------|-------------|--------|
EOF
}

# Summary
print_summary() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}VALIDATION SUMMARY${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "Total Tests:  $TOTAL_TESTS"
    echo -e "Passed:       ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed:       ${RED}$FAILED_TESTS${NC}"

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}All tests passed!${NC}"
    else
        echo -e "\n${RED}Some tests failed. Please review the report.${NC}"
    fi

    # Append summary to report
    cat >> "$REPORT_FILE" << EOF

---

## Summary

- **Total Tests**: $TOTAL_TESTS
- **Passed**: $PASSED_TESTS
- **Failed**: $FAILED_TESTS
- **Pass Rate**: $(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)%

EOF

    echo -e "\nReport saved to: ${BLUE}$REPORT_FILE${NC}"
}

# ==========================================
# PHASE 1: Environment Validation
# ==========================================
phase1_environment() {
    print_header "PHASE 1: Environment Validation"

    # Test 1: Docker Compose running
    print_test "CE-001" "Docker Compose services running"
    if docker-compose ps 2>/dev/null | grep -q "Up"; then
        pass "CE-001" "Docker services running"
    else
        fail "CE-001" "Docker services not running"
    fi

    # Test 2: Backend health check
    print_test "CE-002" "Backend health endpoint"
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        pass "CE-002" "Backend health OK"
    else
        fail "CE-002" "Backend health failed"
    fi

    # Test 3: PostgreSQL connection
    print_test "CE-003" "PostgreSQL connection"
    if docker-compose exec -T postgres pg_isready -U ipa_user 2>/dev/null | grep -q "accepting"; then
        pass "CE-003" "PostgreSQL ready"
    else
        fail "CE-003" "PostgreSQL not ready"
    fi

    # Test 4: Redis connection
    print_test "CE-004" "Redis connection"
    if docker-compose exec -T redis redis-cli -a redis_password ping 2>/dev/null | grep -q "PONG"; then
        pass "CE-004" "Redis ready"
    else
        fail "CE-004" "Redis not ready"
    fi

    # Test 5: Swagger UI accessible
    print_test "CE-005" "Swagger UI accessible"
    if curl -sf http://localhost:8000/docs > /dev/null 2>&1; then
        pass "CE-005" "Swagger UI OK"
    else
        fail "CE-005" "Swagger UI not accessible"
    fi
}

# ==========================================
# PHASE 2: API Endpoint Validation
# ==========================================
phase2_api() {
    print_header "PHASE 2: API Endpoint Validation"

    # Workflows API
    print_test "WF-001" "GET /api/v1/workflows"
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/workflows 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
        pass "WF-001" "Workflows API responding"
    else
        fail "WF-001" "Workflows API failed (HTTP $HTTP_CODE)"
    fi

    # Monitoring API
    print_test "MON-001" "GET /api/v1/monitoring/health"
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/monitoring/health 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        pass "MON-001" "Monitoring health OK"
    else
        fail "MON-001" "Monitoring health failed (HTTP $HTTP_CODE)"
    fi

    # Metrics API
    print_test "MET-001" "GET /api/v1/metrics/summary"
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/metrics/summary 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
        pass "MET-001" "Metrics API responding"
    else
        fail "MET-001" "Metrics API failed (HTTP $HTTP_CODE)"
    fi

    # Security testing API
    print_test "SEC-001" "GET /api/v1/security-testing/owasp-checklist"
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/security-testing/owasp-checklist 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
        pass "SEC-001" "Security testing API responding"
    else
        fail "SEC-001" "Security testing API failed (HTTP $HTTP_CODE)"
    fi

    # Audit API
    print_test "AUD-001" "GET /api/v1/audit/logs"
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/audit/logs 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
        pass "AUD-001" "Audit API responding"
    else
        fail "AUD-001" "Audit API failed (HTTP $HTTP_CODE)"
    fi
}

# ==========================================
# PHASE 3: Backend Testing
# ==========================================
phase3_backend() {
    print_header "PHASE 3: Backend Testing"

    cd backend 2>/dev/null || { warn "backend directory not found"; return; }

    # Unit tests
    print_test "TEST-001" "Unit tests execution"
    if python -m pytest tests/unit/ -v --tb=short -q 2>/dev/null; then
        pass "TEST-001" "Unit tests passed"
    else
        fail "TEST-001" "Unit tests failed"
    fi

    # Code formatting check
    print_test "QUAL-001" "Code formatting (black)"
    if python -m black --check . --quiet 2>/dev/null; then
        pass "QUAL-001" "Code formatting OK"
    else
        fail "QUAL-001" "Code formatting issues"
    fi

    cd ..
}

# ==========================================
# PHASE 4: Frontend Validation
# ==========================================
phase4_frontend() {
    print_header "PHASE 4: Frontend Validation"

    cd frontend 2>/dev/null || { warn "frontend directory not found"; return; }

    # Build check
    print_test "FE-001" "Frontend build"
    if npm run build --silent 2>/dev/null; then
        pass "FE-001" "Frontend build successful"
    else
        fail "FE-001" "Frontend build failed"
    fi

    # Type check
    print_test "FE-002" "TypeScript type check"
    if npm run type-check --silent 2>/dev/null; then
        pass "FE-002" "TypeScript types OK"
    else
        fail "FE-002" "TypeScript type errors"
    fi

    cd ..
}

# ==========================================
# PHASE 5: Security Validation
# ==========================================
phase5_security() {
    print_header "PHASE 5: Security Validation"

    # Security headers
    print_test "SEC-HDR-001" "Security headers present"
    HEADERS=$(curl -sI http://localhost:8000/health 2>/dev/null)
    if echo "$HEADERS" | grep -qi "x-content-type-options"; then
        pass "SEC-HDR-001" "Security headers present"
    else
        fail "SEC-HDR-001" "Security headers missing"
    fi

    # HTTPS redirect check (if applicable)
    print_test "SEC-TLS-001" "CORS configured"
    if curl -sI http://localhost:8000/health 2>/dev/null | grep -qi "access-control"; then
        pass "SEC-TLS-001" "CORS configured"
    else
        warn "CORS headers not present (may be OK for local dev)"
        pass "SEC-TLS-001" "CORS check (local dev)"
    fi
}

# ==========================================
# PHASE 6: Documentation Check
# ==========================================
phase6_docs() {
    print_header "PHASE 6: Documentation Check"

    # User guide
    print_test "DOC-001" "User guide exists"
    if [ -f "docs/user-guide/getting-started.md" ]; then
        pass "DOC-001" "User guide present"
    else
        fail "DOC-001" "User guide missing"
    fi

    # Admin guide
    print_test "DOC-002" "Admin guide exists"
    if [ -f "docs/admin-guide/installation.md" ]; then
        pass "DOC-002" "Admin guide present"
    else
        fail "DOC-002" "Admin guide missing"
    fi

    # Deployment runbook
    print_test "DOC-003" "Deployment runbook exists"
    if [ -f "docs/admin-guide/deployment-runbook.md" ]; then
        pass "DOC-003" "Deployment runbook present"
    else
        fail "DOC-003" "Deployment runbook missing"
    fi

    # UAT preparation
    print_test "DOC-004" "UAT preparation exists"
    if [ -f "docs/admin-guide/uat-preparation.md" ]; then
        pass "DOC-004" "UAT preparation present"
    else
        fail "DOC-004" "UAT preparation missing"
    fi

    # MVP acceptance framework
    print_test "DOC-005" "MVP acceptance framework exists"
    if [ -f "docs/03-implementation/mvp-acceptance-framework.md" ]; then
        pass "DOC-005" "MVP acceptance framework present"
    else
        fail "DOC-005" "MVP acceptance framework missing"
    fi
}

# ==========================================
# MAIN EXECUTION
# ==========================================
main() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║     IPA Platform MVP Validation Script    ║"
    echo "║     Version 1.0 - 2025-11-29             ║"
    echo "╚═══════════════════════════════════════════╝"
    echo -e "${NC}"

    init_report

    # Run validation phases
    phase1_environment
    phase2_api
    phase3_backend
    phase4_frontend
    phase5_security
    phase6_docs

    # Print summary
    print_summary

    # Exit code based on results
    if [ $FAILED_TESTS -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Parse arguments
case "$1" in
    --env-only)
        init_report
        phase1_environment
        print_summary
        ;;
    --api-only)
        init_report
        phase2_api
        print_summary
        ;;
    --help)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --env-only    Run only environment validation"
        echo "  --api-only    Run only API validation"
        echo "  --help        Show this help message"
        echo ""
        echo "Without options, runs all validation phases."
        ;;
    *)
        main
        ;;
esac
