#!/bin/bash

# Configuration
PROJECT_ID="th-ai-talent-wow"
REGION="asia-southeast1"
SERVICE_NAME="skill-analytics"
BUCKET_NAME="th-ai-talent-data"
SA_NAME="skill-analytics-sa"

# Set project
echo "Setting up GCP project: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Enable APIs
echo "Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Create Cloud Storage bucket
echo "Creating Cloud Storage bucket: $BUCKET_NAME"
gsutil mb -l $REGION gs://$BUCKET_NAME || echo "Bucket already exists"

# Create service account
echo "Creating service account: $SA_NAME"
gcloud iam service-accounts create $SA_NAME \
    --display-name="Skill Analytics Service Account" || echo "Service account already exists"

# Grant permissions
echo "Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.invoker"

# Upload mock data to Cloud Storage
echo "Uploading mock data to Cloud Storage..."
gsutil -m cp -r mock_data/* gs://$BUCKET_NAME/mock_data/

# Build and push Docker image
echo "Building Docker image..."
docker build -f Dockerfile.skill-analytics -t gcr.io/$PROJECT_ID/skill-analytics:latest .

echo "Pushing Docker image..."
docker push gcr.io/$PROJECT_ID/skill-analytics:latest

echo "Setup complete!"
echo "Next steps:"
echo "1. Deploy as Cloud Run Job: gcloud run jobs replace deploy/cloud-run-job.yaml --region=$REGION"  
echo "2. Execute job: gcloud run jobs execute skill-analytics-job --region=$REGION"
echo "3. Check results: gsutil ls gs://$BUCKET_NAME/output/"