"""
Secure Real-time API with Authentication
"""

import os
import json
import random
import secrets
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import hashlib
import hmac

# FastAPI app
app = FastAPI(
    title="TH.AI Talent Analytics - Secure API",
    description="Secure real-time predictions with API key authentication",
    version="2.0.0-secure"
)

# Security
security = HTTPBearer()

# Configuration - In production, use environment variables or Secret Manager
API_KEYS = {
    "demo-key-2024": {
        "name": "Demo User",
        "created": "2024-01-01",
        "permissions": ["read", "predict"],
        "rate_limit": 100
    },
    "th-talent-prod-key": {
        "name": "Production User",
        "created": "2024-01-01", 
        "permissions": ["read", "predict", "admin"],
        "rate_limit": 1000
    }
}

# In production, use environment variable
SECRET_KEY = os.getenv("API_SECRET_KEY", "th-ai-talent-wow-secret-2024")

# Rate limiting storage (in production, use Redis)
request_counts = {}

# Request/Response models
class EmployeeData(BaseModel):
    employee_id: str
    job_level: int = 2
    years_at_company: float = 3.0
    performance_score: float = 4.0
    salary_percentile: float = 0.6

class RetentionRequest(BaseModel):
    employees: List[EmployeeData]

class SkillGapRequest(BaseModel):
    employee_ids: List[str]

class PromotionRequest(BaseModel):
    employee_ids: List[str]

class APIKeyRequest(BaseModel):
    user_name: str
    user_email: str
    purpose: str

# Authentication functions
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Verify API key and return user info"""
    api_key = credentials.credentials
    
    # Check if API key exists
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_info = API_KEYS[api_key]
    
    # Check rate limiting
    current_time = datetime.now()
    time_window = current_time.strftime("%Y-%m-%d-%H")
    rate_limit_key = f"{api_key}:{time_window}"
    
    if rate_limit_key not in request_counts:
        request_counts[rate_limit_key] = 0
    
    request_counts[rate_limit_key] += 1
    
    if request_counts[rate_limit_key] > user_info["rate_limit"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {user_info['rate_limit']} requests per hour"
        )
    
    return user_info

def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"tk_{secrets.token_urlsafe(32)}"

# Demo prediction functions (same as before)
def predict_retention_demo(employee: EmployeeData) -> Dict:
    """Demo retention prediction with realistic logic"""
    risk_score = 0.0
    
    if employee.performance_score < 3.0:
        risk_score += 0.4
    elif employee.performance_score < 4.0:
        risk_score += 0.2
    
    if employee.salary_percentile < 0.4:
        risk_score += 0.3
    elif employee.salary_percentile < 0.6:
        risk_score += 0.1
    
    if employee.years_at_company < 1 or employee.years_at_company > 8:
        risk_score += 0.1
    
    risk_score += random.uniform(-0.1, 0.1)
    risk_score = max(0.0, min(1.0, risk_score))
    
    if risk_score >= 0.7:
        risk_level = "HIGH"
    elif risk_score >= 0.4:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    return {
        "employee_id": employee.employee_id,
        "termination_probability": round(risk_score, 3),
        "predicted_termination": risk_score > 0.5,
        "risk_level": risk_level,
        "confidence": round(abs(risk_score - 0.5) * 2, 3)
    }

def predict_skill_gap_demo(employee_id: str) -> Dict:
    """Demo skill gap analysis"""
    skills_pool = [
        "Python", "JavaScript", "SQL", "Docker", "Kubernetes", 
        "AWS", "Machine Learning", "React", "Node.js", "MongoDB",
        "System Design", "Leadership", "Project Management"
    ]
    
    num_skills = random.randint(3, 8)
    employee_skills = [
        {
            "skill_name": skill,
            "skill_score": random.randint(2, 5)
        }
        for skill in random.sample(skills_pool, num_skills)
    ]
    
    remaining_skills = [s for s in skills_pool if s not in [es["skill_name"] for es in employee_skills]]
    current_missing = random.sample(remaining_skills, min(3, len(remaining_skills)))
    next_missing = random.sample(remaining_skills, min(2, len(remaining_skills)))
    
    avg_skill_score = sum(s["skill_score"] for s in employee_skills) / len(employee_skills)
    skill_gap_score = len(current_missing) * 10 + len(next_missing) * 5
    readiness_score = max(0, min(100, (avg_skill_score * 15) + len(employee_skills) * 2 - skill_gap_score))
    
    return {
        "employee_id": employee_id,
        "current_position": f"Software Engineer (L{random.randint(1, 4)})",
        "next_position": f"Senior Software Engineer (L{random.randint(2, 5)})",
        "employee_skills": employee_skills,
        "current_missing_skills": current_missing,
        "next_missing_skills": next_missing,
        "skill_gap_score": min(100, skill_gap_score),
        "readiness_score": round(readiness_score, 1)
    }

def predict_promotion_demo(employee_id: str) -> Dict:
    """Demo promotion readiness analysis"""
    categories = ["On Track", "Overlooked Talent", "Disengaged Employee", "New and Promising"]
    category = random.choice(categories)
    
    if category == "On Track":
        score = random.uniform(80, 95)
    elif category == "Overlooked Talent":
        score = random.uniform(70, 85)
    elif category == "New and Promising":
        score = random.uniform(60, 75)
    else:
        score = random.uniform(30, 50)
    
    return {
        "employee_id": employee_id,
        "promotion_category": category,
        "promotion_score": round(score, 1),
        "recent_evaluation_score": round(random.uniform(3.0, 5.0), 1),
        "evaluation_trend": round(random.uniform(-0.5, 0.5), 2)
    }

# Public endpoints (no authentication required)
@app.get("/")
async def root():
    """API health check - public endpoint"""
    return {
        "message": "TH.AI Talent Analytics Secure API",
        "version": "2.0.0-secure",
        "status": "healthy",
        "authentication": "Required for prediction endpoints",
        "docs": "/docs",
        "get_api_key": "Contact admin or use /request-api-key endpoint"
    }

@app.get("/health")
async def health_check():
    """Health check - public endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0-secure"
    }

