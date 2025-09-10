#!/bin/bash

# Deploy Thai Talent ML API to Cloud Run
echo "Deploying Thai Talent ML API using Cloud Build..."

# Submit build using the ML API configuration
gcloud builds submit --config=api/cloudbuild.yaml .

echo "Deployment complete!"
echo "You can view the service at: https://console.cloud.google.com/run/detail/asia-southeast1/thai-talent-ml-api"