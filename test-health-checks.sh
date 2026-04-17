#!/bin/bash

# Real-World Health Check Verification Script
# This script tests the new production-grade health check endpoints

set -e

PLATFORM_URL="http://localhost:8000"
HEALTH_ENDPOINT="${PLATFORM_URL}/health"

echo "================================"
echo "Real-World Health Check Tests"
echo "================================"
echo ""

# Test 1: Platform Root
echo "Test 1: Platform Root Endpoint"
echo "---"
curl -s "$PLATFORM_URL/" | jq .
echo ""

# Test 2: Full Health Check
echo "Test 2: Comprehensive Platform Health Check"
echo "---"
curl -s "$HEALTH_ENDPOINT" | jq .
echo ""

# Test 3: Database Health Only
echo "Test 3: Database Health Status"
echo "---"
curl -s "$HEALTH_ENDPOINT" | jq '.services.database'
echo ""

# Test 4: Redis Health Only
echo "Test 4: Redis Health Status"
echo "---"
curl -s "$HEALTH_ENDPOINT" | jq '.services.redis'
echo ""

# Test 5: Prometheus Health Only
echo "Test 5: Prometheus Health Status"
echo "---"
curl -s "$HEALTH_ENDPOINT" | jq '.services.prometheus'
echo ""

# Test 6: Overall Platform Status
echo "Test 6: Overall Platform Status"
echo "---"
STATUS=$(curl -s "$HEALTH_ENDPOINT" | jq -r '.status')
echo "Platform Status: $STATUS"
echo ""

if [ "$STATUS" = "healthy" ]; then
    echo "✅ Platform is HEALTHY - All services operational"
    exit 0
elif [ "$STATUS" = "degraded" ]; then
    echo "⚠️  Platform is DEGRADED - Some services experiencing latency"
    curl -s "$HEALTH_ENDPOINT" | jq '.services[] | select(.status != "healthy")'
    exit 0
else
    echo "❌ Platform is UNHEALTHY - Critical services down"
    curl -s "$HEALTH_ENDPOINT" | jq '.services[] | select(.status == "unhealthy")'
    exit 1
fi
