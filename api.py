from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import redis
import uuid
import os
import asyncio

app = FastAPI(
    title="Talent Analytics API",
    description="API for triggering talent management analytics and predictions",
    version="1.0.0"
)

# Redis connection
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)


# Request/Response Models
class InferenceRequest(BaseModel):
    analysis_type: str  # "retention", "skill_gap", "promotion", "rotation"
    employee_ids: Optional[List[str]] = None
    department_ids: Optional[List[str]] = None
    include_shap: bool = True
    callback_url: Optional[str] = None


class InferenceResponse(BaseModel):
    job_id: str
    status: str
    message: str
    created_at: str


class JobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


# Helper functions
def create_job(request_data: dict) -> str:
    """Create a new job and add it to the queue."""
    job_id = str(uuid.uuid4())
    job_data = {
        "job_id": job_id,
        "status": "pending",
        "request": json.dumps(request_data),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Store job data in Redis
    redis_client.hset(f"job:{job_id}", mapping=job_data)
    
    # Add to job queue
    redis_client.lpush("job_queue", job_id)
    
    return job_id


def get_job_status(job_id: str) -> Optional[dict]:
    """Get the status of a job."""
    job_data = redis_client.hgetall(f"job:{job_id}")
    if not job_data:
        return None
    
    # Parse JSON fields if they exist
    if "request" in job_data:
        job_data["request"] = json.loads(job_data["request"])
    if "result" in job_data and job_data["result"]:
        job_data["result"] = json.loads(job_data["result"])
    
    return job_data


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Talent Analytics API",
        "version": "1.0.0"
    }


@app.post("/inference/trigger", response_model=InferenceResponse)
async def trigger_inference(request: InferenceRequest):
    """
    Trigger an inference job for talent analytics.
    
    Analysis types:
    - retention: Predict employee termination probability
    - skill_gap: Analyze skill gaps for employees/departments
    - promotion: Analyze promotion readiness
    - rotation: Analyze department rotation possibilities
    """
    valid_types = ["retention", "skill_gap", "promotion", "rotation"]
    
    if request.analysis_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid analysis_type. Must be one of: {valid_types}"
        )
    
    # Create job
    job_data = {
        "analysis_type": request.analysis_type,
        "employee_ids": request.employee_ids,
        "department_ids": request.department_ids,
        "include_shap": request.include_shap,
        "callback_url": request.callback_url
    }
    
    job_id = create_job(job_data)
    
    return InferenceResponse(
        job_id=job_id,
        status="pending",
        message=f"Job created successfully. Use /inference/status/{job_id} to check progress.",
        created_at=datetime.now().isoformat()
    )


@app.get("/inference/status/{job_id}", response_model=JobStatus)
async def get_inference_status(job_id: str):
    """Get the status of an inference job."""
    job_data = get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return JobStatus(**job_data)


@app.get("/inference/result/{job_id}")
async def get_inference_result(job_id: str):
    """Get the result of a completed inference job."""
    job_data = get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not completed. Current status: {job_data['status']}"
        )
    
    # Return the result directly
    return JSONResponse(content=job_data.get("result", {}))


@app.get("/inference/jobs")
async def list_jobs(limit: int = 10, status: Optional[str] = None):
    """List recent inference jobs."""
    # Get all job keys
    job_keys = redis_client.keys("job:*")
    
    jobs = []
    for key in job_keys[:limit]:
        job_id = key.split(":")[1]
        job_data = get_job_status(job_id)
        
        if status and job_data["status"] != status:
            continue
            
        jobs.append({
            "job_id": job_id,
            "status": job_data["status"],
            "analysis_type": job_data.get("request", {}).get("analysis_type"),
            "created_at": job_data["created_at"],
            "updated_at": job_data["updated_at"]
        })
    
    return {"jobs": jobs, "total": len(jobs)}


@app.delete("/inference/job/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a pending or processing job."""
    job_data = get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if job_data["status"] in ["completed", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job_data['status']}"
        )
    
    # Update job status
    redis_client.hset(f"job:{job_id}", "status", "cancelled")
    redis_client.hset(f"job:{job_id}", "updated_at", datetime.now().isoformat())
    
    return {"message": f"Job {job_id} cancelled successfully"}


@app.post("/inference/batch")
async def trigger_batch_inference(requests: List[InferenceRequest]):
    """Trigger multiple inference jobs at once."""
    job_ids = []
    
    for request in requests:
        job_data = {
            "analysis_type": request.analysis_type,
            "employee_ids": request.employee_ids,
            "department_ids": request.department_ids,
            "include_shap": request.include_shap,
            "callback_url": request.callback_url
        }
        job_id = create_job(job_data)
        job_ids.append(job_id)
    
    return {
        "message": f"Created {len(job_ids)} jobs successfully",
        "job_ids": job_ids,
        "created_at": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)