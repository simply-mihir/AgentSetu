#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# AgentSetu Production Readiness Check
# Run before any production deployment to catch misconfigurations.
# Usage: ./scripts/production-check.sh [BASE_URL]
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
PASS=0
FAIL=0
WARN=0

check() {
    local label="$1"
    local result="$2"  # 0 = pass, 1 = fail, 2 = warn
    if [ "$result" -eq 0 ]; then
        echo "  ✅ $label"
        PASS=$((PASS + 1))
    elif [ "$result" -eq 2 ]; then
        echo "  ⚠️  $label"
        WARN=$((WARN + 1))
    else
        echo "  ❌ $label"
        FAIL=$((FAIL + 1))
    fi
}

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  AgentSetu Production Readiness Check                      ║"
echo "║  Target: $BASE_URL"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── 1. Health endpoints ──────────────────────────────────────────────────────
echo "── Health Checks ──"
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null || echo "000")
check "GET /health returns 200" $([ "$HEALTH" = "200" ] && echo 0 || echo 1)

READY=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/ready" 2>/dev/null || echo "000")
check "GET /ready returns 200" $([ "$READY" = "200" ] && echo 0 || echo 1)

# ── 2. Security headers ─────────────────────────────────────────────────────
echo ""
echo "── Security Headers ──"
HEADERS=$(curl -s -D - -o /dev/null "$BASE_URL/health" 2>/dev/null)

echo "$HEADERS" | grep -qi "x-content-type-options: nosniff"
check "X-Content-Type-Options: nosniff" $?

echo "$HEADERS" | grep -qi "x-frame-options: deny"
check "X-Frame-Options: DENY" $?

echo "$HEADERS" | grep -qi "referrer-policy"
check "Referrer-Policy present" $?

echo "$HEADERS" | grep -qi "x-request-id"
check "X-Request-ID present" $?

echo "$HEADERS" | grep -qi "cache-control: no-store"
check "Cache-Control: no-store" $?

# ── 3. Error format ─────────────────────────────────────────────────────────
echo ""
echo "── Error Format ──"
ERR_BODY=$(curl -s "$BASE_URL/v1/transactions/" 2>/dev/null)
echo "$ERR_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'error' in d and 'code' in d['error']" 2>/dev/null
check "401 returns standard error envelope" $?

# ── 4. Docs disabled in production ───────────────────────────────────────────
echo ""
echo "── Production Config ──"
DOCS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/docs" 2>/dev/null || echo "000")
if [ "$DOCS" = "404" ] || [ "$DOCS" = "000" ]; then
    check "/docs disabled (production)" 0
else
    check "/docs still accessible (should be disabled in production)" 2
fi

# ── 5. CORS check ───────────────────────────────────────────────────────────
CORS_HEADER=$(curl -s -H "Origin: http://evil.com" -D - -o /dev/null "$BASE_URL/health" 2>/dev/null | grep -i "access-control-allow-origin" || true)
if echo "$CORS_HEADER" | grep -q "evil.com"; then
    check "CORS does NOT allow arbitrary origins" 1
elif echo "$CORS_HEADER" | grep -q "\*"; then
    check "CORS wildcard (ok for dev, NOT for production)" 2
else
    check "CORS restricted to configured origins" 0
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed, $WARN warnings"
if [ "$FAIL" -gt 0 ]; then
    echo "  ❌ NOT READY FOR PRODUCTION"
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo "  ⚠️  REVIEW WARNINGS BEFORE PRODUCTION"
    exit 0
else
    echo "  ✅ PRODUCTION READY"
    exit 0
fi
