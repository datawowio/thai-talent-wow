import os
import sys
import json
import pickle
import pandas as pd
import numpy as np
from google.cloud import aiplatform
from google.cloud.aiplatform import Model
from google.cloud.aiplatform.prediction import LocalModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config
from predictive_retention.model import load_model

class RetentionPredictor:
    """Vertex AI compatible predictor for employee retention"""
    
    def __init__(self, model_uri=None):
        if model_uri:
            # Load from Vertex AI model registry
            self.model = Model(model_uri)
            self.model_config = None
        else:
            # Load local model
            self.model, self.model_config = load_model()
    
    def predict(self, instances):
        """
        Make predictions for employee retention
        
        Args:
            instances: List of dictionaries containing employee features
            
        Returns:
            List of prediction dictionaries with probabilities and classifications
        """
        if not isinstance(instances, list):
            instances = [instances]
        
        predictions = []
        
        for instance in instances:
            # Convert instance to DataFrame with required features
            df = pd.DataFrame([instance])
            
            # Ensure all required features are present
            missing_features = set(self.model_config['features']) - set(df.columns)
            for feature in missing_features:
                df[feature] = 0  # Default value for missing features
            
            # Select only the features used by the model
            df = df[self.model_config['features']]
            
            # Make prediction
            prob = self.model.predict(df)[0]
            prob = np.clip(prob, 0, 1)
            
            prediction = {
                'employee_id': instance.get('emp_id', 'unknown'),
                'termination_probability': float(prob),
                'predicted_termination': bool(prob > self.model_config['optimal_threshold']),
                'risk_level': self._get_risk_level(prob),
                'confidence': self._get_confidence(prob)
            }
            
            predictions.append(prediction)
        
        return predictions
    
    def _get_risk_level(self, probability):
        """Convert probability to risk level"""
        if probability >= 0.7:
            return 'HIGH'
        elif probability >= 0.4:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _get_confidence(self, probability):
        """Calculate prediction confidence"""
        # Distance from 0.5 (neutral point)
        return abs(probability - 0.5) * 2

class VertexAIRetentionModel:
    """Wrapper for deploying retention model to Vertex AI"""
    
    def __init__(self, project_id, region="asia-southeast1"):
        aiplatform.init(project=project_id, location=region)
        self.project_id = project_id
        self.region = region
    
    def create_model(self, model_display_name="retention-predictor"):
        """Create and upload model to Vertex AI Model Registry"""
        
        # Create a local model artifact
        local_model = LocalModel.build_cpr_model(
            "vertex_ai/retention_predictor.py",
            "RetentionPredictor",
            requirements=["pandas", "numpy", "catboost", "scikit-learn"]
        )
        
        # Upload to Vertex AI
        model = local_model.upload(
            display_name=model_display_name,
            description="Employee retention prediction model"
        )
        
        return model
    
    def deploy_model(self, model, endpoint_display_name="retention-endpoint"):
        """Deploy model to Vertex AI endpoint"""
        
        endpoint = aiplatform.Endpoint.create(
            display_name=endpoint_display_name,
            description="Real-time employee retention predictions"
        )
        
        deployed_model = model.deploy(
            endpoint=endpoint,
            deployed_model_display_name="retention-predictor-v1",
            machine_type="n1-standard-2",
            min_replica_count=1,
            max_replica_count=3,
            accelerator_type=None,
            accelerator_count=0
        )
        
        return endpoint, deployed_model
    
    def predict_online(self, endpoint, instances):
        """Make online predictions via Vertex AI endpoint"""
        return endpoint.predict(instances=instances)

# Example usage and testing
if __name__ == "__main__":
    # Test local predictor
    predictor = RetentionPredictor()
    
    # Sample employee data
    sample_employee = {
        'emp_id': 'EMP001',
        'job_level': 2,
        'years_at_company': 3.5,
        'years_in_position': 1.2,
        'performance_score': 4.2,
        'salary_percentile': 0.65,
        'promotion_eligible': 1,
        'skill_diversity': 8,
        'last_evaluation_score': 4.0
    }
    
    predictions = predictor.predict([sample_employee])
    print(json.dumps(predictions, indent=2))