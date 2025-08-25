# Docker Setup for Talent Analytics Inference

This setup provides containerized API and worker services for running talent analytics inference.

## Architecture

The system consists of three main components:

1. **API Service** - FastAPI-based REST API for triggering inference jobs
2. **Inference Worker** - Background worker that processes inference requests
3. **Redis** - Message queue for job management

## Quick Start

### 1. Build and Start Services

```bash
# Copy environment configuration
cp .env.example .env

# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 2. Access the API

The API will be available at: http://localhost:8000

API Documentation: http://localhost:8000/docs

## API Endpoints

### Trigger Inference

```bash
# Retention Analysis
curl -X POST "http://localhost:8000/inference/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_type": "retention",
    "include_shap": true
  }'

# Skill Gap Analysis
curl -X POST "http://localhost:8000/inference/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_type": "skill_gap",
    "employee_ids": ["EMP001", "EMP002"]
  }'

# Promotion Analysis
curl -X POST "http://localhost:8000/inference/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_type": "promotion",
    "department_ids": ["DEPT001"]
  }'

# Rotation Analysis  
curl -X POST "http://localhost:8000/inference/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_type": "rotation",
    "employee_ids": ["EMP001"]
  }'
```

### Check Job Status

```bash
curl "http://localhost:8000/inference/status/{job_id}"
```

### Get Job Result

```bash
curl "http://localhost:8000/inference/result/{job_id}"
```

### List Recent Jobs

```bash
curl "http://localhost:8000/inference/jobs?limit=10&status=completed"
```

## Analysis Types

- **retention**: Predict employee termination probability with SHAP explanations
- **skill_gap**: Analyze skill gaps for employees and departments
- **promotion**: Evaluate promotion readiness across the organization
- **rotation**: Identify skills needed for department transitions

## Configuration

### Environment Variables

Edit `.env` file to configure:

- `REDIS_HOST`: Redis server hostname (default: redis)
- `REDIS_PORT`: Redis server port (default: 6379)
- `WORKER_CONCURRENCY`: Number of worker processes (default: 2)

### Scaling Workers

To scale the number of workers:

```bash
# Scale to 5 workers
docker-compose up -d --scale worker=5
```

## Development

### Running Locally (Without Docker)

1. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-api.txt
```

2. Start Redis:
```bash
redis-server
```

3. Start the API:
```bash
uvicorn api:app --reload
```

4. Start the worker:
```bash
python inference_worker.py
```

### Monitoring

View logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
```

Check service status:
```bash
docker-compose ps
```

## Data Management

### Input Data
- Mock data should be placed in `mock_data/` directory
- Data is mounted as read-only in containers

### Output Data
- Results are saved to `output/` directory
- Model artifacts are saved to `output/model/`

## Troubleshooting

### Clear Redis Queue
```bash
docker-compose exec redis redis-cli FLUSHALL
```

### Rebuild Containers
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Check Worker Health
```bash
docker-compose exec worker ps aux
```

## API Response Examples

### Successful Job Creation
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "message": "Job created successfully. Use /inference/status/{job_id} to check progress.",
  "created_at": "2024-01-01T10:00:00"
}
```

### Job Status
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": 1.0,
  "result": {...},
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:05:00"
}
```

## Production Deployment

For production deployment, consider:

1. Use external Redis instance (AWS ElastiCache, Redis Cloud)
2. Add authentication to API endpoints
3. Configure SSL/TLS certificates
4. Set up monitoring (Prometheus, Grafana)
5. Implement rate limiting
6. Add health check endpoints
7. Configure log aggregation (ELK stack)
8. Set resource limits in docker-compose.yml