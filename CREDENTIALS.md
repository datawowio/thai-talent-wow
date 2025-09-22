# Credentials Setup

## Google Service Account

For GenAI and GCS access, place your service account JSON file in the project root directory.

### Required File Location:
```
/path/to/project/th-ai-talent-wow-XXXXXXXXX.json
```

Where `XXXXXXXXX` is your service account key ID.

### Container Mount Path:
The service account file should be mounted at `/app/service-account.json` in the Docker container.

### Environment Variable:
Set `GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json` in the container.

### Example Docker Run:
```bash
docker run -d --name thai-talent-ml-api \
  -p 8080:8080 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json \
  -v /path/to/your/service-account.json:/app/service-account.json \
  -e API_SECRET_KEY=your-api-key \
  thai-talent-ml-api:latest
```

### Required Permissions:
- `roles/aiplatform.admin` or `roles/aiplatform.user` - for Vertex AI GenAI access
- `roles/storage.objectViewer` - for GCS data access
- `roles/ml.developer` - for ML operations

### Note:
- Never commit credential files to git
- The credential file is already ignored in .gitignore
- Use mock data (gcs_bucket: "mock") for testing without GCS access