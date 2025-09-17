# Vertex AI Deployment Guide from Compute Engine

## Prerequisites
- GCP Project with billing enabled
- Compute Engine instance running your model
- Model trained using `predictive_retention/main.py`

## Step-by-Step Deployment

### 1. On Your Compute Engine Instance

SSH into your Compute Engine instance and navigate to your project:
```bash
cd /path/to/thai-talent-wow
```

### 2. Train Your Model (if not already done)
```bash
python predictive_retention/main.py
```
This creates model files in `output/model/`

### 3. Deploy to Vertex AI

Run the deployment script with your project ID:
```bash
python vertex_ai/deploy_from_compute.py --project-id YOUR_PROJECT_ID --region asia-southeast1
```

This script will:
- Package your model with necessary files
- Upload to Google Cloud Storage
- Create a Vertex AI model
- Deploy to an endpoint
- Save deployment info to `vertex_deployment_info.json`

### 4. Test Your Endpoint
```bash
python vertex_ai/test_vertex_endpoint.py --project-id YOUR_PROJECT_ID
```

## What Happens During Deployment

1. **Model Packaging**: Your trained model (`model.pkl`) and config are packaged with a predictor script
2. **GCS Upload**: Files are uploaded to a GCS bucket (created automatically)
3. **Vertex AI Model**: A model is created in Vertex AI Model Registry
4. **Endpoint Creation**: An HTTP endpoint is created for real-time predictions
5. **Auto-scaling**: The endpoint automatically scales from 1-3 instances based on traffic

## Using the Deployed Model

### From Python Application
```python
from google.cloud import aiplatform

# Initialize
aiplatform.init(project="YOUR_PROJECT_ID", location="asia-southeast1")

# Get endpoint (from vertex_deployment_info.json)
endpoint = aiplatform.Endpoint("projects/123/locations/asia-southeast1/endpoints/456")

# Make prediction
employee_data = {
    "emp_id": "EMP001",
    "job_level": 2,
    "years_at_company": 3.5,
    "performance_score": 4.2,
    "salary_percentile": 0.65,
    # ... other features
}

result = endpoint.predict(instances=[employee_data])
print(f"Termination risk: {result.predictions[0]['risk_level']}")
```

### Via REST API
```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  https://asia-southeast1-aiplatform.googleapis.com/v1/projects/YOUR_PROJECT/locations/asia-southeast1/endpoints/ENDPOINT_ID:predict \
  -d '{
    "instances": [{
      "emp_id": "EMP001",
      "job_level": 2,
      "years_at_company": 3.5
    }]
  }'
```

## Cost Optimization

- **Machine Type**: Uses n1-standard-2 (2 vCPUs, 7.5GB RAM) - suitable for most workloads
- **Auto-scaling**: Scales between 1-3 replicas based on traffic
- **Region**: asia-southeast1 (Singapore) for low latency in Southeast Asia

## Monitoring

View your deployment in GCP Console:
1. Go to Vertex AI > Models
2. Click on your model to see metrics
3. Monitor predictions, latency, and errors

## Updating the Model

To deploy a new version:
1. Train new model: `python predictive_retention/main.py`
2. Deploy with new name: `python vertex_ai/deploy_from_compute.py --project-id YOUR_PROJECT_ID`
3. Traffic split: Gradually route traffic to new version via Console

## Troubleshooting

### Authentication Issues
```bash
gcloud auth application-default login
```

### API Not Enabled
```bash
gcloud services enable aiplatform.googleapis.com
```

### Quota Issues
- Check quotas in GCP Console > IAM & Admin > Quotas
- Request increase if needed

## Clean Up

To avoid charges when not using:
```python
# Undeploy from endpoint (keeps model)
endpoint.undeploy_all()

# Delete endpoint
endpoint.delete()

# Delete model (if no longer needed)
model.delete()
```