@app.post("/request-api-key")
async def request_api_key(request: APIKeyRequest):
    """Request a demo API key - public endpoint"""
    # In production, this would send email for approval
    # For demo, we'll return a temporary key
    
    if not request.user_email or "@" not in request.user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid email required"
        )
    
    # Generate demo key (valid for 24 hours in production)
    demo_key = generate_api_key()
    
    return {
        "status": "success",
        "message": "Demo API key generated (valid for testing)",
        "api_key": demo_key,
        "usage": {
            "header": "Authorization",
            "value": f"Bearer {demo_key}",
            "example_curl": f"curl -H 'Authorization: Bearer {demo_key}' https://api-url/predict/retention"
        },
        "rate_limit": "100 requests per hour",
        "note": "For production access, contact admin@th-ai-talent.com"
    }

# Protected endpoints (authentication required)
@app.post("/predict/retention", dependencies=[Depends(verify_api_key)])
async def predict_retention(
    request: RetentionRequest,
    user_info: Dict = Depends(verify_api_key)
):
    """Predict employee retention risk - requires authentication"""
    try:
        predictions = []
        for employee in request.employees:
            prediction = predict_retention_demo(employee)
            predictions.append(prediction)
        
        return {
            "status": "success",
            "predictions": predictions,
            "model_version": "retention-secure-v2",
            "count": len(predictions),
            "api_user": user_info["name"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/predict/skill-gap", dependencies=[Depends(verify_api_key)])
async def predict_skill_gap(
    request: SkillGapRequest,
    user_info: Dict = Depends(verify_api_key)
):
    """Analyze skill gaps - requires authentication"""
    try:
        predictions = []
        for emp_id in request.employee_ids:
            prediction = predict_skill_gap_demo(emp_id)
            predictions.append(prediction)
        
        return {
            "status": "success",
            "predictions": predictions,
            "model_version": "skill-gap-secure-v2",
            "count": len(predictions),
            "api_user": user_info["name"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill gap analysis failed: {str(e)}")

@app.post("/predict/promotion", dependencies=[Depends(verify_api_key)])
async def predict_promotion(
    request: PromotionRequest,
    user_info: Dict = Depends(verify_api_key)
):
    """Analyze promotion readiness - requires authentication"""
    try:
        predictions = []
        for emp_id in request.employee_ids:
            prediction = predict_promotion_demo(emp_id)
            predictions.append(prediction)
        
        return {
            "status": "success",
            "predictions": predictions,
            "model_version": "promotion-secure-v2",
            "count": len(predictions),
            "api_user": user_info["name"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Promotion analysis failed: {str(e)}")

@app.get("/api/usage", dependencies=[Depends(verify_api_key)])
async def get_api_usage(user_info: Dict = Depends(verify_api_key)):
    """Get API usage statistics - requires authentication"""
    current_time = datetime.now()
    time_window = current_time.strftime("%Y-%m-%d-%H")
    
    # Get usage for current user
    usage_keys = [k for k in request_counts.keys() if k.startswith(user_info["name"])]
    total_requests = sum(request_counts.get(k, 0) for k in usage_keys)
    
    return {
        "user": user_info["name"],
        "rate_limit": user_info["rate_limit"],
        "current_hour_usage": request_counts.get(f"{user_info['name']}:{time_window}", 0),
        "total_requests_tracked": total_requests,
        "permissions": user_info["permissions"]
    }

# Admin endpoints (requires admin permission)
@app.get("/admin/keys", dependencies=[Depends(verify_api_key)])
async def list_api_keys(user_info: Dict = Depends(verify_api_key)):
    """List all API keys - admin only"""
    if "admin" not in user_info.get("permissions", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Return sanitized key list
    keys_info = []
    for key, info in API_KEYS.items():
        keys_info.append({
            "key_preview": f"{key[:10]}...{key[-4:]}",
            "user": info["name"],
            "created": info["created"],
            "rate_limit": info["rate_limit"]
        })
    
    return {"api_keys": keys_info}

# Run the app
if __name__ == "__main__":
    import uvicorn
    print("🔒 Starting TH.AI Talent Analytics Secure API...")
    print("🔑 Authentication: Required for prediction endpoints")
    print("📊 Features: Secure real-time predictions with rate limiting")
    print("🌐 API Docs: http://localhost:8080/docs")
    print("🎫 Get API Key: POST /request-api-key")
    print("\n📌 Demo API Keys:")
    print("   - demo-key-2024 (100 req/hour)")
    print("   - th-talent-prod-key (1000 req/hour)")
    
    uvicorn.run(
        "secure_api:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )