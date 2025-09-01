# GCP Deployment Guide - Skill Promotion Analytics

This guide shows how to deploy your skill promotion analytics as a containerized job on Google Cloud Platform.

## Architecture

- **Cloud Run Jobs**: Execute analytics as batch jobs
- **Cloud Storage**: Store input data and results
- **Container Registry**: Host Docker images
- **Service Account**: Secure access to GCP services

## Quick Deployment

### 1. Prerequisites

```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Login and set project
gcloud auth login
gcloud config set project th-ai-talent-wow
```

### 2. Run Setup Script

```bash
cd thai-talent-wow
./deploy/setup-gcp.sh
```

This script will:
- Enable required APIs
- Create Cloud Storage bucket
- Create service account with proper permissions
- Upload mock data to Cloud Storage
- Build and push Docker image

### 3. Deploy and Execute Job

```bash
# Deploy the job
gcloud run jobs replace deploy/cloud-run-job.yaml --region=asia-southeast1

# Execute the analytics job
gcloud run jobs execute skill-analytics-job --region=asia-southeast1 --wait

# Check the results
gsutil ls gs://th-ai-talent-data/output/
```

## Manual Steps

If you prefer manual setup:

### 1. Enable APIs

```bash
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Create Storage and Upload Data

```bash
# Create bucket
gsutil mb -l asia-southeast1 gs://th-ai-talent-data

# Upload input data
gsutil -m cp -r mock_data/* gs://th-ai-talent-data/mock_data/
```

### 3. Build and Push Container

```bash
# Build image
docker build -f Dockerfile.skill-analytics -t gcr.io/th-ai-talent-wow/skill-analytics:latest .

# Push to registry
docker push gcr.io/th-ai-talent-wow/skill-analytics:latest
```

### 4. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create skill-analytics-sa \
    --display-name="Skill Analytics Service Account"

# Grant storage permissions
gcloud projects add-iam-policy-binding th-ai-talent-wow \
    --member="serviceAccount:skill-analytics-sa@th-ai-talent-wow.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

### 5. Deploy Job

```bash
# Update PROJECT_ID in cloud-run-job.yaml, then:
gcloud run jobs replace deploy/cloud-run-job.yaml --region=asia-southeast1
```

## Monitoring and Results

### Check Job Status

```bash
# List executions
gcloud run jobs executions list --job=skill-analytics-job --region=asia-southeast1

# Get logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=skill-analytics-job" --limit=50
```

### Download Results

```bash
# Download all results
gsutil -m cp -r gs://th-ai-talent-data/output/ ./results/

# View specific result
gsutil cat gs://th-ai-talent-data/output/employee_skill_gap_result.json
```

## Output Files

The job generates these analytics files:

1. **employee_skill_gap_result.json** - Individual employee skill analysis
2. **department_skill_gap_result.json** - Department-level skill gaps
3. **rotation_skill_gap_result.json** - Cross-department rotation opportunities
4. **promotion_analysis_results.json** - Promotion readiness categories

## Cost Optimization

- **Scheduled Runs**: Use Cloud Scheduler for periodic execution
- **Resource Limits**: Adjust CPU/memory in `cloud-run-job.yaml`
- **Regional Storage**: Use regional buckets for better performance
- **Lifecycle Policies**: Set up automatic deletion of old results

## Production Considerations

1. **Data Security**: Use VPC Service Controls for sensitive data
2. **Monitoring**: Set up alerting with Cloud Monitoring
3. **Backup**: Regular backup of critical input data
4. **Version Control**: Tag Docker images with versions
5. **Access Control**: Use IAM conditions for fine-grained permissions

## Troubleshooting

### Common Issues

1. **Permission Denied**: Check service account has storage.objectAdmin role
2. **Memory Errors**: Increase memory limit in job configuration
3. **Timeout**: Extend task-timeout in job spec
4. **Data Not Found**: Verify data exists in Cloud Storage

### Debug Commands

```bash
# Check job configuration
gcloud run jobs describe skill-analytics-job --region=asia-southeast1

# View recent logs
gcloud logging read "resource.type=cloud_run_job" --limit=10

# Test container locally
docker run --rm -e GCS_BUCKET_NAME=th-ai-talent-data gcr.io/th-ai-talent-wow/skill-analytics:latest
```

## Next Steps

- Set up Cloud Scheduler for automated runs
- Create CI/CD pipeline for deployments
- Add data validation before processing
- Implement result notifications (email/Slack)
- Scale to multiple regions if needed