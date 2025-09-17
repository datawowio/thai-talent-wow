#!/usr/bin/env python3
"""
Test script for Vertex AI deployed model
Run this from your Compute Engine instance after deployment
"""

import json
import argparse
from google.cloud import aiplatform

def test_endpoint(project_id, region="asia-southeast1", endpoint_id=None):
    """
    Test the deployed Vertex AI endpoint
    """
    # Initialize Vertex AI
    aiplatform.init(project=project_id, location=region)
    
    # Load deployment info if endpoint_id not provided
    if not endpoint_id:
        try:
            with open("vertex_deployment_info.json", 'r') as f:
                deployment_info = json.load(f)
                endpoint_id = deployment_info['endpoint_id']
                print(f"Using endpoint from deployment info: {deployment_info['endpoint_name']}")
        except FileNotFoundError:
            print("ERROR: No endpoint_id provided and vertex_deployment_info.json not found")
            print("Please provide --endpoint-id or run deploy_from_compute.py first")
            return
    
    # Get endpoint
    endpoint = aiplatform.Endpoint(endpoint_id)
    
    # Test data - multiple employees with different risk profiles
    test_instances = [
        {
            "emp_id": "TEST001",
            "job_level": 2,
            "years_at_company": 0.5,  # New employee
            "years_in_position": 0.5,
            "performance_score": 3.0,  # Low performance
            "salary_percentile": 0.3,  # Low salary
            "promotion_eligible": 0,
            "skill_diversity": 3,
            "last_evaluation_score": 2.8,
            "has_mentor": 0,
            "training_hours_per_year": 5
        },
        {
            "emp_id": "TEST002", 
            "job_level": 3,
            "years_at_company": 5.0,  # Experienced
            "years_in_position": 2.0,
            "performance_score": 4.5,  # High performance
            "salary_percentile": 0.75,  # Good salary
            "promotion_eligible": 1,
            "skill_diversity": 10,
            "last_evaluation_score": 4.3,
            "has_mentor": 1,
            "training_hours_per_year": 40
        },
        {
            "emp_id": "TEST003",
            "job_level": 1,
            "years_at_company": 2.0,
            "years_in_position": 2.0,  # No growth
            "performance_score": 3.5,
            "salary_percentile": 0.4,
            "promotion_eligible": 0,
            "skill_diversity": 5,
            "last_evaluation_score": 3.2,
            "has_mentor": 0,
            "training_hours_per_year": 10
        }
    ]
    
    print("\n=== Testing Vertex AI Endpoint ===\n")
    print(f"Endpoint: {endpoint.display_name}")
    print(f"Region: {region}")
    print(f"Project: {project_id}\n")
    
    try:
        # Make predictions
        print("Sending test instances...")
        response = endpoint.predict(instances=test_instances)
        
        print("\n=== Prediction Results ===\n")
        
        predictions = response.predictions
        if isinstance(predictions, dict) and 'predictions' in predictions:
            predictions = predictions['predictions']
        
        for i, (instance, prediction) in enumerate(zip(test_instances, predictions)):
            print(f"Employee {i+1}: {instance['emp_id']}")
            print(f"  Profile:")
            print(f"    - Years at company: {instance['years_at_company']}")
            print(f"    - Performance score: {instance['performance_score']}")
            print(f"    - Salary percentile: {instance['salary_percentile']}")
            print(f"  Prediction:")
            print(f"    - Termination probability: {prediction.get('termination_probability', 'N/A'):.2%}")
            print(f"    - Risk level: {prediction.get('risk_level', 'N/A')}")
            print(f"    - Predicted to leave: {prediction.get('predicted_termination', 'N/A')}")
            print()
        
        print("✅ Endpoint test successful!")
        
        # Show endpoint details for future use
        print("\n=== Endpoint Details for Integration ===")
        print(f"Endpoint ID: {endpoint.resource_name}")
        print(f"REST API URL: https://{region}-aiplatform.googleapis.com/v1/{endpoint.resource_name}:predict")
        print("\nTo use in your application:")
        print("1. Install: pip install google-cloud-aiplatform")
        print("2. Code example:")
        print(f'''
from google.cloud import aiplatform
aiplatform.init(project="{project_id}", location="{region}")
endpoint = aiplatform.Endpoint("{endpoint.resource_name}")
predictions = endpoint.predict(instances=[{{"emp_id": "123", "job_level": 2, ...}}])
''')
        
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")
        print("\nTroubleshooting:")
        print("1. Check if the model is fully deployed (may take a few minutes)")
        print("2. Verify your authentication: gcloud auth application-default login")
        print("3. Check if all required features are provided in test instances")

def main():
    parser = argparse.ArgumentParser(description='Test Vertex AI endpoint')
    parser.add_argument('--project-id', required=True, help='GCP Project ID')
    parser.add_argument('--region', default='asia-southeast1', help='Vertex AI region')
    parser.add_argument('--endpoint-id', help='Endpoint ID (reads from vertex_deployment_info.json if not provided)')
    
    args = parser.parse_args()
    
    test_endpoint(
        project_id=args.project_id,
        region=args.region,
        endpoint_id=args.endpoint_id
    )

if __name__ == "__main__":
    main()