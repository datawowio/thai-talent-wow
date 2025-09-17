#!/usr/bin/env python3
"""
Deploy retention model from Compute Engine to Vertex AI
This script runs ON your Compute Engine instance
"""

import os
import sys
import json
import pickle
import shutil
from datetime import datetime
from google.cloud import aiplatform
from google.cloud import storage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config

class ComputeEngineToVertexAI:
    """Deploy model from Compute Engine to Vertex AI"""
    
    def __init__(self, project_id, region="asia-southeast1", bucket_name=None):
        """
        Initialize deployment from Compute Engine
        
        Args:
            project_id: Your GCP project ID
            region: Vertex AI region (default: asia-southeast1 for Singapore)
            bucket_name: GCS bucket for model artifacts (will create if None)
        """
        self.project_id = project_id
        self.region = region
        self.bucket_name = bucket_name or f"{project_id}-vertex-models"
        
        # Initialize Vertex AI
        aiplatform.init(project=project_id, location=region)
        
        # Initialize GCS client
        self.storage_client = storage.Client(project=project_id)
        
    def prepare_model_artifacts(self):
        """
        Prepare model artifacts for Vertex AI deployment
        Creates a directory with all necessary files
        """
        print("Preparing model artifacts...")
        
        # Create temporary directory for model package
        model_dir = "vertex_model_package"
        if os.path.exists(model_dir):
            shutil.rmtree(model_dir)
        os.makedirs(model_dir)
        
        # Copy model files
        shutil.copy(config.MODEL_PATH, f"{model_dir}/model.pkl")
        shutil.copy(config.MODEL_CONFIG_PATH, f"{model_dir}/model_config.json")
        
        # Create predictor script
        predictor_content = '''
import os
import json
import pickle
import pandas as pd
import numpy as np
from typing import Dict, List, Any

class RetentionPredictor:
    """Custom predictor for Vertex AI"""
    
    def __init__(self):
        """Load model and config from artifacts directory"""
        artifacts_dir = os.environ.get("AIP_STORAGE_URI", ".")
        
        # Load model
        model_path = os.path.join(artifacts_dir, "model.pkl")
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        
        # Load config
        config_path = os.path.join(artifacts_dir, "model_config.json")
        with open(config_path, 'r') as f:
            self.model_config = json.load(f)
    
    def predict(self, instances: List[Dict[str, Any]]) -> Dict[str, List]:
        """
        Make predictions for Vertex AI
        
        Args:
            instances: List of input instances
            
        Returns:
            Dictionary with predictions
        """
        predictions = []
        
        for instance in instances:
            # Convert to DataFrame
            df = pd.DataFrame([instance])
            
            # Ensure all required features are present
            for feature in self.model_config['features']:
                if feature not in df.columns:
                    df[feature] = 0
            
            # Select features
            df = df[self.model_config['features']]
            
            # Make prediction
            prob = self.model.predict_proba(df)[0][1] if hasattr(self.model, 'predict_proba') else self.model.predict(df)[0]
            prob = float(np.clip(prob, 0, 1))
            
            prediction = {
                'termination_probability': prob,
                'predicted_termination': prob > self.model_config.get('optimal_threshold', 0.5),
                'risk_level': 'HIGH' if prob >= 0.7 else 'MEDIUM' if prob >= 0.4 else 'LOW'
            }
            predictions.append(prediction)
        
        return {"predictions": predictions}
'''
        
        with open(f"{model_dir}/predictor.py", 'w') as f:
            f.write(predictor_content)
        
        # Create requirements.txt
        requirements = """
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
catboost>=1.2.0
google-cloud-aiplatform>=1.36.0
google-cloud-storage>=2.10.0
"""
        with open(f"{model_dir}/requirements.txt", 'w') as f:
            f.write(requirements)
        
        print(f"Model artifacts prepared in {model_dir}/")
        return model_dir
    
    def upload_to_gcs(self, model_dir):
        """
        Upload model artifacts to Google Cloud Storage
        """
        print(f"Uploading to GCS bucket: {self.bucket_name}...")
        
        # Create bucket if it doesn't exist
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(
                    self.bucket_name,
                    location=self.region
                )
                print(f"Created bucket: {self.bucket_name}")
        except Exception as e:
            print(f"Using existing bucket: {self.bucket_name}")
            bucket = self.storage_client.bucket(self.bucket_name)
        
        # Upload files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        gcs_path = f"retention_model_{timestamp}"
        
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, model_dir)
                blob_name = f"{gcs_path}/{relative_path}"
                
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(local_path)
                print(f"Uploaded: {blob_name}")
        
        gcs_uri = f"gs://{self.bucket_name}/{gcs_path}"
        print(f"Model artifacts uploaded to: {gcs_uri}")
        return gcs_uri
    
    def create_and_deploy_model(self, gcs_uri, model_display_name=None):
        """
        Create Vertex AI model and deploy to endpoint
        """
        if not model_display_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_display_name = f"retention-model-{timestamp}"
        
        print(f"Creating Vertex AI model: {model_display_name}")
        
        # Upload model to Vertex AI Model Registry
        model = aiplatform.Model.upload(
            display_name=model_display_name,
            artifact_uri=gcs_uri,
            serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-3:latest",
            serving_container_predict_route="/predict",
            serving_container_health_route="/health",
            description="Employee retention prediction model",
            labels={"model_type": "retention", "framework": "sklearn"}
        )
        
        print(f"Model created: {model.display_name}")
        print(f"Model resource name: {model.resource_name}")
        
        # Create endpoint
        endpoint_display_name = f"{model_display_name}-endpoint"
        endpoint = aiplatform.Endpoint.create(
            display_name=endpoint_display_name,
            description="Endpoint for employee retention predictions"
        )
        
        print(f"Endpoint created: {endpoint.display_name}")
        
        # Deploy model to endpoint
        deployed_model = model.deploy(
            endpoint=endpoint,
            deployed_model_display_name=model_display_name,
            machine_type="n1-standard-2",
            min_replica_count=1,
            max_replica_count=3,
            traffic_percentage=100,
            sync=True
        )
        
        print(f"Model deployed successfully!")
        
        return {
            "model_name": model.display_name,
            "model_id": model.resource_name,
            "endpoint_name": endpoint.display_name,
            "endpoint_id": endpoint.resource_name,
            "endpoint_uri": f"https://{self.region}-aiplatform.googleapis.com/v1/{endpoint.resource_name}:predict"
        }
    
    def deploy_full_pipeline(self):
        """
        Execute full deployment pipeline
        """
        print("=== Starting Vertex AI Deployment from Compute Engine ===\n")
        
        # Step 1: Prepare artifacts
        model_dir = self.prepare_model_artifacts()
        
        # Step 2: Upload to GCS
        gcs_uri = self.upload_to_gcs(model_dir)
        
        # Step 3: Create and deploy model
        deployment_info = self.create_and_deploy_model(gcs_uri)
        
        # Step 4: Save deployment info
        with open("vertex_deployment_info.json", 'w') as f:
            json.dump(deployment_info, f, indent=2)
        
        print("\n=== Deployment Complete ===")
        print(f"Endpoint URI: {deployment_info['endpoint_uri']}")
        print("\nDeployment info saved to: vertex_deployment_info.json")
        
        return deployment_info

def main():
    """Main deployment function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy model from Compute Engine to Vertex AI')
    parser.add_argument('--project-id', required=True, help='GCP Project ID')
    parser.add_argument('--region', default='asia-southeast1', help='Vertex AI region')
    parser.add_argument('--bucket', help='GCS bucket name (auto-generated if not provided)')
    
    args = parser.parse_args()
    
    # First, ensure model exists
    if not os.path.exists(config.MODEL_PATH):
        print("ERROR: Model not found. Please run main.py to train the model first.")
        sys.exit(1)
    
    # Deploy
    deployer = ComputeEngineToVertexAI(
        project_id=args.project_id,
        region=args.region,
        bucket_name=args.bucket
    )
    
    deployment_info = deployer.deploy_full_pipeline()
    
    print("\n✅ Your model is now deployed and ready for predictions!")
    print("\nTo test your endpoint, use the test script: python test_vertex_endpoint.py")

if __name__ == "__main__":
    main()