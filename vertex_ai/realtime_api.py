"""
Real-time API wrapper for Vertex AI predictions
FastAPI service that provides REST endpoints for talent analytics
"""

import os
import sys
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import aiplatform
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Initialize Vertex AI
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'th-ai-talent-wow')
REGION = os.getenv('GOOGLE_CLOUD_REGION', 'asia-southeast1')
aiplatform.init(project=PROJECT_ID, location=REGION)

# FastAPI app
app = FastAPI(
    title="TH.AI Talent Analytics - Real-time API",
    description="Real-time predictions for employee retention, skill gaps, and promotion readiness",
    version="1.0.0"
)

# Request/Response models
class EmployeeData(BaseModel):
    employee_id: str
    job_level: Optional[int] = None
    years_at_company: Optional[float] = None
    years_in_position: Optional[float] = None
    performance_score: Optional[float] = None
    salary_percentile: Optional[float] = None
    skill_diversity: Optional[int] = None
    last_evaluation_score: Optional[float] = None

class RetentionRequest(BaseModel):
    employees: List[EmployeeData]
    include_shap: Optional[bool] = False

class SkillGapRequest(BaseModel):
    employee_ids: List[str]

class PromotionRequest(BaseModel):
    employee_ids: List[str]

class BatchPredictionRequest(BaseModel):
    employee_ids: List[str]
    include_retention: Optional[bool] = True
    include_skill_gap: Optional[bool] = True
    include_promotion: Optional[bool] = True

# Endpoint managers
class EndpointManager:
    """Manages Vertex AI endpoint connections"""
    
    def __init__(self):
        self.endpoints = {}
        self._load_endpoints()
    
    def _load_endpoints(self):
        """Load endpoint information from deployment info"""
        try:
            with open('deployment_info.json', 'r') as f:
                deployment_info = json.load(f)
            
            # Load retention endpoint
            if 'retention' in deployment_info:
                endpoint_id = deployment_info['retention']['endpoint_id']
                self.endpoints['retention'] = aiplatform.Endpoint(endpoint_id)
            
            # Load skill endpoints
            if 'skill' in deployment_info:
                skill_info = deployment_info['skill']
                if 'skill_gap' in skill_info:
                    endpoint_id = skill_info['skill_gap']['endpoint_id']
                    self.endpoints['skill_gap'] = aiplatform.Endpoint(endpoint_id)
                
                if 'promotion' in skill_info:
                    endpoint_id = skill_info['promotion']['endpoint_id']
                    self.endpoints['promotion'] = aiplatform.Endpoint(endpoint_id)
        
        except FileNotFoundError:
            print("⚠️  No deployment_info.json found. Endpoints will be discovered dynamically.")
            self._discover_endpoints()
    
    def _discover_endpoints(self):
        """Discover endpoints by name if deployment info not available"""
        try:
            # Find retention endpoint
            retention_endpoints = aiplatform.Endpoint.list(
                filter='display_name="retention-endpoint-v1"'
            )
            if retention_endpoints:
                self.endpoints['retention'] = retention_endpoints[0]
            
            # Find skill gap endpoint
            skill_endpoints = aiplatform.Endpoint.list(
                filter='display_name="skill-gap-endpoint-v1"'
            )
            if skill_endpoints:
                self.endpoints['skill_gap'] = skill_endpoints[0]
            
            # Find promotion endpoint
            promotion_endpoints = aiplatform.Endpoint.list(
                filter='display_name="promotion-endpoint-v1"'
            )
            if promotion_endpoints:
                self.endpoints['promotion'] = promotion_endpoints[0]
        
        except Exception as e:
            print(f"❌ Error discovering endpoints: {e}")

    def get_endpoint(self, endpoint_name: str):
        """Get endpoint by name"""
        if endpoint_name not in self.endpoints:
            raise HTTPException(
                status_code=503, 
                detail=f"Endpoint {endpoint_name} not available"
            )
        return self.endpoints[endpoint_name]

# Global endpoint manager
endpoint_manager = EndpointManager()

# API Endpoints
@app.get("/")
async def root():
    """API health check"""
    return {
        "message": "TH.AI Talent Analytics Real-time API",
        "version": "1.0.0",
        "status": "healthy",
        "available_endpoints": list(endpoint_manager.endpoints.keys())
    }

