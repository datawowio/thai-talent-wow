### FOR COMPANY-RELATED MANUAL CHANGE
COMPANY_POSTAL_CODE = '10110'

### TABLE PATHS
EMPLOYEE_DATA = 'mock_data/employees.csv'
MANAGER_LOG_DATA = 'mock_data/managerLog.csv'
EMPLOYEE_SKILL_DATA= 'mock_data/employeeSkill.csv'
EMPLOYEE_POSITION_DATA = 'mock_data/employeePosition.csv'
SKILL_DATA = 'mock_data/skills.csv'
POSITION_DATA = 'mock_data/positions.csv'
DEPARTMENT_DATA = 'mock_data/departments.csv'
POSITION_SKILL_DATA = 'mock_data/positionSkill.csv'
EMPLOYEE_MOVEMENT_DATA = 'mock_data/employeeMovement.csv'
ENGAGEMENT_DATA = 'mock_data/engagement.csv'
EVENT_DATA = 'mock_data/event.csv'
LEAVE_DATA = 'mock_data/leave.csv'
EVALUATION_RECORD_DATA = 'mock_data/evaluationRecord.csv'
CLOCK_IN_OUT_DATA = 'mock_data/clockInOut.csv'

### FOR PREDICTIVE RETENTION MODEL
FEATURE_ENGINEERED_PATH = 'output/feature_engineered_data.csv'

RESULT_DIR = 'output'
MODEL_PATH = 'output/model.pkl'
MODEL_CONFIG_PATH = 'output/model_config.json'
MODEL_INTERPRETATION_PATH = 'output/model_interpretation.pkl'
MODEL_RESULTS_PATH = 'output/model_result.parquet'
# FEATURE_IMPORTANCE_PATH = 'output/feature_importance.parquet'

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

TERMINATION_ANALYSIS_OUTPUT = 'output/termination_result.json'

### FOR SKILL GAP ANALYSIS
EMPLOYEE_SKILL_GAP_ANALYSIS_OUTPUT = 'output/employee_skill_gap_result.json'
DEPARTMENT_SKILL_GAP_ANALYSIS_OUTPUT = 'output/department_skill_gap_result.json'

### FOR PROMOTION ANALYSIS
PROMOTION_ANALYSIS_OUTPUT = 'output/promotion_analysis_results.json'
