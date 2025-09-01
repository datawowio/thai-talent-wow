"""
Demo Real-time API - Shows the concept without full model dependencies
"""

import json
import random
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# FastAPI app
app = FastAPI(
    title="TH.AI Talent Analytics - Demo API",
    description="Demo of real-time predictions for employee retention, skill gaps, and promotion readiness",
    version="1.0.0-demo"
)

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

# Demo prediction functions
def predict_retention_demo(employee: EmployeeData) -> Dict:
    """Demo retention prediction with realistic logic"""
    # Simple risk calculation based on inputs
    risk_score = 0.0
    
    # Low performance increases risk
    if employee.performance_score < 3.0:
        risk_score += 0.4
    elif employee.performance_score < 4.0:
        risk_score += 0.2
    
    # Low salary percentile increases risk
    if employee.salary_percentile < 0.4:
        risk_score += 0.3
    elif employee.salary_percentile < 0.6:
        risk_score += 0.1
    
    # Very long or very short tenure can increase risk
    if employee.years_at_company < 1 or employee.years_at_company > 8:
        risk_score += 0.1
    
    # Add some randomness
    risk_score += random.uniform(-0.1, 0.1)
    risk_score = max(0.0, min(1.0, risk_score))
    
    # Determine risk level
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
    
    # Sample skills data
    skills_pool = [
        "Python", "JavaScript", "SQL", "Docker", "Kubernetes", 
        "AWS", "Machine Learning", "React", "Node.js", "MongoDB",
        "System Design", "Leadership", "Project Management"
    ]
    
    # Simulate employee skills
    num_skills = random.randint(3, 8)
    employee_skills = [
        {
            "skill_name": skill,
            "skill_score": random.randint(2, 5)
        }
        for skill in random.sample(skills_pool, num_skills)
    ]
    
    # Simulate missing skills
    remaining_skills = [s for s in skills_pool if s not in [es["skill_name"] for es in employee_skills]]
    current_missing = random.sample(remaining_skills, min(3, len(remaining_skills)))
    next_missing = random.sample(remaining_skills, min(2, len(remaining_skills)))
    
    # Calculate scores
    avg_skill_score = sum(s["skill_score"] for s in employee_skills) / len(employee_skills)
    skill_gap_score = len(current_missing) * 10 + len(next_missing) * 5
    readiness_score = max(0, min(100, (avg_skill_score * 15) + len(employee_skills) * 2 - skill_gap_score))
    
    return {
        "employee_id": employee_id,
        "current_position": f"Software Engineer (L{random.randint(1, 4)})",
        "next_position": f"Senior Software Engineer (L{random.randint(2, 5)})",
        "employee_skills": employee_skills,
        "current_missing_skills": current_missing,
        "peer_missing_skills": [
            {
                "skill_name": skill,
                "percentage_of_peer": f"{random.randint(30, 80)}.0",
                "peer_count": random.randint(5, 15)
            }
            for skill in random.sample(remaining_skills, min(2, len(remaining_skills)))
        ],
        "next_missing_skills": next_missing,
        "skill_gap_score": min(100, skill_gap_score),
        "readiness_score": round(readiness_score, 1)
    }

def predict_promotion_demo(employee_id: str) -> Dict:
    """Demo promotion readiness analysis"""
    
    categories = ["On Track", "Overlooked Talent", "Disengaged Employee", "New and Promising"]
    category = random.choice(categories)
    
    # Score based on category
    if category == "On Track":
        score = random.uniform(80, 95)
    elif category == "Overlooked Talent":
        score = random.uniform(70, 85)
    elif category == "New and Promising":
        score = random.uniform(60, 75)
    else:  # Disengaged
        score = random.uniform(30, 50)
    
    return {
        "employee_id": employee_id,
        "promotion_category": category,
        "promotion_score": round(score, 1),
        "recent_evaluation_score": round(random.uniform(3.0, 5.0), 1),
        "evaluation_trend": round(random.uniform(-0.5, 0.5), 2)
    }

# API Endpoints
@app.get("/")
async def root():
    """API health check"""
    return {
        "message": "TH.AI Talent Analytics Demo API",
        "version": "1.0.0-demo",
        "status": "healthy",
        "note": "This is a demo showing real-time prediction concepts"
    }

@app.post("/predict/retention")
async def predict_retention(request: RetentionRequest):
    """Demo retention risk prediction"""
    try:
        predictions = []
        for employee in request.employees:
            prediction = predict_retention_demo(employee)
            predictions.append(prediction)
        
        return {
            "status": "success",
            "predictions": predictions,
            "model_version": "retention-demo-v1",
            "count": len(predictions),
            "note": "Demo predictions with realistic logic"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/predict/skill-gap")
async def predict_skill_gap(request: SkillGapRequest):
    """Demo skill gap analysis"""
    try:
        predictions = []
        for emp_id in request.employee_ids:
            prediction = predict_skill_gap_demo(emp_id)
            predictions.append(prediction)
        
        return {
            "status": "success",
            "predictions": predictions,
            "model_version": "skill-gap-demo-v1",
            "count": len(predictions),
            "note": "Demo skill analysis with sample data"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill gap analysis failed: {str(e)}")

@app.post("/predict/promotion")
async def predict_promotion(request: PromotionRequest):
    """Demo promotion readiness analysis"""
    try:
        predictions = []
        for emp_id in request.employee_ids:
            prediction = predict_promotion_demo(emp_id)
            predictions.append(prediction)
        
        return {
            "status": "success",
            "predictions": predictions,
            "model_version": "promotion-demo-v1",
            "count": len(predictions),
            "note": "Demo promotion analysis with sample logic"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Promotion analysis failed: {str(e)}")

@app.post("/predict/comprehensive")
async def predict_comprehensive(request: SkillGapRequest):
    """Demo comprehensive analytics"""
    try:
        results = {
            "status": "success",
            "employee_analytics": {},
            "summary": {
                "total_employees": len(request.employee_ids),
                "completed_analyses": ["retention", "skill_gap", "promotion"]
            },
            "note": "Demo comprehensive analysis"
        }
        
        for emp_id in request.employee_ids:
            # Create sample employee data for retention
            sample_employee = EmployeeData(
                employee_id=emp_id,
                job_level=random.randint(1, 4),
                performance_score=random.uniform(3.0, 5.0)
            )
            
            results["employee_analytics"][emp_id] = {
                "employee_id": emp_id,
                "retention": predict_retention_demo(sample_employee),
                "skill_gap": predict_skill_gap_demo(emp_id),
                "promotion": predict_promotion_demo(emp_id)
            }
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comprehensive analysis failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "api_status": "healthy",
        "endpoints": {
            "retention": {"status": "healthy", "type": "demo"},
            "skill_gap": {"status": "healthy", "type": "demo"},
            "promotion": {"status": "healthy", "type": "demo"}
        },
        "message": "Demo API - all endpoints operational"
    }

# Run the app
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting TH.AI Talent Analytics Demo API...")
    print("📊 Features: Real-time retention, skill gap, and promotion predictions")
    print("🌐 API Docs: http://localhost:8080/docs")
    print("💡 This is a demo showing the concept - uses sample data and logic")
    
    uvicorn.run(
        "demo_api:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )