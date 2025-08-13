import json
import pandas as pd
import joblib
from dateutil.relativedelta import relativedelta
from config import config, feature_mapper

def generate_termination_visualizations(model_config, model_interpretation, model_result):
    """
    Loads model results and metadata to generate termination analysis visualizations.

    Returns:
        dict: A dictionary containing all the analysis results ready for JSON serialization.
    """
    json_result = {}

    # --- 1. Load Data ---
    employee_metadata = pd.read_csv(config.FEATURE_ENGINEERED_PATH)
    employee_metadata['execution_date'] = pd.to_datetime(employee_metadata['execution_date'])
    employee_metadata = employee_metadata.sort_values(['emp_id', 'execution_date']).drop_duplicates('emp_id', keep='last')
    employee_metadata['model_predicted_termination'] = employee_metadata['emp_id'].map(
        model_result.set_index('emp_id')['predicted_termination']
    )
    employee_metadata['model_predicted_termination_probability'] = employee_metadata['emp_id'].map(
        model_result.set_index('emp_id')['termination_probability']
    )

    _employee_position_df = pd.read_csv(config.EMPLOYEE_POSITION_DATA)
    _employee_position_df = _employee_position_df.sort_values(by=['employee_id', 'created_at'], ascending=[True, False]).drop_duplicates(subset=['employee_id'], keep='first')
    _position_df = pd.read_csv(config.POSITION_DATA)
    employee_metadata['job_level_name'] = employee_metadata['job_level'].map(config.JOB_LEVEL_MAPPER)
    employee_metadata['position_id'] = employee_metadata['emp_id'].map(_employee_position_df.set_index('employee_id')['position_id'])
    employee_metadata['job_title'] = employee_metadata['position_id'].map(_position_df.set_index('id')['name'])

    termination_emp = employee_metadata[(employee_metadata['model_predicted_termination'] == True) | (employee_metadata['termination_value'] > 0)]

    features = model_config['features']
    shap_df_list = []
    for emp_id, shap_explanation in model_interpretation.items():
        shap_values = shap_explanation.values
        _temp_df = pd.DataFrame([shap_values], columns=features)
        _temp_df['emp_id'] = emp_id
        shap_df_list.append(_temp_df)

    all_shap_df = pd.concat(shap_df_list, ignore_index=True)
    metadata_columns = ['emp_id', 'job_title', 'job_level_name', 'department_name']
    shap_with_metadata = pd.merge(all_shap_df, employee_metadata[metadata_columns], on='emp_id', how='left')

    # --- 2. Overall Summary ---
    predicted_execution_date = employee_metadata['execution_date'].max() + relativedelta(months=1)
    predicted_end_date = predicted_execution_date + relativedelta(months=3) - relativedelta(days=1)
    json_result['overall_summary'] = {
        'prediction_start_date': predicted_execution_date.strftime('%Y-%m-%d'),
        'prediction_end_date': predicted_end_date.strftime('%Y-%m-%d'),
        'total_employees': len(model_result),
        'total_employees_left': employee_metadata[employee_metadata['termination_value'] > 0].drop_duplicates('emp_id').shape[0],
        'employees_predicted_to_leave': employee_metadata[employee_metadata['model_predicted_termination'] == True].shape[0],
        'average_retention_probability': employee_metadata['model_predicted_termination_probability'].mean()
    }

    # --- 3. Termination Proportions ---
    department_count = termination_emp.groupby('department_name')['termination_value'].count().to_frame('termination_count').reset_index()
    json_result['termination_proportion_by_department'] = department_count.sort_values('termination_count', ascending=False).to_dict(orient='records')

    level_count = termination_emp.groupby('job_level')['termination_value'].count().to_frame('termination_count').reset_index()
    level_count['level_name'] = level_count['job_level'].map(config.JOB_LEVEL_MAPPER)
    json_result['termination_proportion_by_job_level'] = level_count[['level_name', 'termination_count']].sort_values('termination_count', ascending=False).to_dict(orient='records')

    # --- 4. Termination Probability Distribution ---
    prob_dist_dept = employee_metadata.groupby('department_name')['model_predicted_termination_probability'].apply(lambda x: [p for p in x if pd.notna(p)])
    prob_dist_level = employee_metadata.groupby('job_level_name')['model_predicted_termination_probability'].apply(lambda x: [p for p in x if pd.notna(p)])

    json_result['termination_probability_distribution'] = {
        'by_department': [
            {'department_name': dept, 'probabilities': probs} for dept, probs in prob_dist_dept.items()
        ],
        'by_job_level': [
            {'job_level_name': level, 'probabilities': probs} for level, probs in prob_dist_level.items()
        ]
    }
    
    # --- 5. Top Reasons for Quitting ---
    num_features = 5
    mean_importance = (all_shap_df.mean(axis=0, skipna=True).sort_values(ascending=False)).to_frame('impact_value')
    mean_importance = mean_importance.drop('emp_id', errors='ignore').reset_index().rename(columns={'index': 'feature'}).head(num_features)
    total_impact = mean_importance['impact_value'].sum()
    mean_importance['impact_percentage'] = (mean_importance['impact_value'] / total_impact) * 100
    mean_importance['feature_name'] = mean_importance['feature'].map(feature_mapper.FEARURES_MEANING_MAPPER)
    mean_importance['recommendation_action'] = mean_importance['feature'].map(feature_mapper.FEATURES_ACTION_MAPPER)
    json_result['top_reasons_for_quitting'] = mean_importance[['feature_name', 'impact_percentage', 'recommendation_action']].to_dict(orient='records')

    # --- 6. Analysis by Employee, Department, and Job Level ---
    termination_shap_emp = employee_metadata[employee_metadata['model_predicted_termination'] == True].drop_duplicates('emp_id')[['emp_id']]
    termination_shap_emp = shap_with_metadata[shap_with_metadata['emp_id'].isin(termination_shap_emp['emp_id'])]
    termination_shap_emp['predicted_temination_probability'] = termination_shap_emp['emp_id'].map(model_result.set_index('emp_id')['termination_probability'])

    # By Employee
    termination_reason_by_employee = {}
    for emp_id in termination_shap_emp['emp_id'].unique():
        # ... (rest of the employee analysis logic from notebook)
        predicted_termination_probability = termination_shap_emp[termination_shap_emp['emp_id'] == emp_id]['predicted_temination_probability'].values[0]
        _emp_shap_t = termination_shap_emp[termination_shap_emp['emp_id'] == emp_id][features].T.reset_index()
        _emp_shap_t.columns = ['feature', 'impact_value']
        abs_mean_shap_value = _emp_shap_t['impact_value'].abs().mean()
        _emp_shap_t = _emp_shap_t[_emp_shap_t['impact_value'].abs() > abs_mean_shap_value]
        total_abs_impact = _emp_shap_t['impact_value'].abs().sum()
        _emp_shap_t['impact_percentage'] = (_emp_shap_t['impact_value'].abs() / total_abs_impact) * 100
        _emp_shap_t['feature_name'] = _emp_shap_t['feature'].map(feature_mapper.FEARURES_MEANING_MAPPER)
        _emp_shap_t['recommendation_action'] = _emp_shap_t['feature'].map(feature_mapper.FEATURES_ACTION_MAPPER)
        termination_reason_by_employee[str(emp_id)] = {
            'predicted_termination_probability': predicted_termination_probability,
            'impact_factors': _emp_shap_t[['feature_name', 'impact_percentage', 'recommendation_action']].sort_values(by='impact_percentage', ascending=False).to_dict(orient='records')
        }
    json_result["termination_reason_by_employee"] = termination_reason_by_employee

    # By Department
    department_shap = shap_with_metadata.groupby('department_name')[features].mean().reset_index()
    termination_reason_by_department = {}
    for department in department_shap['department_name'].unique():
        # ... (rest of the department analysis logic from notebook)
        num_emp_left = termination_emp[termination_emp['department_name'] == department].shape[0]
        num_emp_predicted_to_leave = termination_emp[(termination_emp['department_name'] == department) & (termination_emp['model_predicted_termination'] == True)].shape[0]
        avg_termination_probability = employee_metadata[employee_metadata['department_name'] == department]['model_predicted_termination_probability'].mean()
        _dept_shap_t = department_shap[department_shap['department_name'] == department][features].T.reset_index()
        _dept_shap_t.columns = ['feature', 'impact_value']
        abs_mean_shap_value = _dept_shap_t['impact_value'].abs().mean()
        _dept_shap_t = _dept_shap_t[_dept_shap_t['impact_value'].abs() > abs_mean_shap_value]
        total_abs_impact = _dept_shap_t['impact_value'].abs().sum()
        _dept_shap_t['impact_percentage'] = (_dept_shap_t['impact_value'].abs() / total_abs_impact) * 100
        _dept_shap_t['feature_name'] = _dept_shap_t['feature'].map(feature_mapper.FEARURES_MEANING_MAPPER)
        _dept_shap_t['recommendation_action'] = _dept_shap_t['feature'].map(feature_mapper.FEATURES_ACTION_MAPPER)
        termination_reason_by_department[department] = {
            'num_emp_left': num_emp_left,
            'num_emp_predicted_to_leave': num_emp_predicted_to_leave,
            'avg_termination_probability': avg_termination_probability,
            'impact_factors': _dept_shap_t[['feature_name', 'impact_percentage', 'recommendation_action']].sort_values(by='impact_percentage', ascending=False).to_dict(orient='records')
        }
    json_result["termination_reason_by_department"] = termination_reason_by_department

    # By Job Level
    job_level_shap = shap_with_metadata.groupby('job_level_name')[features].mean().reset_index()
    termination_reason_by_job_level = {}
    for job_level in job_level_shap['job_level_name'].unique():
        # ... (rest of the job level analysis logic from notebook)
        num_emp_left = termination_emp[termination_emp['job_level_name'] == job_level].shape[0]
        num_emp_predicted_to_leave = termination_emp[(termination_emp['job_level_name'] == job_level) & (termination_emp['model_predicted_termination'] == True)].shape[0]
        avg_termination_probability = employee_metadata[employee_metadata['job_level_name'] == job_level]['model_predicted_termination_probability'].mean()
        _level_shap_t = job_level_shap[job_level_shap['job_level_name'] == job_level][features].T.reset_index()
        _level_shap_t.columns = ['feature', 'impact_value']
        abs_mean_shap_value = _level_shap_t['impact_value'].abs().mean()
        _level_shap_t = _level_shap_t[_level_shap_t['impact_value'].abs() > abs_mean_shap_value]
        total_abs_impact = _level_shap_t['impact_value'].abs().sum()
        _level_shap_t['impact_percentage'] = (_level_shap_t['impact_value'].abs() / total_abs_impact) * 100
        _level_shap_t['feature_name'] = _level_shap_t['feature'].map(feature_mapper.FEARURES_MEANING_MAPPER)
        _level_shap_t['recommendation_action'] = _level_shap_t['feature'].map(feature_mapper.FEATURES_ACTION_MAPPER)
        termination_reason_by_job_level[job_level] = {
            'num_emp_left': num_emp_left,
            'num_emp_predicted_to_leave': num_emp_predicted_to_leave,
            'avg_termination_probability': avg_termination_probability,
            'impact_factors': _level_shap_t[['feature_name', 'impact_percentage', 'recommendation_action']].sort_values(by='impact_percentage', ascending=False).to_dict(orient='records')
        }
    json_result["termination_reason_by_job_level"] = termination_reason_by_job_level

    return json_result