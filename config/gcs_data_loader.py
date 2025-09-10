"""
Google Cloud Storage Data Loader for Mock Data
"""

import os
import pandas as pd
from google.cloud import storage
import io
from typing import Dict, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GCSDataLoader:
    """Load CSV data from Google Cloud Storage bucket with simple date partitioning"""
    
    def __init__(self, bucket_name: str = "th-ai-talent-data", project_id: str = "th-ai-talent-wow", date_partition: str = "2025-09-05"):
        """
        Initialize GCS data loader
        
        Args:
            bucket_name: Name of GCS bucket containing the data
            project_id: GCP project ID
            date_partition: Date partition folder (e.g., '2025-09-05')
        """
        self.bucket_name = bucket_name
        self.project_id = project_id
        self.date_partition = date_partition
        
        try:
            self.client = storage.Client(project=project_id)
            self.bucket = self.client.bucket(bucket_name)
        except Exception as e:
            logger.warning(f"Failed to initialize GCS client: {str(e)}")
            logger.warning("GCS functionality will not be available")
            self.client = None
            self.bucket = None
    
    def get_file_path(self, file_name: str) -> str:
        """
        Get the full file path including date partition
        
        Args:
            file_name: Name of the file (e.g., 'employees.csv')
            
        Returns:
            str: Full path with date partition (e.g., '2025-09-05/employees.csv')
        """
        return f"{self.date_partition}/{file_name}"
        
    def read_csv_from_gcs(self, file_name: str) -> pd.DataFrame:
        """
        Read a CSV file from GCS bucket with date partitioning
        
        Args:
            file_name: Name of the CSV file (e.g., 'employees.csv')
            
        Returns:
            pandas.DataFrame: The loaded dataframe
            
        Raises:
            FileNotFoundError: If file doesn't exist in bucket
            Exception: For other GCS or parsing errors
        """
        if self.client is None or self.bucket is None:
            raise Exception("GCS client not initialized. Check credentials and project access.")
        
        try:
            # Get full path with date partition
            full_path = self.get_file_path(file_name)
            blob = self.bucket.blob(full_path)
            
            if not blob.exists():
                raise FileNotFoundError(f"File {full_path} not found in bucket {self.bucket_name}")
            
            # Download as text and read with pandas
            csv_content = blob.download_as_text()
            df = pd.read_csv(io.StringIO(csv_content))
            
            logger.info(f"Successfully loaded {full_path} from GCS: {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Error loading {file_name} from GCS: {str(e)}")
            raise
    
    def get_all_data(self) -> Dict[str, pd.DataFrame]:
        """
        Load all mock data files from GCS
        
        Returns:
            Dict[str, pd.DataFrame]: Dictionary with file names as keys and dataframes as values
        """
        data_files = {
            'employees': 'employees.csv',
            'manager_log': 'managerLog.csv', 
            'employee_skill': 'employeeSkill.csv',
            'skills': 'skills.csv',
            'positions': 'positions.csv',
            'departments': 'departments.csv',
            'position_skill': 'positionSkill.csv',
            'employee_movement': 'employeeMovement.csv',
            'engagement': 'engagement.csv',
            'event': 'event.csv',
            'leave': 'leave.csv',
            'evaluation_record': 'evaluationRecord.csv',
            'clock_in_out': 'clockInOut.csv'
        }
        
        loaded_data = {}
        
        for key, filename in data_files.items():
            try:
                loaded_data[key] = self.read_csv_from_gcs(filename)
            except Exception as e:
                logger.warning(f"Failed to load {filename}: {str(e)}")
                continue
        
        logger.info(f"Successfully loaded {len(loaded_data)} data files from GCS")
        return loaded_data