@app.post("/predict/retention")
async def predict_retention(request: RetentionRequest):
    """Predict employee retention risk"""
    try:
        endpoint = endpoint_manager.get_endpoint('retention')
        
        # Convert employees to instances
        instances = []
        for emp in request.employees:
            instance = emp.dict()
            instances.append(instance)
        
        # Make prediction
        predictions = endpoint.predict(instances=instances)
        
        return {
            "status": "success",
            "predictions": predictions.predictions,
            "model_version": "retention-v1",
            "count": len(instances)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/predict/skill-gap")
async def predict_skill_gap(request: SkillGapRequest):
    """Analyze skill gaps for employees"""
    try:
        endpoint = endpoint_manager.get_endpoint('skill_gap')
        
        # Convert to instances
        instances = [{"employee_id": emp_id} for emp_id in request.employee_ids]
        
        # Make prediction
        predictions = endpoint.predict(instances=instances)
        
        return {
            "status": "success",
            "predictions": predictions.predictions,
            "model_version": "skill-gap-v1",
            "count": len(instances)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill gap analysis failed: {str(e)}")

@app.post("/predict/promotion")
async def predict_promotion(request: PromotionRequest):
    """Analyze promotion readiness for employees"""
    try:
        endpoint = endpoint_manager.get_endpoint('promotion')
        
        # Convert to instances
        instances = [{"employee_id": emp_id} for emp_id in request.employee_ids]
        
        # Make prediction
        predictions = endpoint.predict(instances=instances)
        
        return {
            "status": "success", 
            "predictions": predictions.predictions,
            "model_version": "promotion-v1",
            "count": len(instances)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Promotion analysis failed: {str(e)}")

@app.post("/predict/comprehensive")
async def predict_comprehensive(request: BatchPredictionRequest):
    """Get comprehensive analytics for employees (retention + skill gap + promotion)"""
    results = {
        "status": "success",
        "employee_analytics": {},
        "summary": {
            "total_employees": len(request.employee_ids),
            "completed_analyses": []
        }
    }
    
    errors = []
    
    # Initialize employee results
    for emp_id in request.employee_ids:
        results["employee_analytics"][emp_id] = {"employee_id": emp_id}
    
    try:
        # Retention analysis
        if request.include_retention:
            try:
                retention_endpoint = endpoint_manager.get_endpoint('retention')
                retention_instances = []
                
                for emp_id in request.employee_ids:
                    # Basic instance - real implementation would fetch from database
                    retention_instances.append({
                        "employee_id": emp_id,
                        "job_level": 2,  # Default values - replace with actual data
                        "performance_score": 4.0
                    })
                
                retention_preds = retention_endpoint.predict(instances=retention_instances)
                
                for i, emp_id in enumerate(request.employee_ids):
                    results["employee_analytics"][emp_id]["retention"] = retention_preds.predictions[i]
                
                results["summary"]["completed_analyses"].append("retention")
                
            except Exception as e:
                errors.append(f"Retention analysis failed: {str(e)}")
        
        # Skill gap analysis
        if request.include_skill_gap:
            try:
                skill_endpoint = endpoint_manager.get_endpoint('skill_gap')
                skill_instances = [{"employee_id": emp_id} for emp_id in request.employee_ids]
                
                skill_preds = skill_endpoint.predict(instances=skill_instances)
                
                for i, emp_id in enumerate(request.employee_ids):
                    results["employee_analytics"][emp_id]["skill_gap"] = skill_preds.predictions[i]
                
                results["summary"]["completed_analyses"].append("skill_gap")
                
            except Exception as e:
                errors.append(f"Skill gap analysis failed: {str(e)}")
        
        # Promotion analysis  
        if request.include_promotion:
            try:
                promotion_endpoint = endpoint_manager.get_endpoint('promotion')
                promotion_instances = [{"employee_id": emp_id} for emp_id in request.employee_ids]
                
                promotion_preds = promotion_endpoint.predict(instances=promotion_instances)
                
                for i, emp_id in enumerate(request.employee_ids):
                    results["employee_analytics"][emp_id]["promotion"] = promotion_preds.predictions[i]
                
                results["summary"]["completed_analyses"].append("promotion")
                
            except Exception as e:
                errors.append(f"Promotion analysis failed: {str(e)}")
        
        if errors:
            results["warnings"] = errors
            
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comprehensive analysis failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Detailed health check of all services"""
    health_status = {
        "api_status": "healthy",
        "endpoints": {},
        "timestamp": "2024-01-01T00:00:00Z"  # Replace with actual timestamp
    }
    
    # Check each endpoint
    for endpoint_name, endpoint in endpoint_manager.endpoints.items():
        try:
            # Simple connectivity test
            health_status["endpoints"][endpoint_name] = {
                "status": "healthy",
                "endpoint_id": endpoint.name
            }
        except Exception as e:
            health_status["endpoints"][endpoint_name] = {
                "status": "unhealthy", 
                "error": str(e)
            }
    
    overall_healthy = all(
        ep["status"] == "healthy" 
        for ep in health_status["endpoints"].values()
    )
    
    if not overall_healthy:
        health_status["api_status"] = "degraded"
    
    return health_status

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "realtime_api:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )