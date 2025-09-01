#!/bin/bash

# Configuration
PROJECT_ID="th-ai-talent-wow"
REGION="asia-southeast1"
SERVICE_NAME="talent-analytics-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/talent-api:latest"

echo "🚀 Deploying Talent Analytics API to Google Cloud Run"
echo "=================================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Set project
echo "1️⃣ Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Create simple Dockerfile for demo API
echo "2️⃣ Creating Dockerfile for demo API..."
cat > vertex_ai/Dockerfile.demo <<EOF
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn pydantic

# Copy demo API
COPY vertex_ai/demo_api.py ./

# Expose port
EXPOSE 8080

# Run the API
CMD ["python", "demo_api.py"]
EOF

# Build Docker image
echo "3️⃣ Building Docker image..."
docker build -f vertex_ai/Dockerfile.demo -t ${IMAGE_NAME} .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    echo "   Make sure Docker is running"
    exit 1
fi

# Push to Container Registry
echo "4️⃣ Pushing image to Container Registry..."
docker push ${IMAGE_NAME}

if [ $? -ne 0 ]; then
    echo "❌ Docker push failed"
    echo "   You may need to configure Docker for GCR:"
    echo "   gcloud auth configure-docker"
    exit 1
fi

# Deploy to Cloud Run
echo "5️⃣ Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10 \
    --min-instances 1

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ DEPLOYMENT SUCCESSFUL!"
    echo "=================================================="
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')
    
    echo "🌐 Your API is live at: ${SERVICE_URL}"
    echo ""
    echo "📊 Test endpoints:"
    echo "   ${SERVICE_URL}/health"
    echo "   ${SERVICE_URL}/docs"
    echo ""
    echo "🧪 Test with curl:"
    echo "curl -X POST \"${SERVICE_URL}/predict/retention\" \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"employees\": [{\"employee_id\": \"EMP001\", \"performance_score\": 4.2}]}'"
    echo ""
    echo "🎉 Your talent analytics API is now globally accessible!"
else
    echo "❌ Deployment failed"
    echo "   Check the error messages above"
fi