#!/usr/bin/env python3
import sys
import os
print("TEST: Script starting successfully")
print(f"TEST: Python version: {sys.version}")
print(f"TEST: Current working directory: {os.getcwd()}")
print(f"TEST: Python path: {sys.path}")

# Test if the main script can be imported
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'predictive_retention'))
    print("TEST: Attempting to import main...")
    from predictive_retention.main import main
    print("TEST: Import successful!")
except Exception as e:
    print(f"TEST: Import failed with error: {e}")
    print(f"TEST: Error type: {type(e)}")

print("TEST: Script completed successfully")