### TABLE PATHS
EMPLOYEE_DATA = 'mock_data/employees.csv'
MANAGER_LOG_DATA = 'mock_data/managerLog.csv'
EMPLOYEE_SKILL_DATA= 'mock_data/employeeSkill.csv'
EMPLOYEE_POSITION_DATA = 'mock_data/employeePosition.csv'
# SKILL_DATA = 'mock_data/skills.csv'
POSITION_DATA = 'mock_data/positions.csv'
DEPARTMENT_DATA = 'mock_data/departments.csv'
POSITION_SKILL_DATA = 'mock_data/positionSkill.csv'
SALARY_DATA = 'mock_data/salary.csv'
EMPLOYEE_MOVEMENT_DATA = 'mock_data/employeeMovement.csv'
ENGAGEMENT_DATA = 'mock_data/engagement.csv'
LEAVE_DATA = 'mock_data/leave.csv'
EVALUATION_RECORD_DATA = 'mock_data/evaluationRecord.csv'
CLOCK_IN_OUT_DATA = 'mock_data/clockInOut.csv'

FEATURE_ENGINEERED_PATH = 'output/feature_engineered_data.csv'

RESULT_DIR = 'output'
MODEL_PATH = 'output/model.pkl'
MODEL_CONFIG_PATH = 'output/model_config.json'
MODEL_INTERPRETATION_PATH = 'output/model_interpretation.pkl'
MODEL_RESULTS_PATH = 'output/model_result.parquet'
FEATURE_IMPORTANCE_PATH = 'output/feature_importance.parquet'

JOB_LEVEL_MAPPER = {
    0: 'Junior',
    1: 'Mid-level',
    2: 'Senior',
    3: 'Lead',
    4: 'Manager',
    5: 'Director',
    6: 'Vice President',
    7: 'C-Level',
}

### FOR PREDICTIVE RETENTION MODEL
FEARURES_MEANING_MAPPER = {
    'avg_performance_score': 'Average Performance Score',
    'avg_time_to_promotion': 'Time Taking to Promotion',
    'total_working_year_z_department': 'Total Working Years Compared to Department',
    'year_since_last_salary_adjustment': 'Time Since Last Salary Adjustment',
    'salary_compare_market_rate': 'Salary Compared to Market Rate',
    'performance_score_z_job_level': 'Performance Score Compared to Job Level',
    'year_in_current_position': 'Years in Current Position',
    'total_working_year': 'Total Working Years',
    'avg_training_per_year': 'Average Training Times per Year',
    'total_ot_hours_3_months': 'Total Overtime Hours in Last 3 Months',
    'year_with_current_manager': 'Years with Current Manager',
    'total_working_year_z_manager': 'Total Working Years Compared to Manager',
    'avg_activity_per_year': 'Average Activity Times per Year',
    'performance_score_z_manager': 'Performance Score Compared to Manager',
    'total_working_year_z_job_level': 'Total Working Years Compared to Job Level',
    'avg_salary': 'Average Salary',
    'avg_performance_score': 'Average Performance Score',
    'num_training': 'Number of Trainings Attended',
    'num_activity': 'Number of Activities Participated',
    'time_since_last_promotion': 'Time Since Last Promotion',
    'num_skills': 'Number of Skills Acquired',
    'distance_from_home_to_office': 'Distance from Home to Office',
    'total_sick_leave_hours_3_months': 'Total Sick Leave Taken in Last 3 Months',
    'total_vacation_leave_hours_3_months': 'Total Vacation Leave Taken in Last 3 Months',
    'avg_skills_score': 'Average Skills Score',
    'num_skill_gaps': 'Number of Skill Gaps Identified',
    'skill_score_vs_avg_position_score': 'Skill Score Compared to Average Position Score',
    'skill_score_vs_median_position_score': 'Skill Score Compared to Median Position Score',
    'age': 'Age of Employee',
}

TERMINATION_RESULT_JSON_PATH = 'output/termination_result.json'