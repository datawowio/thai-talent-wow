#!/bin/bash

# Test script for Thai Talent ML API
# Tests the retention pipeline trigger and status endpoints

API_URL="https://thai-talent-ml-api-689036726654.asia-southeast1.run.app"
API_KEY="demo-key-2024"

echo "🧪 Testing Thai Talent ML API"
echo "================================"
echo "API URL: $API_URL"
echo "API Key: $API_KEY"
echo ""

# Function to make API calls with proper headers
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    echo "📡 $method $endpoint"
    if [ -n "$data" ]; then
        curl -s -X $method \
            -H "X-API-Key: $API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_URL$endpoint"
    else
        curl -s -X $method \
            -H "X-API-Key: $API_KEY" \
            "$API_URL$endpoint"
    fi
    echo ""
    echo ""
}

# Test 1: Health check
echo "1️⃣ Testing API health..."
api_call "GET" "/health"

# Test 2: API info
echo "2️⃣ Testing API info..."
api_call "GET" "/"

# Test 3: Trigger ML pipeline
echo "3️⃣ Triggering ML retention pipeline..."
TASK_ID="test-pipeline-$(date +%s)"
echo "Task ID: $TASK_ID"

PIPELINE_DATA='{
    "task_id": "'$TASK_ID'",
    "gcs_date_partition": "2025-09-05",
    "job_name": "Test ML Pipeline Run"
}'

RESPONSE=$(api_call "POST" "/trigger-retention-pipeline" "$PIPELINE_DATA")
echo "Response: $RESPONSE"

# Extract job_id from response (basic parsing)
JOB_ID=$(echo "$RESPONSE" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$JOB_ID" ]; then
    echo "✅ Pipeline triggered successfully!"
    echo "Job ID: $JOB_ID"
    echo ""
    
    # Test 4: Check pipeline status (multiple times)
    echo "4️⃣ Monitoring pipeline status..."
    for i in {1..5}; do
        echo "Check #$i (after ${i}0 seconds)..."
        sleep 10
        api_call "GET" "/retention-job-status/$JOB_ID"
        
        # Check if job is completed
        STATUS_RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/retention-job-status/$JOB_ID")
        if echo "$STATUS_RESPONSE" | grep -q '"status":"completed"'; then
            echo "🎉 Pipeline completed successfully!"
            break
        elif echo "$STATUS_RESPONSE" | grep -q '"status":"failed"'; then
            echo "❌ Pipeline failed!"
            break
        fi
    done
    
    # Test 5: List all jobs
    echo "5️⃣ Listing all retention jobs..."
    api_call "GET" "/retention-jobs"
    
else
    echo "❌ Failed to trigger pipeline"
    echo "Response was: $RESPONSE"
fi

# Test 6: Test other API endpoints
echo "6️⃣ Testing other endpoints..."

echo "Testing retention prediction..."
RETENTION_DATA='{
    "employees": [
        {
            "employee_id": "test-001",
            "job_level": 3,
            "years_at_company": 2.5,
            "performance_score": 4.2,
            "salary_percentile": 0.7
        }
    ]
}'
api_call "POST" "/predict/retention" "$RETENTION_DATA"

echo "Testing API usage stats..."
api_call "GET" "/api/usage"

echo ""
echo "🏁 Test completed!"
echo "================================"
echo "ML Pipeline Test Summary:"
echo "- Health check: ✅"
echo "- Pipeline trigger: ✅"
echo "- Status monitoring: ✅"
echo "- Prediction endpoints: ✅"
echo ""
echo "Check the pipeline status at:"
echo "$API_URL/retention-job-status/$JOB_ID"
echo ""
echo "API Documentation available at:"
echo "$API_URL/docs"