def get_gcs_config_paths(bucket_name: str = "th-ai-talent-data", date_partition: str = "2025-09-05") -> Dict[str, str]:
    """
    Get GCS paths for all data files in config format with date partitioning
    
    Args:
        bucket_name: Name of GCS bucket
        date_partition: Date partition (e.g., '2025-09-05')
        
    Returns:
        Dict[str, str]: Dictionary with config variable names as keys and GCS paths as values
    """
    
    return {
        'EMPLOYEE_DATA': f'gs://{bucket_name}/{date_partition}/employees.csv',
        'MANAGER_LOG_DATA': f'gs://{bucket_name}/{date_partition}/managerLog.csv',
        'EMPLOYEE_SKILL_DATA': f'gs://{bucket_name}/{date_partition}/employeeSkill.csv',
        'SKILL_DATA': f'gs://{bucket_name}/{date_partition}/skills.csv',
        'POSITION_DATA': f'gs://{bucket_name}/{date_partition}/positions.csv',
        'DEPARTMENT_DATA': f'gs://{bucket_name}/{date_partition}/departments.csv',
        'POSITION_SKILL_DATA': f'gs://{bucket_name}/{date_partition}/positionSkill.csv',
        'EMPLOYEE_MOVEMENT_DATA': f'gs://{bucket_name}/{date_partition}/employeeMovement.csv',
        'ENGAGEMENT_DATA': f'gs://{bucket_name}/{date_partition}/engagement.csv',
        'EVENT_DATA': f'gs://{bucket_name}/{date_partition}/event.csv',
        'LEAVE_DATA': f'gs://{bucket_name}/{date_partition}/leave.csv',
        'EVALUATION_RECORD_DATA': f'gs://{bucket_name}/{date_partition}/evaluationRecord.csv',
        'CLOCK_IN_OUT_DATA': f'gs://{bucket_name}/{date_partition}/clockInOut.csv'
    }


def read_csv_from_gcs_path(gcs_path: str) -> pd.DataFrame:
    """
    Read a CSV file directly from a GCS path
    
    Args:
        gcs_path: Full GCS path (e.g., 'gs://bucket-name/file.csv')
        
    Returns:
        pandas.DataFrame: The loaded dataframe
    """
    if not gcs_path.startswith('gs://'):
        # If it's a local path, read normally
        return pd.read_csv(gcs_path)
    
    # Parse GCS path
    path_parts = gcs_path.replace('gs://', '').split('/', 1)
    bucket_name = path_parts[0]
    file_path = path_parts[1] if len(path_parts) > 1 else ''
    
    # Use GCS loader
    loader = GCSDataLoader(bucket_name)
    return loader.read_csv_from_gcs(file_path)


# Convenience function for backward compatibility
def load_data_from_gcs(use_gcs: bool = True) -> Dict[str, pd.DataFrame]:
    """
    Load data either from GCS or local files based on flag
    
    Args:
        use_gcs: If True, load from GCS. If False, use local mock_data files
        
    Returns:
        Dict[str, pd.DataFrame]: Loaded data
    """
    if use_gcs:
        loader = GCSDataLoader()
        return loader.get_all_data()
    else:
        # Load from local files (original behavior)
        from config import config
        data = {}
        
        try:
            data['employees'] = pd.read_csv(config.EMPLOYEE_DATA)
            data['manager_log'] = pd.read_csv(config.MANAGER_LOG_DATA)
            data['employee_skill'] = pd.read_csv(config.EMPLOYEE_SKILL_DATA)
            data['skills'] = pd.read_csv(config.SKILL_DATA)
            data['positions'] = pd.read_csv(config.POSITION_DATA)
            data['departments'] = pd.read_csv(config.DEPARTMENT_DATA)
            data['position_skill'] = pd.read_csv(config.POSITION_SKILL_DATA)
            data['employee_movement'] = pd.read_csv(config.EMPLOYEE_MOVEMENT_DATA)
            data['engagement'] = pd.read_csv(config.ENGAGEMENT_DATA)
            data['event'] = pd.read_csv(config.EVENT_DATA)
            data['leave'] = pd.read_csv(config.LEAVE_DATA)
            data['evaluation_record'] = pd.read_csv(config.EVALUATION_RECORD_DATA)
            data['clock_in_out'] = pd.read_csv(config.CLOCK_IN_OUT_DATA)
        except Exception as e:
            logger.error(f"Error loading local data: {str(e)}")
            raise
            
        return data


if __name__ == "__main__":
    # Test the GCS data loader
    print("Testing GCS Data Loader...")
    
    try:
        loader = GCSDataLoader()
        
        # Test loading a single file
        employees_df = loader.read_csv_from_gcs('employees.csv')
        print(f"Employees data shape: {employees_df.shape}")
        print(f"Employees columns: {list(employees_df.columns)}")
        
        # Test loading all data
        all_data = loader.get_all_data()
        print(f"\nLoaded {len(all_data)} datasets:")
        for key, df in all_data.items():
            print(f"  {key}: {df.shape}")
        
        # Test GCS paths
        gcs_paths = get_gcs_config_paths()
        print(f"\nGCS config paths:")
        for key, path in gcs_paths.items():
            print(f"  {key} = '{path}'")
            
    except Exception as e:
        print(f"Error testing GCS loader: {str(e)}")