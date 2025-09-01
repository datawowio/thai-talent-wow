import os
import sys
import json
import redis
import time
import traceback
from datetime import datetime
import pandas as pd
import logging

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from predictive_retention.model import load_model, predict_result, save_model_result
from predictive_retention.feature_engineering import feature_engineering
from predictive_retention.termination_analysis import generate_termination_analysis
# Import main function from skill_promotion_management that handles all analyses
from skill_promotion_management.main import main as skill_management_main
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis connection
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)


class InferenceWorker:
    def __init__(self):
        self.redis_client = redis_client
        self.worker_id = f"worker-{os.getpid()}"
        logger.info(f"Initialized worker: {self.worker_id}")
    
    def update_job_status(self, job_id: str, status: str, progress: float = None, 
                         result: dict = None, error: str = None):
        """Update job status in Redis."""
        updates = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }
        
        if progress is not None:
            updates["progress"] = str(progress)
        
        if result is not None:
            updates["result"] = json.dumps(result)
        
        if error is not None:
            updates["error"] = error
        
        self.redis_client.hset(f"job:{job_id}", mapping=updates)
        logger.info(f"Updated job {job_id} status to: {status}")
    
    def process_retention_analysis(self, job_id: str, request: dict) -> dict:
        """Process retention/termination prediction analysis."""
        logger.info(f"Processing retention analysis for job {job_id}")
        
        try:
            # Update progress
            self.update_job_status(job_id, "processing", progress=0.1)
            
            # Load or prepare feature engineering data
            if os.path.exists(config.FEATURE_ENGINEERED_PATH):
                feature_engineered_df = pd.read_csv(config.FEATURE_ENGINEERED_PATH)
            else:
                logger.info("Preparing feature engineering data...")
                feature_engineered_df = feature_engineering()
                feature_engineered_df.to_csv(config.FEATURE_ENGINEERED_PATH, index=False)
            
            self.update_job_status(job_id, "processing", progress=0.3)
            
            # Load model and make predictions
            model, model_config = load_model()
            prediction_df, feature_importance_df, model_interpretation = predict_result(feature_engineered_df)
            
            self.update_job_status(job_id, "processing", progress=0.6)
            
            # Filter by employee IDs if specified
            if request.get("employee_ids"):
                prediction_df = prediction_df[prediction_df["emp_id"].isin(request["employee_ids"])]
            
            # Generate analysis
            if request.get("include_shap", True):
                save_model_result(prediction_df, feature_importance_df, model_interpretation)
                result = generate_termination_analysis(model_config, model_interpretation, prediction_df)
            else:
                result = {
                    "predictions": prediction_df.to_dict(orient="records"),
                    "feature_importance": feature_importance_df.to_dict(orient="records")
                }
            
            self.update_job_status(job_id, "processing", progress=0.9)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in retention analysis: {str(e)}")
            raise
    
    def process_skill_gap_analysis(self, job_id: str, request: dict) -> dict:
        """Process skill gap analysis."""
        logger.info(f"Processing skill gap analysis for job {job_id}")
        
        try:
            self.update_job_status(job_id, "processing", progress=0.1)
            
            result = {}
            
            # Employee skill gap analysis
            if request.get("employee_ids") or not request.get("department_ids"):
                employee_result = employee_skill_gap_analysis()
                if request.get("employee_ids"):
                    # Filter by employee IDs
                    employee_result = [
                        emp for emp in employee_result 
                        if emp.get("employee_id") in request["employee_ids"]
                    ]
                result["employee_skill_gaps"] = employee_result
            
            self.update_job_status(job_id, "processing", progress=0.5)
            
            # Department skill gap analysis
            if request.get("department_ids") or not request.get("employee_ids"):
                department_result = department_skill_gap_analysis()
                if request.get("department_ids"):
                    # Filter by department IDs
                    department_result = [
                        dept for dept in department_result 
                        if str(dept.get("department_id")) in request["department_ids"]
                    ]
                result["department_skill_gaps"] = department_result
            
            self.update_job_status(job_id, "processing", progress=0.9)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in skill gap analysis: {str(e)}")
            raise
    
    def process_promotion_analysis(self, job_id: str, request: dict) -> dict:
        """Process promotion readiness analysis."""
        logger.info(f"Processing promotion analysis for job {job_id}")
        
        try:
            self.update_job_status(job_id, "processing", progress=0.1)
            
            # Run promotion analysis
            result = promotion_readiness_analysis()
            
            self.update_job_status(job_id, "processing", progress=0.5)
            
            # Filter by employee IDs if specified
            if request.get("employee_ids"):
                for category in result:
                    if "employees" in result[category]:
                        result[category]["employees"] = [
                            emp for emp in result[category]["employees"]
                            if emp.get("employee_id") in request["employee_ids"]
                        ]
            
            # Filter by department IDs if specified
            if request.get("department_ids"):
                for category in result:
                    if "employees" in result[category]:
                        result[category]["employees"] = [
                            emp for emp in result[category]["employees"]
                            if str(emp.get("department_id")) in request["department_ids"]
                        ]
            
            self.update_job_status(job_id, "processing", progress=0.9)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in promotion analysis: {str(e)}")
            raise
    
    def process_rotation_analysis(self, job_id: str, request: dict) -> dict:
        """Process department rotation analysis."""
        logger.info(f"Processing rotation analysis for job {job_id}")
        
        try:
            self.update_job_status(job_id, "processing", progress=0.1)
            
            # Run rotation analysis
            result = rotation_analysis()
            
            self.update_job_status(job_id, "processing", progress=0.5)
            
            # Filter by employee IDs if specified
            if request.get("employee_ids"):
                result = [
                    emp for emp in result 
                    if emp.get("employee_id") in request["employee_ids"]
                ]
            
            # Filter by department IDs if specified
            if request.get("department_ids"):
                filtered_result = []
                for emp in result:
                    # Filter target departments
                    if "target_departments" in emp:
                        emp["target_departments"] = [
                            dept for dept in emp["target_departments"]
                            if str(dept.get("department_id")) in request["department_ids"]
                        ]
                        if emp["target_departments"]:
                            filtered_result.append(emp)
                result = filtered_result
            
            self.update_job_status(job_id, "processing", progress=0.9)
            
            return {"rotation_analysis": result}
            
        except Exception as e:
            logger.error(f"Error in rotation analysis: {str(e)}")
            raise
    
    def process_job(self, job_id: str):
        """Process a single job."""
        logger.info(f"Processing job: {job_id}")
        
        try:
            # Get job data
            job_data = self.redis_client.hgetall(f"job:{job_id}")
            if not job_data:
                logger.error(f"Job {job_id} not found")
                return
            
            # Parse request data
            request = json.loads(job_data["request"])
            analysis_type = request["analysis_type"]
            
            # Update status to processing
            self.update_job_status(job_id, "processing", progress=0.0)
            
            # Process based on analysis type
            if analysis_type == "retention":
                result = self.process_retention_analysis(job_id, request)
            elif analysis_type == "skill_gap":
                result = self.process_skill_gap_analysis(job_id, request)
            elif analysis_type == "promotion":
                result = self.process_promotion_analysis(job_id, request)
            elif analysis_type == "rotation":
                result = self.process_rotation_analysis(job_id, request)
            else:
                raise ValueError(f"Unknown analysis type: {analysis_type}")
            
            # Update job as completed
            self.update_job_status(job_id, "completed", progress=1.0, result=result)
            
            # Send callback if specified
            if request.get("callback_url"):
                self.send_callback(request["callback_url"], job_id, result)
            
            logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            error_msg = f"Error processing job {job_id}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.update_job_status(job_id, "failed", error=str(e))
    
    def send_callback(self, callback_url: str, job_id: str, result: dict):
        """Send callback to the specified URL."""
        try:
            import requests
            payload = {
                "job_id": job_id,
                "status": "completed",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            response = requests.post(callback_url, json=payload, timeout=30)
            logger.info(f"Callback sent to {callback_url}, status: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to send callback: {str(e)}")
    
    def run(self):
        """Main worker loop."""
        logger.info(f"Worker {self.worker_id} started")
        
        while True:
            try:
                # Get job from queue (blocking with timeout)
                job_data = self.redis_client.brpop("job_queue", timeout=5)
                
                if job_data:
                    _, job_id = job_data
                    logger.info(f"Worker {self.worker_id} picked up job: {job_id}")
                    self.process_job(job_id)
                
            except KeyboardInterrupt:
                logger.info(f"Worker {self.worker_id} shutting down...")
                break
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
                time.sleep(5)  # Wait before retrying


if __name__ == "__main__":
    # Get worker concurrency from environment
    concurrency = int(os.getenv("WORKER_CONCURRENCY", 1))
    
    if concurrency > 1:
        # Multi-process mode
        import multiprocessing
        
        processes = []
        for i in range(concurrency):
            p = multiprocessing.Process(target=lambda: InferenceWorker().run())
            p.start()
            processes.append(p)
        
        # Wait for all processes
        for p in processes:
            p.join()
    else:
        # Single process mode
        worker = InferenceWorker()
        worker.run()