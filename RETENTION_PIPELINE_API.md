# Retention ML Pipeline API

Simple API to trigger the retention ML pipeline and check job status. No authentication complexity, just pure pipeline execution.

## Authentication

All endpoints require API key authentication via `X-API-Key` header.

### Available API Keys
- `demo-key-2024` - 100 requests per hour
- `th-talent-prod-key` - 1000 requests per hour

## Overview

The API triggers the ML pipeline in `predictive_retention/main.py` which performs:
1. Feature Engineering from CSV/GCS data
2. Model Training 
3. Model Saving
4. Predictions Generation
5. Results Saving
6. Output File Validation

## Running the API

```bash
# Start the API server
python api/retention_api.py

# API available at http://localhost:8080
# API Docs at http://localhost:8080/docs
```

## API Endpoints

### 1. Health Check (Public)
```bash
GET /
GET /health
```

Returns API status and available endpoints. No authentication required.

### 2. Trigger Retention Pipeline
```bash
POST /trigger-retention-pipeline
X-API-Key: demo-key-2024
```

Starts the retention prediction pipeline.

**Request Body:**
```json
{
  "task_id": "task_55555_from_backend",
  "gcs_bucket": "th-ai-talent-data/2025-09-05"
}
```

**Response:**
```json
{
  "job_id": "task_55555_from_backend", 
  "status": "queued",
  "message": "Retention pipeline triggered. Use /retention-job-status/task_55555_from_backend to check progress.",
  "started_at": "2025-09-10T14:15:23"
}
```

### 3. Check Job Status
```bash
GET /retention-job-status/{job_id}
X-API-Key: demo-key-2024
```

Get detailed status of a pipeline job.

**Response:**
```json
{
  "job_id": "task_55555_from_backend",
  "status": "completed",
  "created_at": "2025-09-10T14:15:23",
  "started_at": "2025-09-10T14:15:24", 
  "completed_at": "2025-09-10T14:18:45",
  "execution_time_seconds": 201.3,
  "gcs_bucket": "th-ai-talent-data/2025-09-05",
  "api_user": "Demo User",
  "output_preview": "Retention pipeline completed successfully for GCS bucket: th-ai-talent-data/2025-09-05",
  "output_files": {
    "output/feature_engineered_data.csv": true,
    "output/model/model.pkl": true,
    "output/model/model_config.json": true,
    "output/model/model_interpretation.pkl": true,
    "output/model_result.parquet": true,
    "output/termination_result.json": true
  },
  "output_files_count": "6/6",
  "model_saved": true
}
```

**Status Values:**
- `queued` - Job created, waiting to start
- `running` - Pipeline executing
- `completed` - Successfully finished
- `failed` - Pipeline failed (includes error details)

### 4. List All Jobs
```bash
GET /retention-jobs
X-API-Key: demo-key-2024
```

List all retention pipeline jobs.

**Response:**
```json
{
  "total": 2,
  "jobs": [
    {
      "job_id": "task_55555_from_backend",
      "status": "completed", 
      "created_at": "2025-09-10T14:15:23",
      "gcs_bucket": "th-ai-talent-data/2025-09-05",
      "api_user": "Demo User"
    },
    {
      "job_id": "task_66666_from_backend", 
      "status": "running",
      "created_at": "2025-09-10T15:10:00",
      "gcs_bucket": "th-ai-talent-data/2025-09-06",
      "api_user": "Production User"
    }
  ]
}
```

## Example Usage

### Trigger Pipeline
```bash
curl -X POST https://talent-analytics-689036726654.asia-southeast1.run.app/trigger-retention-pipeline \
    -H "Content-Type: application/json" \
    -H "X-API-Key: demo-key-2024" \
    -d '{"task_id": "task_55555_from_backend", "gcs_bucket": "th-ai-talent-data/2025-09-05"}'
```

### Check Job Status
```bash
curl https://talent-analytics-689036726654.asia-southeast1.run.app/retention-job-status/task_55555_from_backend \
    -H "X-API-Key: demo-key-2024"
```

### List All Jobs
```bash
curl https://talent-analytics-689036726654.asia-southeast1.run.app/retention-jobs \
    -H "X-API-Key: demo-key-2024"
```

## Important Notes

1. **Single Job Limit**: Only one pipeline can run at a time
2. **GCS Data**: When `gcs_bucket` provided, sets `GCS_BUCKET_PATH` environment variable
3. **Local Fallback**: Without `gcs_bucket`, uses local data files
4. **Background Processing**: Pipeline runs in background thread
5. **30 Minute Timeout**: Jobs automatically fail after 30 minutes
6. **Rate Limiting**: API keys have hourly request limits
7. **Output Validation**: Checks for 6 expected output files after completion

## Output Files Generated

The pipeline creates these files in the project directory:
- `output/feature_engineered_data.csv` - Processed features
- `output/model/model.pkl` - Trained model
- `output/model/model_config.json` - Model configuration  
- `output/model/model_interpretation.pkl` - Model interpretation
- `output/model_result.parquet` - Prediction results
- `output/termination_result.json` - Analysis results

## Integration with Ruby Backend

```ruby
require 'net/http'
require 'json'

# Trigger pipeline
uri = URI('https://talent-analytics-689036726654.asia-southeast1.run.app/trigger-retention-pipeline')
http = Net::HTTP.new(uri.host, uri.port)
http.use_ssl = true

request = Net::HTTP::Post.new(uri)
request['Content-Type'] = 'application/json'
request['X-API-Key'] = 'th-talent-prod-key'
request.body = {
  task_id: "task_#{Time.now.to_i}_from_backend",
  gcs_bucket: "th-ai-talent-data/#{Date.today.strftime('%Y-%m-%d')}"
}.to_json

response = http.request(request)
result = JSON.parse(response.body)
job_id = result['job_id']

# Check status
status_uri = URI("https://talent-analytics-689036726654.asia-southeast1.run.app/retention-job-status/#{job_id}")
status_request = Net::HTTP::Get.new(status_uri)
status_request['X-API-Key'] = 'th-talent-prod-key'

status_response = http.request(status_request)
status_result = JSON.parse(status_response.body)
```

## Error Handling

**Failed Jobs Include:**
- `error` - Error description
- `stderr_preview` - Last 500 chars of error output
- `stdout_preview` - Last 500 chars of standard output
- `execution_time_seconds` - Time before failure

**Common Errors:**
- Pipeline script not found
- Timeout after 30 minutes
- Python execution errors
- Missing dependencies