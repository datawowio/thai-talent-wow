"""
Simple Retention ML Pipeline API
"""

import os
import logging
from typing import Optional, Dict
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, status, Header
from pydantic import BaseModel
import subprocess
import sys
import threading
import time
import traceback
import json
import pandas as pd
from database import db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("retention_pipeline_api")

# API Keys Configuration
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

# Rate limiting storage
request_counts = {}

# FastAPI app
app = FastAPI(
    title="TH.AI Retention ML Pipeline",
    description="Simple API to trigger retention ML pipeline and get job status",
    version="1.0.0"
)

# Request/Response models
class RetentionPipelineRequest(BaseModel):
    task_id: str
    gcs_bucket: Optional[str] = None

class RetentionPipelineResponse(BaseModel):
    job_id: str
    status: str
    message: str
    started_at: str

# Track running retention jobs
retention_jobs = {}

# Authentication functions
def verify_api_key(x_api_key: Optional[str] = Header(None)) -> Dict:
    """Verify API key and return user info"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header"
        )
    
    # Check if API key exists
    if x_api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    user_info = API_KEYS[x_api_key]
    
    # Check rate limiting
    current_time = datetime.now()
    time_window = current_time.strftime("%Y-%m-%d-%H")
    rate_limit_key = f"{x_api_key}:{time_window}"
    
    if rate_limit_key not in request_counts:
        request_counts[rate_limit_key] = 0
    
    request_counts[rate_limit_key] += 1
    
    if request_counts[rate_limit_key] > user_info["rate_limit"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {user_info['rate_limit']} requests per hour"
        )
    
    return user_info

def validate_output_files():
    """Validate that expected output files were created"""
    expected_files = [
        'output/feature_engineered_data.csv',
        'output/model/model.pkl',
        'output/model/model_config.json',
        'output/model/model_interpretation.pkl',
        'output/model_result.parquet',
        'output/termination_result.json'
    ]
    
    validation_results = {}
    for file_path in expected_files:
        full_path = os.path.join(os.path.dirname(__file__), '..', file_path)
        validation_results[file_path] = os.path.exists(full_path)
    
    return validation_results

def save_results_to_database(job_id: str):
    """Save pipeline results to PostgreSQL database"""
    try:
        # Use /app paths since we're in container
        termination_file = '/app/output/termination_result.json'
        logger.info(f"Job {job_id}: Checking for termination file at {termination_file}")
        
        if os.path.exists(termination_file):
            logger.info(f"Job {job_id}: Found termination file, loading data...")
            with open(termination_file, 'r') as f:
                termination_data = json.load(f)
            
            logger.info(f"Job {job_id}: Loaded termination data with {len(termination_data)} entries")
            
            # Save to termination_results table
            if db.save_termination_results(job_id, termination_data):
                logger.info(f"Job {job_id}: Termination results saved to database successfully")
            else:
                logger.error(f"Job {job_id}: Failed to save termination results to database")
        else:
            logger.error(f"Job {job_id}: Termination results file not found at {termination_file}")
            # List files in output directory for debugging
            output_dir = '/app/output'
            if os.path.exists(output_dir):
                files = os.listdir(output_dir)
                logger.info(f"Job {job_id}: Files in {output_dir}: {files}")
            else:
                logger.error(f"Job {job_id}: Output directory {output_dir} does not exist")
        
        # Read individual predictions
        predictions_file = '/app/output/model/model_result.parquet'
        logger.info(f"Job {job_id}: Checking for predictions file at {predictions_file}")
        
        if os.path.exists(predictions_file):
            logger.info(f"Job {job_id}: Found predictions file, loading data...")
            predictions_df = pd.read_parquet(predictions_file)
            logger.info(f"Job {job_id}: Loaded predictions with shape {predictions_df.shape}")
            
            # Save to employee predictions table (if it exists)
            if db.save_employee_predictions(job_id, predictions_df):
                logger.info(f"Job {job_id}: Employee predictions saved to database successfully")
            else:
                logger.error(f"Job {job_id}: Failed to save employee predictions to database")
        else:
            logger.error(f"Job {job_id}: Predictions file not found at {predictions_file}")
            # List files in model directory for debugging
            model_dir = '/app/output/model'
            if os.path.exists(model_dir):
                files = os.listdir(model_dir)
                logger.info(f"Job {job_id}: Files in {model_dir}: {files}")
            else:
                logger.error(f"Job {job_id}: Model directory {model_dir} does not exist")
                
    except Exception as e:
        logger.error(f"Job {job_id}: Error saving results to database: {str(e)}")
        import traceback
        logger.error(f"Job {job_id}: Full traceback: {traceback.format_exc()}")

def run_retention_pipeline(job_id: str, gcs_bucket: Optional[str] = None):
    """Execute the retention ML pipeline"""
    def execute_pipeline():
        start_time = time.time()
        try:
            logger.info(f"Starting retention pipeline job {job_id} with GCS bucket: {gcs_bucket}")
            
            retention_jobs[job_id]["status"] = "running"
            retention_jobs[job_id]["started_at"] = datetime.now().isoformat()
            retention_jobs[job_id]["progress"] = "Initializing pipeline..."
            
            # Set up environment
            env = os.environ.copy()
            if gcs_bucket:
                env['GCS_BUCKET_PATH'] = gcs_bucket
                # Extract date partition from gcs_bucket (e.g., "th-ai-talent-data/2025-09-05" -> "2025-09-05")
                if '/' in gcs_bucket:
                    date_partition = gcs_bucket.split('/')[-1]
                    env['GCS_DATE_PARTITION'] = date_partition
                    logger.info(f"Job {job_id}: Using GCS bucket: {gcs_bucket}, date partition: {date_partition}")
                else:
                    logger.info(f"Job {job_id}: Using GCS bucket: {gcs_bucket}")
            else:
                logger.info(f"Job {job_id}: Using local data files")
            
            retention_jobs[job_id]["progress"] = "Executing ML pipeline..."
            
            # Execute the ML pipeline
            # Try Docker path first, then local development path
            docker_script = os.path.join('/app', 'predictive_retention', 'main.py')
            local_script = os.path.join(os.path.dirname(__file__), '..', 'predictive_retention', 'main.py')
            
            if os.path.exists(docker_script):
                pipeline_script = docker_script
            elif os.path.exists(local_script):
                pipeline_script = local_script
            else:
                raise FileNotFoundError(f"Pipeline script not found in Docker path ({docker_script}) or local path ({local_script})")
            
            logger.info(f"Job {job_id}: Executing pipeline script: {pipeline_script}")
            
            # Run pipeline with real-time output streaming
            process = subprocess.Popen([
                sys.executable, 
                '-u',  # Unbuffered output
                pipeline_script
            ], 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd='/app',
            bufsize=1,  # Line buffered
            universal_newlines=True
            )
            
            # Stream output in real-time
            output_lines = []
            for line in iter(process.stdout.readline, ''):
                if line:
                    line = line.rstrip()
                    output_lines.append(line)
                    logger.info(f"Job {job_id} pipeline: {line}")
            
            # Wait for process to complete
            process.wait()
            result = subprocess.CompletedProcess(
                args=[sys.executable, pipeline_script],
                returncode=process.returncode,
                stdout='\n'.join(output_lines)
            )
            
            execution_time = time.time() - start_time
            retention_jobs[job_id]["execution_time_seconds"] = round(execution_time, 2)
            
            if result.returncode == 0:
                logger.info(f"Job {job_id}: Pipeline completed successfully in {execution_time:.2f} seconds")
                
                retention_jobs[job_id]["progress"] = "Validating output files..."
                output_validation = validate_output_files()
                
                # Save results to database if output files exist
                if output_validation.get('output/termination_result.json', False):
                    retention_jobs[job_id]["progress"] = "Saving results to database..."
                    save_results_to_database(job_id)
                
                retention_jobs[job_id]["status"] = "completed"
                retention_jobs[job_id]["completed_at"] = datetime.now().isoformat()
                retention_jobs[job_id]["progress"] = "Pipeline completed successfully"
                retention_jobs[job_id]["output"] = f"Retention pipeline completed successfully for GCS bucket: {gcs_bucket or 'local'}"
                retention_jobs[job_id]["stdout"] = result.stdout[-2000:] if result.stdout else ""
                retention_jobs[job_id]["output_files"] = output_validation
                retention_jobs[job_id]["model_saved"] = output_validation.get('output/model/model.pkl', False)
                
                successful_files = sum(1 for v in output_validation.values() if v)
                retention_jobs[job_id]["output_files_count"] = f"{successful_files}/{len(output_validation)}"
                
                if successful_files < len(output_validation):
                    logger.warning(f"Job {job_id}: Some output files missing: {output_validation}")
                    retention_jobs[job_id]["warnings"] = f"Some output files missing: {successful_files}/{len(output_validation)} files created"
                
            else:
                logger.error(f"Job {job_id}: Pipeline failed with exit code {result.returncode}")
                retention_jobs[job_id]["status"] = "failed"
                retention_jobs[job_id]["completed_at"] = datetime.now().isoformat()
                retention_jobs[job_id]["progress"] = f"Pipeline failed (exit code: {result.returncode})"
                retention_jobs[job_id]["error"] = f"Pipeline failed with exit code {result.returncode}"
                retention_jobs[job_id]["stderr"] = result.stderr[-2000:] if result.stderr else ""
                retention_jobs[job_id]["stdout"] = result.stdout[-1000:] if result.stdout else ""
                
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.error(f"Job {job_id}: Pipeline timed out after {execution_time:.2f} seconds")
            retention_jobs[job_id]["status"] = "failed"
            retention_jobs[job_id]["completed_at"] = datetime.now().isoformat()
            retention_jobs[job_id]["progress"] = "Pipeline timed out"
            retention_jobs[job_id]["error"] = f"Pipeline execution timed out after {execution_time:.2f} seconds (30 minute limit)"
            retention_jobs[job_id]["execution_time_seconds"] = round(execution_time, 2)
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Job {job_id}: Pipeline execution error: {str(e)}")
            retention_jobs[job_id]["status"] = "failed"
            retention_jobs[job_id]["completed_at"] = datetime.now().isoformat()
            retention_jobs[job_id]["progress"] = f"Pipeline error: {str(e)[:100]}..."
            retention_jobs[job_id]["error"] = f"Pipeline execution error: {str(e)}"
            retention_jobs[job_id]["traceback"] = traceback.format_exc()[-2000:]
            retention_jobs[job_id]["execution_time_seconds"] = round(execution_time, 2)
    
    # Run in background thread
    thread = threading.Thread(target=execute_pipeline, name=f"retention-pipeline-{job_id}")
    thread.daemon = True
    thread.start()
    
    logger.info(f"Job {job_id}: Background pipeline thread started")

# API Endpoints
@app.get("/")
async def root():
    """API health check"""
    return {
        "message": "TH.AI Retention ML Pipeline API",
        "version": "1.0.0",
        "status": "healthy",
        "authentication": "Required (X-API-Key header)",
        "endpoints": {
            "trigger": "POST /trigger-retention-pipeline",
            "status": "GET /retention-job-status/{job_id}",
            "list": "GET /retention-jobs"
        },
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.post("/trigger-retention-pipeline", response_model=RetentionPipelineResponse)
async def trigger_retention_pipeline(
    request: RetentionPipelineRequest,
    user_info: Dict = Depends(verify_api_key)
):
    """Trigger the retention prediction pipeline"""
    job_id = request.task_id
    
    # Check if task_id already exists
    if job_id in retention_jobs:
        raise HTTPException(
            status_code=400,
            detail=f"Task ID '{job_id}' already exists. Please use a unique task ID."
        )
    
    # Check if a job is already running
    for job in retention_jobs.values():
        if job["status"] == "running":
            raise HTTPException(
                status_code=400,
                detail="A retention pipeline is already running. Please wait for it to complete."
            )
    
    # Initialize job tracking
    retention_jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "gcs_bucket": request.gcs_bucket,
        "api_user": user_info["name"]
    }
    
    # Start pipeline 
    run_retention_pipeline(job_id, request.gcs_bucket)
    
    return RetentionPipelineResponse(
        job_id=job_id,
        status="queued",
        message=f"Retention pipeline triggered. Use /retention-job-status/{job_id} to check progress.",
        started_at=datetime.now().isoformat()
    )

@app.get("/retention-job-status/{job_id}")
async def get_retention_job_status(job_id: str, user_info: Dict = Depends(verify_api_key)):
    """Get the status of a retention pipeline job"""
    if job_id not in retention_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Retention job {job_id} not found"
        )
    
    job = retention_jobs[job_id]
    response = {
        "job_id": job_id,
        "status": job["status"],
        "created_at": job["created_at"],
        "api_user": job.get("api_user")
    }
    
    # Add progress information
    if "progress" in job:
        response["progress"] = job["progress"]
    
    # Add timing information
    if "started_at" in job:
        response["started_at"] = job["started_at"]
    if "completed_at" in job:
        response["completed_at"] = job["completed_at"]
    if "execution_time_seconds" in job:
        response["execution_time_seconds"] = job["execution_time_seconds"]
    
    # Add GCS bucket information
    if "gcs_bucket" in job and job["gcs_bucket"]:
        response["gcs_bucket"] = job["gcs_bucket"]
    
    # Add error information for failed jobs
    if job["status"] == "failed":
        if "error" in job:
            response["error"] = job["error"]
        if "stderr" in job and job["stderr"]:
            response["stderr_preview"] = job["stderr"][:500] if len(job["stderr"]) > 500 else job["stderr"]
    
    # Add success information for completed jobs
    if job["status"] == "completed":
        if "output" in job:
            response["output_preview"] = job["output"][:500] if len(job["output"]) > 500 else job["output"]
        if "output_files" in job:
            response["output_files"] = job["output_files"]
        if "output_files_count" in job:
            response["output_files_count"] = job["output_files_count"]
        if "model_saved" in job:
            response["model_saved"] = job["model_saved"]
        if "warnings" in job:
            response["warnings"] = job["warnings"]
    
    # Add stdout for debugging
    if "stdout" in job and job["stdout"]:
        response["stdout_preview"] = job["stdout"][:500] if len(job["stdout"]) > 500 else job["stdout"]
    
    return response

@app.get("/retention-jobs")
async def list_retention_jobs(user_info: Dict = Depends(verify_api_key)):
    """List all retention pipeline jobs"""
    jobs_summary = []
    for job_id, job in retention_jobs.items():
        jobs_summary.append({
            "job_id": job_id,
            "status": job["status"],
            "created_at": job["created_at"],
            "gcs_bucket": job.get("gcs_bucket"),
            "api_user": job.get("api_user")
        })
    
    return {
        "total": len(jobs_summary),
        "jobs": jobs_summary
    }

# Run the app
if __name__ == "__main__":
    import uvicorn
    print("Starting TH.AI Retention ML Pipeline API...")
    port = int(os.getenv("PORT", 8080))
    print(f"API Docs: http://localhost:{port}/docs")
    
    uvicorn.run(
        "retention_api:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )