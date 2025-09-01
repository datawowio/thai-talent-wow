#!/usr/bin/env python3
"""
Simple deployment script for Vertex AI models
"""

import os
import sys
from google.cloud import aiplatform

# Configuration
PROJECT_ID = "th-ai-talent-wow"
REGION = "asia-southeast1"

def init_vertex_ai():
    """Initialize Vertex AI"""
    print(f"🚀 Initializing Vertex AI in project: {PROJECT_ID}, region: {REGION}")
    aiplatform.init(project=PROJECT_ID, location=REGION)
    print("✅ Vertex AI initialized")

def create_demo_model():
    """Create a demo model in Vertex AI"""
    print("\n📦 Creating demo model in Vertex AI...")
    
    try:
        # Create a simple model
        model = aiplatform.Model.upload(
            display_name="talent-analytics-demo",
            description="Demo model for talent analytics",
            serving_container_image_uri="gcr.io/cloud-aiplatform/prediction/sklearn-cpu.0-24:latest",
            artifact_uri="gs://cloud-samples-data/ai-platform/sklearn/model.pkl",  # Sample model
        )
        
        print(f"✅ Model created: {model.display_name}")
        print(f"   Model ID: {model.resource_name}")
        
        return model
    
    except Exception as e:
        print(f"⚠️  Note: {e}")
        print("   This is expected if you haven't trained a model yet.")
        print("   For now, we'll deploy the API without Vertex AI models.")
        return None

def create_endpoint(model):
    """Deploy model to endpoint"""
    if not model:
        print("⚠️  Skipping endpoint creation - no model available")
        return None
    
    print("\n🎯 Creating endpoint...")
    
    try:
        # Create endpoint
        endpoint = aiplatform.Endpoint.create(
            display_name="talent-analytics-endpoint",
            description="Endpoint for talent analytics predictions"
        )
        
        print(f"✅ Endpoint created: {endpoint.display_name}")
        
        # Deploy model to endpoint
        print("📤 Deploying model to endpoint...")
        endpoint.deploy(
            model=model,
            deployed_model_display_name="talent-analytics-v1",
            machine_type="n1-standard-2",
            min_replica_count=1,
            max_replica_count=2
        )
        
        print(f"✅ Model deployed to endpoint!")
        print(f"   Endpoint ID: {endpoint.resource_name}")
        
        return endpoint
    
    except Exception as e:
        print(f"❌ Error creating endpoint: {e}")
        return None

def main():
    print("=" * 60)
    print("🎯 VERTEX AI DEPLOYMENT FOR TALENT ANALYTICS")
    print("=" * 60)
    
    # Initialize Vertex AI
    init_vertex_ai()
    
    # Try to create and deploy model
    model = create_demo_model()
    endpoint = create_endpoint(model)
    
    print("\n" + "=" * 60)
    
    if endpoint:
        print("✅ DEPLOYMENT SUCCESSFUL!")
        print(f"   Endpoint: {endpoint.resource_name}")
        print("\n💡 You can now use this endpoint for predictions")
    else:
        print("⚠️  PARTIAL DEPLOYMENT")
        print("   Vertex AI setup is ready, but no models deployed yet.")
        print("   You can still deploy the API to Cloud Run!")
    
    print("\n🚀 Next step: Deploy API to Cloud Run")
    print("   Run: ./deploy_to_cloud_run.sh")
    print("=" * 60)

if __name__ == "__main__":
    main()