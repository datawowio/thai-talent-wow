# TH.AI Talent Analytics API Examples

## API Endpoint
```
https://talent-analytics-secure-689036726654.asia-southeast1.run.app
```

## Authentication
Use `X-API-Key` header with your API key.

**Current API Key:** `tk_RubyBackend2024`

## 1. Retention Prediction

### Request
```bash
curl -X POST https://talent-analytics-secure-689036726654.asia-southeast1.run.app/predict/retention \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tk_RubyBackend2024" \
  -d '{
    "employees": [
      {
        "employee_id": "EMP001",
        "job_level": 3,
        "years_at_company": 2.5,
        "performance_score": 4.2,
        "salary_percentile": 0.7
      },
      {
        "employee_id": "EMP002",
        "job_level": 2,
        "years_at_company": 1.0,
        "performance_score": 3.5,
        "salary_percentile": 0.4
      }
    ]
  }'
```

### Response
```json
{
  "status": "success",
  "predictions": [
    {
      "employee_id": "EMP001",
      "termination_probability": 0.094,
      "predicted_termination": false,
      "risk_level": "LOW",
      "confidence": 0.811
    },
    {
      "employee_id": "EMP002",
      "termination_probability": 0.420,
      "predicted_termination": false,
      "risk_level": "MEDIUM",
      "confidence": 0.160
    }
  ],
  "model_version": "retention-secure-v2",
  "count": 2,
  "api_user": "Ruby Backend"
}
```

## 2. Skill Gap Analysis

### Request
```bash
curl -X POST https://talent-analytics-secure-689036726654.asia-southeast1.run.app/predict/skill-gap \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tk_RubyBackend2024" \
  -d '{
    "employee_ids": ["EMP001", "EMP002", "EMP003"]
  }'
```

### Response
```json
{
  "status": "success",
  "predictions": [
    {
      "employee_id": "EMP001",
      "current_position": "Software Engineer (L3)",
      "next_position": "Senior Software Engineer (L4)",
      "employee_skills": [
        {"skill_name": "Python", "skill_score": 4},
        {"skill_name": "SQL", "skill_score": 3},
        {"skill_name": "Docker", "skill_score": 2}
      ],
      "current_missing_skills": ["Kubernetes", "System Design"],
      "next_missing_skills": ["Leadership", "Architecture"],
      "skill_gap_score": 35,
      "readiness_score": 72.5
    }
  ],
  "model_version": "skill-gap-secure-v2",
  "count": 1,
  "api_user": "Ruby Backend"
}
```

## 3. Promotion Analysis

### Request
```bash
curl -X POST https://talent-analytics-secure-689036726654.asia-southeast1.run.app/predict/promotion \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tk_RubyBackend2024" \
  -d '{
    "employee_ids": ["EMP001", "EMP002"]
  }'
```

### Response
```json
{
  "status": "success",
  "predictions": [
    {
      "employee_id": "EMP001",
      "promotion_category": "On Track",
      "promotion_score": 87.3,
      "recent_evaluation_score": 4.2,
      "evaluation_trend": 0.15
    },
    {
      "employee_id": "EMP002",
      "promotion_category": "Overlooked Talent",
      "promotion_score": 76.8,
      "recent_evaluation_score": 3.9,
      "evaluation_trend": 0.08
    }
  ],
  "model_version": "promotion-secure-v2",
  "count": 2,
  "api_user": "Ruby Backend"
}
```

## 4. Health Check (No Auth Required)

### Request
```bash
curl https://talent-analytics-secure-689036726654.asia-southeast1.run.app/health
```

### Response
```json
{
  "status": "healthy",
  "timestamp": "2025-09-08T15:30:45.123456",
  "version": "2.0.0-secure"
}
```

## 5. API Root Info (No Auth Required)

### Request
```bash
curl https://talent-analytics-secure-689036726654.asia-southeast1.run.app/
```

