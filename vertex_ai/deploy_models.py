#!/usr/bin/env python3
"""
Deploy models to Vertex AI for real-time predictions
"""

import os
import sys
import json
import argparse
from google.cloud import aiplatform

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vertex_ai.retention_predictor import VertexAIRetentionModel
from vertex_ai.skill_predictor import VertexAISkillModel

def deploy_retention_model(project_id, region="asia-southeast1"):
    """Deploy retention prediction model to Vertex AI"""
    print("🚀 Deploying Retention Prediction Model...")
    
    vertex_model = VertexAIRetentionModel(project_id, region)
    
    # Create model
    model = vertex_model.create_model("retention-predictor-v1")
    print(f"✅ Model created: {model.display_name}")
    
    # Deploy to endpoint
    endpoint, deployed_model = vertex_model.deploy_model(
        model, "retention-endpoint-v1"
    )
    print(f"✅ Model deployed to endpoint: {endpoint.display_name}")
    
    return {
        "model_name": model.display_name,
        "model_id": model.name,
        "endpoint_name": endpoint.display_name,
        "endpoint_id": endpoint.name
    }

def deploy_skill_models(project_id, region="asia-southeast1"):
    """Deploy skill analysis models to Vertex AI"""
    print("🚀 Deploying Skill Analysis Models...")
    
    vertex_model = VertexAISkillModel(project_id, region)
    results = {}
    
    # Deploy skill gap model
    skill_model = vertex_model.create_skill_gap_model("skill-gap-predictor-v1")
    print(f"✅ Skill gap model created: {skill_model.display_name}")
    
    skill_endpoint = aiplatform.Endpoint.create(
        display_name="skill-gap-endpoint-v1",
        description="Real-time skill gap analysis"
    )
    
    skill_model.deploy(
        endpoint=skill_endpoint,
        deployed_model_display_name="skill-gap-v1",
        machine_type="n1-standard-2",
        min_replica_count=1,
        max_replica_count=2
    )
    
    results["skill_gap"] = {
        "model_name": skill_model.display_name,
        "model_id": skill_model.name,
        "endpoint_name": skill_endpoint.display_name,
        "endpoint_id": skill_endpoint.name
    }
    
    # Deploy promotion model
    promotion_model = vertex_model.create_promotion_model("promotion-predictor-v1")
    print(f"✅ Promotion model created: {promotion_model.display_name}")
    
    promotion_endpoint = aiplatform.Endpoint.create(
        display_name="promotion-endpoint-v1",
        description="Real-time promotion readiness analysis"
    )
    
    promotion_model.deploy(
        endpoint=promotion_endpoint,
        deployed_model_display_name="promotion-v1",
        machine_type="n1-standard-2", 
        min_replica_count=1,
        max_replica_count=2
    )
    
    results["promotion"] = {
        "model_name": promotion_model.display_name,
        "model_id": promotion_model.name,
        "endpoint_name": promotion_endpoint.display_name,
        "endpoint_id": promotion_endpoint.name
    }
    
    return results

def test_endpoints(project_id, region="asia-southeast1"):
    """Test deployed endpoints with sample data"""
    print("🧪 Testing deployed endpoints...")
    
    aiplatform.init(project=project_id, location=region)
    
    # Sample test data
    test_employee = {
        'employee_id': 'EMP001',
        'job_level': 2,
        'years_at_company': 3.5,
        'performance_score': 4.2,
        'salary_percentile': 0.65
    }
    
    try:
        # Test retention endpoint
        retention_endpoints = aiplatform.Endpoint.list(
            filter='display_name="retention-endpoint-v1"'
        )
        if retention_endpoints:
            endpoint = retention_endpoints[0]
            prediction = endpoint.predict(instances=[test_employee])
            print(f"✅ Retention prediction: {prediction}")
    
    except Exception as e:
        print(f"❌ Retention test failed: {e}")
    
    try:
        # Test skill gap endpoint
        skill_endpoints = aiplatform.Endpoint.list(
            filter='display_name="skill-gap-endpoint-v1"'
        )
        if skill_endpoints:
            endpoint = skill_endpoints[0]
            prediction = endpoint.predict(instances=[{'employee_id': 'EMP001'}])
            print(f"✅ Skill gap prediction: {prediction}")
    
    except Exception as e:
        print(f"❌ Skill gap test failed: {e}")

def save_deployment_info(deployment_info, output_file="deployment_info.json"):
    """Save deployment information for later use"""
    with open(output_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    print(f"💾 Deployment info saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Deploy models to Vertex AI')
    parser.add_argument('--project-id', required=True, help='GCP Project ID')
    parser.add_argument('--region', default='asia-southeast1', help='GCP Region')
    parser.add_argument('--models', nargs='+', 
                       choices=['retention', 'skill', 'all'], 
                       default=['all'], 
                       help='Models to deploy')
    parser.add_argument('--test', action='store_true', 
                       help='Test endpoints after deployment')
    
    args = parser.parse_args()
    
    deployment_results = {}
    
    if 'retention' in args.models or 'all' in args.models:
        deployment_results['retention'] = deploy_retention_model(
            args.project_id, args.region
        )
    
    if 'skill' in args.models or 'all' in args.models:
        deployment_results['skill'] = deploy_skill_models(
            args.project_id, args.region
        )
    
    # Save deployment information
    save_deployment_info(deployment_results)
    
    if args.test:
        test_endpoints(args.project_id, args.region)
    
    print("🎉 Deployment completed!")
    print("\n📋 Summary:")
    for model_type, info in deployment_results.items():
        if isinstance(info, dict):
            if 'model_name' in info:  # Single model (retention)
                print(f"  {model_type}: {info['endpoint_name']}")
            else:  # Multiple models (skill)
                for sub_type, sub_info in info.items():
                    print(f"  {model_type}_{sub_type}: {sub_info['endpoint_name']}")

if __name__ == "__main__":
    main()