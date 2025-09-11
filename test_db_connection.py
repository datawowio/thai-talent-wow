#!/usr/bin/env python3
"""
Test script for database connection and saving results
"""

import os
import json
import pandas as pd
from api.database import db

def test_connection():
    """Test database connection"""
    print("Testing database connection...")
    
    # Set environment variables for testing (you should set these properly)
    # os.environ['DB_PASSWORD'] = 'your_password_here'
    
    if db.connect():
        print("✓ Database connection successful")
        
        # Test if termination_results table exists
        try:
            db.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'termination_results'
                );
            """)
            exists = db.cursor.fetchone()['exists']
            if exists:
                print("✓ termination_results table exists")
            else:
                print("✗ termination_results table does not exist")
        except Exception as e:
            print(f"✗ Error checking table: {e}")
        
        db.disconnect()
    else:
        print("✗ Database connection failed")
        print("Make sure to set DB_PASSWORD environment variable")

def test_save_results():
    """Test saving results to database"""
    print("\nTesting save functionality...")
    
    # Check if output files exist
    termination_file = 'output/termination_result.json'
    predictions_file = 'output/model/model_result.parquet'
    
    if os.path.exists(termination_file):
        print(f"✓ Found {termination_file}")
        
        # Load termination data
        with open(termination_file, 'r') as f:
            termination_data = json.load(f)
        
        # Test saving to database
        if db.connect():
            if db.save_termination_results("test_job_123", termination_data):
                print("✓ Successfully saved termination results to database")
            else:
                print("✗ Failed to save termination results")
            
            # Test employee predictions if file exists
            if os.path.exists(predictions_file):
                print(f"✓ Found {predictions_file}")
                predictions_df = pd.read_parquet(predictions_file)
                
                if db.save_employee_predictions("test_job_123", predictions_df):
                    print("✓ Successfully processed employee predictions")
                else:
                    print("✗ Failed to process employee predictions")
            else:
                print(f"✗ {predictions_file} not found")
            
            db.disconnect()
        else:
            print("✗ Could not connect to database for saving")
    else:
        print(f"✗ {termination_file} not found")
        print("Run the ML pipeline first to generate output files")

if __name__ == "__main__":
    print("=" * 50)
    print("Database Integration Test")
    print("=" * 50)
    
    test_connection()
    test_save_results()
    
    print("\n" + "=" * 50)
    print("Test Complete")
    print("=" * 50)