### Response
```json
{
  "message": "TH.AI Talent Analytics Secure API",
  "version": "2.0.0-secure",
  "status": "healthy",
  "authentication": "Required for prediction endpoints (X-API-Key header)",
  "docs": "/docs",
  "get_api_key": "Contact admin or use /request-api-key endpoint"
}
```

## 6. Request Demo API Key (No Auth Required)

### Request
```bash
curl -X POST https://talent-analytics-secure-689036726654.asia-southeast1.run.app/request-api-key \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "Test User",
    "user_email": "test@example.com",
    "purpose": "Testing the API"
  }'
```

### Response
```json
{
  "status": "success",
  "message": "Demo API key generated (valid for testing)",
  "api_key": "tk_abc123xyz...",
  "usage": {
    "header": "X-API-Key",
    "value": "tk_abc123xyz...",
    "example_curl": "curl -H 'X-API-Key: tk_abc123xyz...' https://api-url/predict/retention"
  },
  "rate_limit": "100 requests per hour",
  "note": "For production access, contact admin@th-ai-talent.com"
}
```

## 7. Check API Usage (Auth Required)

### Request
```bash
curl https://talent-analytics-secure-689036726654.asia-southeast1.run.app/api/usage \
  -H "X-API-Key: tk_RubyBackend2024"
```

### Response
```json
{
  "user": "Ruby Backend",
  "rate_limit": 500,
  "current_hour_usage": 5,
  "total_requests_tracked": 42,
  "permissions": ["read", "predict"]
}
```

## Error Responses

### Missing API Key
```bash
curl -X POST https://talent-analytics-secure-689036726654.asia-southeast1.run.app/predict/retention \
  -H "Content-Type: application/json" \
  -d '{"employees": []}'
```

Response:
```json
{
  "detail": "Missing X-API-Key header"
}
```

### Invalid API Key
```bash
curl -X POST https://talent-analytics-secure-689036726654.asia-southeast1.run.app/predict/retention \
  -H "Content-Type: application/json" \
  -H "X-API-Key: invalid_key" \
  -d '{"employees": []}'
```

Response:
```json
{
  "detail": "Invalid API key"
}
```

## Ruby Integration Example

```ruby
require 'net/http'
require 'json'

class TalentAnalyticsClient
  API_URL = 'https://talent-analytics-secure-689036726654.asia-southeast1.run.app'
  API_KEY = 'tk_RubyBackend2024'

  def predict_retention(employees)
    request('/predict/retention', { employees: employees })
  end

  def analyze_skill_gap(employee_ids)
    request('/predict/skill-gap', { employee_ids: employee_ids })
  end

  def analyze_promotion(employee_ids)
    request('/predict/promotion', { employee_ids: employee_ids })
  end

  private

  def request(endpoint, payload)
    uri = URI("#{API_URL}#{endpoint}")
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = true
    
    request = Net::HTTP::Post.new(uri)
    request['Content-Type'] = 'application/json'
    request['X-API-Key'] = API_KEY
    request.body = payload.to_json
    
    response = http.request(request)
    JSON.parse(response.body)
  end
end

# Usage
client = TalentAnalyticsClient.new
result = client.predict_retention([
  {
    employee_id: 'EMP001',
    job_level: 3,
    years_at_company: 2.5,
    performance_score: 4.2,
    salary_percentile: 0.7
  }
])
puts result
```

## Environment Variables

To add more API keys, update the Cloud Run service:

```bash
gcloud run services update talent-analytics-secure \
  --region=asia-southeast1 \
  --set-env-vars='API_KEY_RUBY_BACKEND=tk_RubyBackend2024:Ruby Backend:read;predict:500,API_KEY_ADMIN=tk_AdminKey2024:Admin:read;predict;admin:1000'
```

Note: Use semicolon (;) to separate permissions, not comma.

## API Documentation

Interactive API documentation available at:
```
https://talent-analytics-secure-689036726654.asia-southeast1.run.app/docs
```