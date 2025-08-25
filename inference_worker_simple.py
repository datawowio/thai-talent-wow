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

from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InferenceWorker:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        self.worker_id = os.getenv('HOSTNAME', 'worker-default')
        logger.info(f"Worker {self.worker_id} initialized")
        
    def run(self):
        """Main worker loop"""
        logger.info(f"Worker {self.worker_id} started and waiting for jobs...")
        
        while True:
            try:
                # Check for jobs in the queue
                job_data = self.redis_client.blpop('job_queue', timeout=5)
                
                if job_data:
                    _, job_id = job_data
                    job_id = job_id.decode('utf-8') if isinstance(job_id, bytes) else job_id
                    
                    # Fetch full job data from Redis
                    job_info = self.redis_client.hgetall(f"job:{job_id}")
                    if not job_info:
                        logger.error(f"Job {job_id} not found in Redis")
                        continue
                    
                    job = {
                        'job_id': job_id,
                        'request': json.loads(job_info['request']),
                        'status': job_info['status'],
                        'created_at': job_info['created_at']
                    }
                    
                    logger.info(f"Processing job {job_id}")
                    
                    # Update job status
                    self.redis_client.hset(f"job:{job_id}", mapping={
                        'status': 'processing',
                        'worker_id': self.worker_id,
                        'started_at': datetime.now().isoformat()
                    })
                    
                    # Simple demo processing
                    result = self.process_job(job)
                    
                    # Store result
                    self.redis_client.hset(f"job:{job_id}", mapping={
                        'status': 'completed',
                        'result': json.dumps(result),
                        'completed_at': datetime.now().isoformat()
                    })
                    
                    logger.info(f"Job {job_id} completed successfully")
                    
            except Exception as e:
                logger.error(f"Error processing job: {str(e)}")
                logger.error(traceback.format_exc())
                
                if 'job_id' in locals():
                    self.redis_client.hset(f"job:{job_id}", mapping={
                        'status': 'failed',
                        'error': str(e),
                        'failed_at': datetime.now().isoformat()
                    })
    
    def process_job(self, job):
        """Process a job based on its type"""
        job_type = job.get('type', 'unknown')
        
        # Simulate processing
        time.sleep(2)
        
        # Return demo result based on job type
        if job_type == 'termination_prediction':
            return {
                'high_risk_employees': 5,
                'medium_risk_employees': 12,
                'low_risk_employees': 83,
                'message': 'Termination prediction analysis completed'
            }
        elif job_type == 'skill_gap_analysis':
            return {
                'employees_analyzed': 100,
                'avg_skill_gap': 0.35,
                'departments_analyzed': 10,
                'message': 'Skill gap analysis completed'
            }
        elif job_type == 'promotion_analysis':
            return {
                'eligible_employees': 15,
                'ready_for_promotion': 8,
                'need_development': 7,
                'message': 'Promotion analysis completed'
            }
        else:
            return {
                'status': 'completed',
                'message': f'Job type {job_type} processed successfully'
            }

if __name__ == "__main__":
    worker = InferenceWorker()
    worker.run()