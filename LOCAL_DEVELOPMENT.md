# Local Development Setup

This guide shows how to run the ML API locally with a PostgreSQL database for testing.

## 🚀 Quick Start

### 1. Start Database
```bash
docker-compose -f docker-compose.local-dev.yml up -d
```

### 2. Start ML API 
```bash
cd api

DB_HOST=localhost \
DB_NAME=thai_talent_wow_production \
DB_USERNAME=app_user \
DB_PASSWORD=TalentWow2024! \
DB_PORT=5432 \
API_SECRET_KEY=demo-key-2024 \
python3 -m uvicorn retention_api:app --host 0.0.0.0 --port 8080
```

### 3. Test the API
```bash
# Health check
curl http://localhost:8080/health

# Trigger ML pipeline
curl -X POST "http://localhost:8080/trigger-retention-pipeline" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: demo-key-2024" \
    -d '{"task_id": "test_'$(date +%s)'", "gcs_bucket": "th-ai-talent-data/2025-09-05"}'
```

### 4. Check Database Results
```python
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    database='thai_talent_wow_production',
    user='app_user',
    password='TalentWow2024!',
    port=5432
)
cursor = conn.cursor()

# Count records
cursor.execute('SELECT COUNT(*) FROM termination_results;')
print(f'Total records: {cursor.fetchone()[0]}')

conn.close()
```

## 📁 Files

- `docker-compose.local-dev.yml` - PostgreSQL container setup
- `init-db.sql` - Database schema initialization
- `api/retention_api.py` - ML API server
- `api/database.py` - Database connection logic

## ✅ Expected Results

- Real-time logs showing ML training progress
- Database records with termination predictions  
- Job status API showing completion with results

## 🔧 Cleanup

```bash
# Stop containers
docker-compose -f docker-compose.local-dev.yml down

# Remove volumes (clears database data)
docker-compose -f docker-compose.local-dev.yml down -v
```