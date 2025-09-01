# Real-time Predictions with Vertex AI

This guide shows how to deploy your batch analytics as real-time prediction endpoints using Vertex AI.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client App    │───▶│  FastAPI        │───▶│  Vertex AI      │
│   (Web/Mobile)  │    │  Real-time API  │    │  Endpoints      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                        ┌─────────────────┐    ┌─────────────────┐
                        │   Monitoring    │    │   Model         │
                        │   & Logging     │    │   Registry      │
                        └─────────────────┘    └─────────────────┘
```

## Available Models

1. **Retention Predictor** - Predicts employee termination probability
2. **Skill Gap Analyzer** - Analyzes skill gaps in real-time  
3. **Promotion Predictor** - Evaluates promotion readiness

## Quick Deployment

### 1. Install Dependencies

```bash
cd vertex_ai
pip install -r requirements.txt
```

### 2. Deploy All Models to Vertex AI

```bash
# Deploy all models (retention, skill gap, promotion)
python deploy_models.py \
  --project-id th-ai-talent-wow \
  --region asia-southeast1 \
  --models all \
  --test
```

### 3. Start Real-time API

```bash
# Start the FastAPI server
python realtime_api.py
```

API will be available at: `http://localhost:8080`

API Documentation: `http://localhost:8080/docs`

## API Endpoints

### Employee Retention Prediction

```bash
curl -X POST "http://localhost:8080/predict/retention" \
  -H "Content-Type: application/json" \
  -d '{
    "employees": [
      {
        "employee_id": "EMP001",
        "job_level": 2,
        "years_at_company": 3.5,
        "performance_score": 4.2,
        "salary_percentile": 0.65,
        "skill_diversity": 8
      }
    ]
  }'
```

**Response:**
```json
{
  "status": "success",
  "predictions": [
    {
      "employee_id": "EMP001",
      "termination_probability": 0.23,
      "predicted_termination": false,
      "risk_level": "LOW",
      "confidence": 0.54
    }
  ],
  "model_version": "retention-v1"
}
```

### Skill Gap Analysis

```bash
curl -X POST "http://localhost:8080/predict/skill-gap" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_ids": ["EMP001", "EMP002"]
  }'
```

**Response:**
```json
{
  "status": "success",
  "predictions": [
    {
      "employee_id": "EMP001",
      "current_position": "Software Engineer (L2)",
      "next_position": "Senior Software Engineer (L3)",
      "employee_skills": [
        {"skill_name": "Python", "skill_score": 4},
        {"skill_name": "JavaScript", "skill_score": 3}
      ],
      "current_missing_skills": ["Docker", "Kubernetes"],
      "next_missing_skills": ["System Design", "Leadership"],
      "skill_gap_score": 25,
      "readiness_score": 75
    }
  ]
}
```

### Promotion Readiness

```bash
curl -X POST "http://localhost:8080/predict/promotion" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_ids": ["EMP001", "EMP002"]
  }'
```

**Response:**
```json
{
  "status": "success",
  "predictions": [
    {
      "employee_id": "EMP001",
      "promotion_category": "On Track",
      "promotion_score": 85,
      "recent_evaluation_score": 4.5,
      "evaluation_trend": 0.2
    }
  ]
}
```

### Comprehensive Analysis

```bash
curl -X POST "http://localhost:8080/predict/comprehensive" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_ids": ["EMP001"],
    "include_retention": true,
    "include_skill_gap": true, 
    "include_promotion": true
  }'
```

## Model Details

### Retention Predictor
- **Input**: Employee features (job level, tenure, performance, etc.)
- **Output**: Termination probability (0-1), risk level, confidence
- **Use Cases**: Identify at-risk employees, plan retention strategies

### Skill Gap Analyzer  
- **Input**: Employee ID
- **Output**: Current skills, missing skills, readiness scores
- **Use Cases**: Training recommendations, career planning

### Promotion Predictor
- **Input**: Employee ID  
- **Output**: Promotion category, readiness score, evaluation trends
- **Use Cases**: Succession planning, talent management

## Production Deployment

### Deploy API as Cloud Run Service

```bash
# Build container
docker build -t gcr.io/th-ai-talent-wow/realtime-api:latest -f vertex_ai/Dockerfile .

# Push to registry
docker push gcr.io/th-ai-talent-wow/realtime-api:latest

# Deploy to Cloud Run
gcloud run deploy realtime-api \
  --image gcr.io/th-ai-talent-wow/realtime-api:latest \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2
```

### Environment Variables

```bash
export GOOGLE_CLOUD_PROJECT="th-ai-talent-wow"
export GOOGLE_CLOUD_REGION="asia-southeast1"
```

## Monitoring & Scaling

### Model Performance Monitoring

```bash
# Check endpoint metrics
gcloud ai endpoints describe ENDPOINT_ID --region=asia-southeast1

# View prediction logs
gcloud logging read "resource.type=aiplatform_endpoint" --limit=50
```

### Auto-scaling Configuration

Models automatically scale based on traffic:
- **Min replicas**: 1 (always available)
- **Max replicas**: 3 (scales up during high load)
- **Machine type**: n1-standard-2 (adjustable based on needs)

## Cost Optimization

### Prediction Costs
- **Retention Model**: ~$0.50 per 1000 predictions
- **Skill Models**: ~$0.30 per 1000 predictions  
- **Storage**: ~$0.02 per GB per month

### Optimization Tips
1. **Batch predictions** when possible
2. **Cache results** for frequently queried employees
3. **Use regional endpoints** to reduce latency
4. **Monitor usage** with Cloud Monitoring

## Integration Examples

### Python Client

```python
import requests

# Predict retention risk
response = requests.post(
    "https://your-api-url/predict/retention",
    json={
        "employees": [{
            "employee_id": "EMP001",
            "job_level": 2,
            "performance_score": 4.2
        }]
    }
)

result = response.json()
print(f"Termination risk: {result['predictions'][0]['risk_level']}")
```

### JavaScript Client

```javascript
// Fetch comprehensive analytics
const response = await fetch('https://your-api-url/predict/comprehensive', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    employee_ids: ['EMP001', 'EMP002'],
    include_retention: true,
    include_skill_gap: true,
    include_promotion: true
  })
});

const analytics = await response.json();
console.log('Employee Analytics:', analytics.employee_analytics);
```

## Troubleshooting

### Common Issues

1. **Model Not Found**: Check if models are deployed to correct region
2. **Permission Denied**: Verify service account has `aiplatform.user` role
3. **Timeout Errors**: Increase request timeout or check model health

### Debug Commands

```bash
# List all endpoints
gcloud ai endpoints list --region=asia-southeast1

# Check model deployment status
gcloud ai models list --region=asia-southeast1

# View API logs
gcloud run logs tail realtime-api --region=asia-southeast1
```

## Next Steps

1. **Add Authentication**: Implement API key or OAuth2 authentication
2. **Add Rate Limiting**: Prevent API abuse with rate limiting
3. **Add Caching**: Cache predictions to reduce costs
4. **Add Batch Processing**: Support bulk predictions
5. **Add Webhooks**: Real-time notifications for high-risk employees

## Support

- **API Documentation**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health
- **Model Registry**: Google Cloud Console > Vertex AI > Model Registry