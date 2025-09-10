# th.ai-talent-wow

This repository contains a suite of analytics modules designed to provide deep insights into talent management, focusing on employee retention, skill development, and career progression.

## Documentation Index

| Document | Description |
|----------|-------------|
| [Latest Activity](./latest_activity.md) | Recent updates and deployment status |
| [API Examples](./API_EXAMPLES.md) | Sample API requests and responses |
| [Retention Pipeline API](./RETENTION_PIPELINE_API.md) | Documentation for retention pipeline trigger endpoints |
| [Realtime Predictions](./REALTIME-PREDICTIONS.md) | Real-time prediction API documentation |
| [Deploy to GCP](./DEPLOY-GCP.md) | Google Cloud Platform deployment guide |
| [Docker Setup](./README-DOCKER.md) | Docker configuration and usage instructions |

## Deployed API Service

The talent analytics API is deployed on Google Cloud Run and provides various endpoints for real-time predictions and pipeline triggers.

- **Service URL**: https://talent-analytics-689036726654.asia-southeast1.run.app/
- **Authentication**: X-API-Key header (demo key: `demo-key-2024`)
- **API Documentation**: Available at `/docs` endpoint
- **Health Check**: `/health` endpoint

### Quick Test
```bash
# Check service health
curl https://talent-analytics-689036726654.asia-southeast1.run.app/health

# Trigger retention pipeline
curl -X POST https://talent-analytics-689036726654.asia-southeast1.run.app/trigger-retention-pipeline \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-key-2024" \
  -d '{"gcs_date_partition": "2025-09-05"}'
```

## Modules Overview
The project is composed of four main analysis modules:
1. **Predictive Retention Analysis** - Utilizes a predictive model to forecast employee termination probability and identifies the key factors influencing attrition.
2. **Skill Gap Analysis** - Assesses and visualizes skill gaps for individual employees and entire departments.
3. **Department Rotation Analysis** - Identifies the skills an employee would need to acquire to successfully transition to a different department.
4. **Promotion Readiness Analysis** - Categorizes employees based on their readiness for promotion, identifying overlooked talent and disengaged individuals.

---

## Requirements
- Python 3.12+
- Install dependencies before running:
```bash
pip install -r requirements.txt
```

---
## Usage
### 1. Predictive Retention Analysis
To train the predictive retention analysis model:
```bash
python predictive_retention/main.py
```

**Results**
- The saved model and its configuration is saved in:
  ```output/model```
- JSON output of the prediction results and analysis is stored at:
  ```output/termination_result.json```

---

### 2. Skill Gap, Promotion, and Rotation Analysis
To run the skill gap analysis:
```bash
python skill_promotion_management/main.py
```

**Results**
- JSON output of the **Employee** skill gap analysis is stored at:
  ```output/employee_skill_gap_result.json```
- JSON output of the **Department** skill gap analysis is stored at:
  ```output/department_skill_gap_result.json```
- JSON output of the **Rotation** analysis is stored at:
  ```output/rotation_skill_gap_result.json```
- JSON output of the **Promotion** analysis is stored at:
  ```output/promotion_analysis_results.json```

**Key Results**

A main key of each JSON file is listed in ```json_output_key.txt``` for quick reference and understanding of the output structure.

---

## Example dashboard 
To view the example dashboard of how each variable can be visualize and plot, run:
```bash
streamlit run all_streamlit.py
```

---

## File Structure
```
├── config/                     # Configuration files
│   └── gcs_data_loader.py      # GCS data loader for date-partitioned data
├── mock_data/                  # Sample data for testing
├── output/                     # Output files and results
├── predictive_retention/       # Predictive retention analysis module
├── skill_promotion_management/ # Skill gap, promotion, and rotation analysis module
├── vertex_ai/                  # API deployment files
│   ├── secure_api.py           # Main API with retention trigger endpoints
│   ├── Dockerfile.secure       # Docker configuration for API
│   └── requirements-secure.txt # API dependencies
├── all_streamlit.py            # Streamlit dashboard
├── json_output_key.txt         # Listed main key of each JSON file
├── requirements.txt            # Python dependencies
├── cloudbuild-secure.yaml      # Cloud Build configuration
├── latest_activity.md          # Recent updates and deployment status
└── README.md                   # Project documentation
```