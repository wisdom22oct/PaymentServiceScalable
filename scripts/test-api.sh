#!/bin/bash

# Test Payment Service API endpoints

# Get service URL
if command -v minikube &> /dev/null; then
    BASE_URL=$(minikube service payment-service --url)
else
    BASE_URL="http://localhost:8003"
fi

echo "Testing Payment Service API at: $BASE_URL"
echo ""

# Test 1: Health Check
echo "1. Health Check"
curl -s "$BASE_URL/health" | jq '.'
echo ""

# Test 2: Process Payment
echo "2. Process Payment (with idempotency key)"
PAYMENT_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/payments/charge" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: test-key-$(date +%s)" \
    -d '{
        "order_id": "ORD_TEST_001",
        "amount": 1575.00,
        "method": "CREDIT_CARD"
    }')
echo "$PAYMENT_RESPONSE" | jq '.'
PAYMENT_ID=$(echo "$PAYMENT_RESPONSE" | jq -r '.payment_id')
echo ""

# Test 3: Get Payment Details
echo "3. Get Payment Details"
curl -s "$BASE_URL/v1/payments/$PAYMENT_ID" | jq '.'
echo

# Test 4: Get Payments by Order
echo "4. Get Payments by Order"
curl -s "$BASE_URL/v1/payments/order/ORD_TEST_001" | jq '.'
echo

# Test 5: List Successful Payments
echo "5. List Successful Payments"
curl -s "$BASE_URL/v1/payments?status=SUCCESS&limit=5" | jq '.'
echo

# Test 6: Process Refund (only if payment was successful)
if [ -z "$PAYMENT_ID" ]; then
  echo "6. Process Refund"
  curl -s -X POST "$BASE_URL/v1/payments/refund" \
    -H "Content-Type: application/json" \
    -d '{
      "payment_id": "$PAYMENT_ID",
      "reason": "Test refund"
    }' | jq '.'
  echo
fi

# Test 7: Verify Refund
if [ -z "$PAYMENT_ID" ]; then
  echo "7. Verify Refund Status"
  curl -s "$BASE_URL/v1/payments/$PAYMENT_ID" | jq '.'
  echo
fi

echo "Api testing completed!"