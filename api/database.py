"""
Database connection module for PostgreSQL
"""

import os
import json
import logging
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd
import subprocess

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Manages PostgreSQL database connections and operations"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
        
    def _get_secret(self, secret_name: str) -> str:
        """Get secret from GCP Secret Manager"""
        try:
            result = subprocess.run([
                'gcloud', 'secrets', 'versions', 'access', 'latest',
                '--secret', secret_name
            ], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get secret {secret_name}: {e}")
            return None

    def connect(self):
        """Establish database connection"""
        try:
            # Get database configuration from environment or GCP Secret Manager
            db_config = {
                'host': os.getenv('DB_HOST') or self._get_secret('db-host'),
                'port': int(os.getenv('DB_PORT', 5432)),
                'database': os.getenv('DB_NAME') or self._get_secret('db-name'),
                'user': os.getenv('DB_USERNAME') or self._get_secret('db-username'),
                'password': os.getenv('DB_PASSWORD') or self._get_secret('db-password')
            }
            
            # Check if password is provided
            if not db_config['password']:
                logger.warning("Database password not available from environment or Secret Manager")
                return False
            
            self.connection = psycopg2.connect(**db_config)
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            logger.info("Database connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Database connection closed")
    
    def save_termination_results(self, job_id: str, termination_data: Dict[str, Any]) -> bool:
        """
        Save termination results to the termination_results table
        
        Args:
            job_id: The job ID from the API
            termination_data: The termination result JSON data
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            # Prepare the INSERT query
            query = """
                INSERT INTO termination_results (
                    overall_summary,
                    department_proportion,
                    job_level_proportion,
                    department_distribution,
                    job_level_distribution,
                    top_quitting_reason,
                    reason_by_employee,
                    reason_by_department,
                    reason_by_job_level,
                    created_at,
                    updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id;
            """
            
            # Add job_id to overall_summary
            if 'overall_summary' in termination_data:
                termination_data['overall_summary']['job_id'] = job_id
            
            # Execute the query
            self.cursor.execute(query, (
                Json(termination_data.get('overall_summary', {})),
                Json(termination_data.get('department_proportion', [])),
                Json(termination_data.get('job_level_proportion', [])),
                Json(termination_data.get('department_distribution', [])),
                Json(termination_data.get('job_level_distribution', [])),
                Json(termination_data.get('top_quitting_reason', [])),
                Json(termination_data.get('reason_by_employee', [])),
                Json(termination_data.get('reason_by_department', [])),
                Json(termination_data.get('reason_by_job_level', [])),
                datetime.now(),
                datetime.now()
            ))
            
            # Get the inserted record ID
            result = self.cursor.fetchone()
            record_id = result['id'] if result else None
            
            # Commit the transaction
            self.connection.commit()
            
            logger.info(f"Termination results saved successfully with ID: {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save termination results: {str(e)}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def save_employee_predictions(self, job_id: str, predictions_df: pd.DataFrame) -> bool:
        """
        Save individual employee predictions (if a table exists for them)
        This is a placeholder for future use when the backend adds an employee predictions table
        
        Args:
            job_id: The job ID from the API
            predictions_df: DataFrame with emp_id, termination_probability, predicted_termination
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if employee_retention_predictions table exists
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'employee_retention_predictions'
                );
            """)
            
            table_exists = self.cursor.fetchone()['exists']
            
            if not table_exists:
                logger.info("employee_retention_predictions table does not exist yet")
                return True  # Not an error, just skip
            
            # If table exists, insert predictions
            for _, row in predictions_df.iterrows():
                query = """
                    INSERT INTO employee_retention_predictions (
                        employee_id,
                        termination_probability,
                        predicted_termination,
                        prediction_date,
                        job_id,
                        created_at,
                        updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s
                    );
                """
                
                self.cursor.execute(query, (
                    row['emp_id'],
                    float(row['termination_probability']),
                    bool(row['predicted_termination']),
                    datetime.now(),
                    job_id,
                    datetime.now(),
                    datetime.now()
                ))
            
            self.connection.commit()
            logger.info(f"Saved {len(predictions_df)} employee predictions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save employee predictions: {str(e)}")
            if self.connection:
                self.connection.rollback()
            return False

    def save_skill_management_results(self, job_id: str) -> bool:
        """
        Save all skill management pipeline results to database tables
        Following the same pattern as save_termination_results

        Args:
            job_id: The job ID from the API

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False

            all_success = True

            # 1. Save Employee Skill Results
            employee_skill_file = '/app/output/employee_skill_gap_result.json'
            if os.path.exists(employee_skill_file):
                try:
                    with open(employee_skill_file, 'r') as f:
                        employee_skill_data = json.load(f)

                    # Clear existing data first
                    self.cursor.execute("DELETE FROM employee_skill_results")

                    for emp_data in employee_skill_data:
                        query = """
                            INSERT INTO employee_skill_results (
                                employee_id,
                                current_position,
                                next_position,
                                employee_skills,
                                current_missing_skills,
                                peer_missing_skills,
                                next_missing_skills,
                                created_at,
                                updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """

                        self.cursor.execute(query, (
                            emp_data['employee_id'],
                            emp_data.get('current_position'),
                            emp_data.get('next_position'),
                            Json(emp_data.get('employee_skills', [])),
                            Json(emp_data.get('current_missing_skills', [])),
                            Json(emp_data.get('peer_missing_skills', [])),
                            Json(emp_data.get('next_missing_skills', [])),
                            datetime.now(),
                            datetime.now()
                        ))

                    logger.info(f"Saved {len(employee_skill_data)} employee skill results")
                except Exception as e:
                    logger.error(f"Failed to save employee skill results: {str(e)}")
                    all_success = False

            # 2. Save Department Skill Results
            department_skill_file = '/app/output/department_skill_gap_result.json'
            if os.path.exists(department_skill_file):
                try:
                    with open(department_skill_file, 'r') as f:
                        department_skill_data = json.load(f)

                    # Clear existing data first
                    self.cursor.execute("DELETE FROM department_skill_results")

                    for dept_data in department_skill_data:
                        # Check if performance_trends column exists (it was renamed from performance_trend)
                        query = """
                            INSERT INTO department_skill_results (
                                department_id,
                                department_name,
                                total_employee,
                                common_existing_skills,
                                department_missing_skills,
                                low_score_skills,
                                performance_trends,
                                created_at,
                                updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """

                        self.cursor.execute(query, (
                            int(dept_data['department_id']),
                            dept_data['department_name'],
                            dept_data['total_employee'],
                            Json(dept_data.get('common_existing_skills', [])),
                            Json(dept_data.get('department_missing_skills', [])),
                            Json(dept_data.get('low_score_skills', [])),
                            Json(dept_data.get('performance_trends', [])),
                            datetime.now(),
                            datetime.now()
                        ))

                    logger.info(f"Saved {len(department_skill_data)} department skill results")
                except Exception as e:
                    logger.error(f"Failed to save department skill results: {str(e)}")
                    all_success = False

            # 3. Save Promotion Results
            promotion_file = '/app/output/promotion_analysis_results.json'
            if os.path.exists(promotion_file):
                try:
                    with open(promotion_file, 'r') as f:
                        promotion_data = json.load(f)

                    # Clear existing data first
                    self.cursor.execute("DELETE FROM promotion_results")

                    # Save each employee type category
                    for emp_type_data in promotion_data.get('employee_data', []):
                        query = """
                            INSERT INTO promotion_results (
                                employee_type,
                                total_employee,
                                employee_ids,
                                avg_promotion_time_by_department,
                                avg_promotion_time_by_job_level,
                                department_promotion_rate,
                                created_at,
                                updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """

                        self.cursor.execute(query, (
                            emp_type_data['employee_type'],
                            emp_type_data['total_employee'],
                            Json(emp_type_data.get('employee_ids', [])),
                            Json(promotion_data.get('avg_promotion_time_by_department', [])),
                            Json(promotion_data.get('avg_promotion_time_by_job_level', [])),
                            Json(promotion_data.get('department_promotion_rate', [])),
                            datetime.now(),
                            datetime.now()
                        ))

                    logger.info(f"Saved promotion analysis results")
                except Exception as e:
                    logger.error(f"Failed to save promotion results: {str(e)}")
                    all_success = False

            # 4. Save Rotation Results
            rotation_file = '/app/output/rotation_skill_gap_result.json'
            if os.path.exists(rotation_file):
                try:
                    with open(rotation_file, 'r') as f:
                        rotation_data = json.load(f)

                    # Clear existing data first
                    self.cursor.execute("DELETE FROM rotation_results")

                    for rotation in rotation_data:
                        query = """
                            INSERT INTO rotation_results (
                                employee_id,
                                from_position,
                                to_position,
                                skill_gaps,
                                skill_overlaps,
                                rotation_score,
                                created_at,
                                updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """

                        self.cursor.execute(query, (
                            rotation.get('employee_id'),
                            rotation.get('from_position'),
                            rotation.get('to_position'),
                            Json(rotation.get('skill_gaps', [])),
                            Json(rotation.get('skill_overlaps', [])),
                            float(rotation.get('rotation_score', 0.0)),
                            datetime.now(),
                            datetime.now()
                        ))

                    logger.info(f"Saved {len(rotation_data)} rotation results")
                except Exception as e:
                    logger.error(f"Failed to save rotation results: {str(e)}")
                    all_success = False

            # Commit all changes if successful
            if all_success:
                self.connection.commit()
                logger.info("All skill management results saved successfully")
            else:
                self.connection.rollback()
                logger.warning("Some skill management results failed to save")

            return all_success

        except Exception as e:
            logger.error(f"Failed to save skill management results: {str(e)}")
            if self.connection:
                self.connection.rollback()
            return False

# Singleton instance
db = DatabaseConnection()