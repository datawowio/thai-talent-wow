import os
import sys
import json
import pandas as pd
import joblib
from google import genai
from dateutil.relativedelta import relativedelta

from config import config, feature_mapper

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config

def generate_termination_analysis(model_config, model_interpretation, model_result):
    """
    Loads model results and metadata to generate termination analysis visualizations.

    Returns:
        dict: A dictionary containing all the analysis results ready for JSON serialization.
    """
    json_result = {}

    # --- 1. Load and Prepare Data ---
    employee_metadata = pd.read_csv(config.FEATURE_ENGINEERED_PATH)
    employee_metadata['execution_date'] = pd.to_datetime(employee_metadata['execution_date'])
    employee_metadata = employee_metadata.sort_values(['emp_id', 'execution_date']).drop_duplicates('emp_id', keep='last')
    employee_metadata['model_predicted_termination'] = employee_metadata['emp_id'].map(
        model_result.set_index('emp_id')['predicted_termination']
    )
    employee_metadata['model_predicted_termination_probability'] = employee_metadata['emp_id'].map(
        model_result.set_index('emp_id')['termination_probability']
    )

    _employee_position_df = pd.read_csv(config.EMPLOYEE_MOVEMENT_DATA)
    _employee_position_df = _employee_position_df.sort_values(by=['employee_id', 'effective_date'], ascending=[True, False]).drop_duplicates(subset=['employee_id'], keep='first')[['employee_id', 'position_id']]
    _position_df = pd.read_csv(config.POSITION_DATA)
    employee_metadata['job_level_name'] = employee_metadata['job_level'].map(config.JOB_LEVEL_MAPPER)
    employee_metadata['position_id'] = employee_metadata['emp_id'].map(_employee_position_df.set_index('employee_id')['position_id'])
    employee_metadata['job_title'] = employee_metadata['position_id'].map(_position_df.set_index('id')['name'])
    employee_metadata['department_id'] = employee_metadata['position_id'].map(_position_df.set_index('id')['department_id'])

    # termination_emp = employee_metadata[(employee_metadata['model_predicted_termination'] == True) | (employee_metadata['termination_value'] > 0)]

    features = model_config['features']
    if 'department_name' in features:
        # rename department_name to department_name_shap in the SHAP values DataFrame
        features.remove('department_name')
        features.append('department_name_shap')
    shap_df_list = []
    for emp_id, shap_explanation in model_interpretation.items():
        shap_values = shap_explanation.values
        _temp_df = pd.DataFrame([shap_values], columns=features)
        _temp_df['emp_id'] = emp_id
        shap_df_list.append(_temp_df)

    all_shap_df = pd.concat(shap_df_list, ignore_index=True)
    # check if 'department_name' exists as a feature column (containing SHAP values).
    if 'department_name' in all_shap_df.columns:
        all_shap_df.rename(columns={'department_name': 'department_name_shap'}, inplace=True) 
    metadata_columns = ['emp_id', 'job_title', 'job_level', 'job_level_name', 'department_name', 'department_id']
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
        'average_termination_probability': round(employee_metadata['model_predicted_termination_probability'].mean(), 2),
        'termination_threshold': model_config['optimal_threshold']
    }


    # --- 3. Termination Proportions By DEPARTMENT ---
    department_count = employee_metadata[employee_metadata['termination_value'] > 0].groupby(['department_name', 'department_id'])['termination_value'].count().to_frame('termination_count').reset_index()
    json_result['department_proportion'] = department_count.sort_values('termination_count', ascending=False).to_dict(orient='records')

    # --- 4. Termination Proportions By JOB LEVEL ---
    level_count = employee_metadata[employee_metadata['termination_value'] > 0].groupby(['job_level', 'job_level_name'])['termination_value'].count().to_frame('termination_count').reset_index()
    level_count['level_name'] = level_count['job_level'].map(config.JOB_LEVEL_MAPPER)
    json_result['job_level_proportion'] = level_count[['job_level', 'level_name', 'termination_count']].sort_values('termination_count', ascending=False).to_dict(orient='records')


    # --- 5. Termination Probability Distribution by DEPARTMENT ---
    prob_dist_dept = employee_metadata.groupby(['department_name', 'department_id'])['model_predicted_termination_probability'].apply(lambda x: [p for p in x if pd.notna(p)])
    prob_dist_dept = prob_dist_dept.apply(lambda x: [round(p, 2) for p in x]).reset_index()
    json_result['department_distribution'] = [
        {'department_id': str(row['department_id']), 'department_name': row['department_name'], 'probabilities': row['model_predicted_termination_probability']}
        for _, row in prob_dist_dept.iterrows()
    ]


    # --- 6. Termination Probability Distribution by JOB LEVEL ---
    prob_dist_level = employee_metadata.groupby(['job_level_name', 'job_level'])['model_predicted_termination_probability'].apply(lambda x: [p for p in x if pd.notna(p)])
    prob_dist_level = prob_dist_level.apply(lambda x: [round(p, 2) for p in x]).reset_index()
    json_result['job_level_distribution'] = [
        {'job_level': str(row['job_level']), 'level_name': row['job_level_name'], 'probabilities': row['model_predicted_termination_probability']}
        for _, row in prob_dist_level.iterrows()
    ]
    

    # --- 7. Top reasons for quitting ---
    num_features = 5
    mean_importance = (all_shap_df.mean(axis=0, skipna=True).sort_values(ascending=False)).to_frame('impact_value')
    mean_importance = mean_importance.drop('emp_id', errors='ignore').reset_index().rename(columns={'index': 'feature'}).head(num_features)
    total_impact = mean_importance['impact_value'].sum()
    mean_importance['impact_percentage'] = round((mean_importance['impact_value'] / total_impact) * 100, 2)
    mean_importance['feature_name'] = mean_importance['feature'].map(feature_mapper.FEARURES_MEANING_MAPPER)

    # call generative ai for tailored recommendation action based on feature
    prompt = f"""You are an HR analytics expert. After built a predictive retention model, you will receive the top features contributing to employee termination risk, along with their impact values and percentages.
Your task is to generate concise, practical recommendations or actions based on these features to help reduce employee attrition.
The recommendations should be specific and actually actionable. Limit your response to 2-5 key recommendations, if the features are similar, group them into one recommendation. Each recommendation should be only one sentence long.

Top {num_features} features contributing to employee termination risk:
{mean_importance[['feature', 'impact_value', 'impact_percentage']].to_string(index=False)}

Return the result in the defined JSON schema.
"""
    
    response_schema = {
        "type": "object",
        "properties": {
            "recommendation": {
                "type": "array",
                "description": "List of concise, practical, and actionable recommendations derived from model features.",
                "items": {
                    "type": "object",
                    "properties": {
                        "feature": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of feature this recommendation is linked to. Group similar features together. Separate multiple features with comma.",
                        },
                        "recommendation_action": {
                            "type": "string",
                            "description": "A single actionable recommendation."
                        }
                    },
                    "required": ["feature", "recommendation_action"]
                },
                "minItems": 2,
                "maxItems": 5
            }
        },
        "required": ["recommendation"]
    }

    client = genai.Client(
    project=config.PROJECT_NAME, location=config.LOCATION, vertexai=True,
    )
    
    response = client.models.generate_content(
    model='gemini-2.5-flash', 
    contents=prompt,
    config={
        "response_mime_type": "application/json",
        "response_schema": response_schema,
    })

    try:
        recommendations = json.loads(response.text)
        recommendations = recommendations['recommendation']
    except:
        recommendations = []
    
    # map back the recommendation to the feature
    if isinstance(recommendations, list):
        df_recommendations = pd.DataFrame(recommendations)
        df_recommendations = df_recommendations.explode("feature")
        mean_importance = mean_importance.merge(df_recommendations, on="feature", how="left")

        # remove duplicated recommendations
        mean_importance['recommendation_action'] = mean_importance['recommendation_action'].where(
            ~mean_importance.duplicated(subset=['recommendation_action']), ''
        )
    else:
        mean_importance['recommendation_action'] = ''

    json_result['top_quitting_reason'] = mean_importance[['feature_name', 'impact_percentage', 'recommendation_action']].to_dict(orient='records')


    # --- Analysis by Employee, Department, and Job Level ---
    termination_shap_emp = employee_metadata[employee_metadata['model_predicted_termination'] == True].drop_duplicates('emp_id')[['emp_id']]
    termination_shap_emp = shap_with_metadata[shap_with_metadata['emp_id'].isin(termination_shap_emp['emp_id'])]
    termination_shap_emp['predicted_temination_probability'] = termination_shap_emp['emp_id'].map(model_result.set_index('emp_id')['termination_probability'])

    # --- 8. Termination reason by employee ---
    termination_reason_by_employee = []
    for emp_id in termination_shap_emp['emp_id'].unique():
        predicted_termination_probability = termination_shap_emp[termination_shap_emp['emp_id'] == emp_id]['predicted_temination_probability'].values[0]
        _emp_shap_t = termination_shap_emp[termination_shap_emp['emp_id'] == emp_id][features].T.reset_index()
        _emp_shap_t.columns = ['feature', 'impact_value']
        abs_mean_shap_value = _emp_shap_t['impact_value'].abs().mean()
        _emp_shap_t = _emp_shap_t[_emp_shap_t['impact_value'].abs() > abs_mean_shap_value]
        total_abs_impact = _emp_shap_t['impact_value'].abs().sum()
        _emp_shap_t['impact_percentage'] = round((_emp_shap_t['impact_value'].abs() / total_abs_impact) * 100, 2)
        _emp_shap_t['feature_name'] = _emp_shap_t['feature'].map(feature_mapper.FEARURES_MEANING_MAPPER)
        _emp_shap_t['recommendation_action'] = _emp_shap_t['feature'].map(feature_mapper.FEATURES_ACTION_MAPPER)

        termination_reason_by_employee.append({
            'employee_id': str(emp_id),
            'predicted_probability': round(predicted_termination_probability, 2),
            'impact_factors': _emp_shap_t[['feature_name', 'impact_percentage', 'recommendation_action']].sort_values(by='impact_percentage', ascending=False).to_dict(orient='records')
        })
    json_result["reason_by_employee"] = termination_reason_by_employee

    # --- 9. Termination reason by department ---
    department_shap = shap_with_metadata.groupby('department_name')[features].mean().reset_index()
    termination_reason_by_department = []
    for department in department_shap['department_name'].unique():
        num_emp_left = employee_metadata[employee_metadata['department_name'] == department][employee_metadata['termination_value'] > 0].shape[0]
        num_emp_predicted_to_leave = employee_metadata[(employee_metadata['department_name'] == department) & (employee_metadata['model_predicted_termination'] == True)].shape[0]
        avg_termination_probability = employee_metadata[employee_metadata['department_name'] == department]['model_predicted_termination_probability'].mean()
        department_id = employee_metadata[employee_metadata['department_name'] == department]['department_id'].iloc[0]
        _dept_shap_t = department_shap[department_shap['department_name'] == department][features].T.reset_index()
        _dept_shap_t.columns = ['feature', 'impact_value']
        abs_mean_shap_value = _dept_shap_t['impact_value'].abs().mean()
        _dept_shap_t = _dept_shap_t[_dept_shap_t['impact_value'].abs() > abs_mean_shap_value]
        total_abs_impact = _dept_shap_t['impact_value'].abs().sum()
        _dept_shap_t['impact_percentage'] = round((_dept_shap_t['impact_value'].abs() / total_abs_impact) * 100, 2)
        _dept_shap_t['feature_name'] = _dept_shap_t['feature'].map(feature_mapper.FEARURES_MEANING_MAPPER)
        _dept_shap_t['recommendation_action'] = _dept_shap_t['feature'].map(feature_mapper.FEATURES_ACTION_MAPPER)

        termination_reason_by_department.append({
            'department_id': str(department_id),
            'department_name': department,
            'total_employee_left': num_emp_left,
            'total_employee_to_leave': num_emp_predicted_to_leave,
            'avg_termination_probability': round(avg_termination_probability, 2),
            'impact_factors': _dept_shap_t[['feature_name', 'impact_percentage', 'recommendation_action']].sort_values(by='impact_percentage', ascending=False).to_dict(orient='records')
        })
    json_result["reason_by_department"] = termination_reason_by_department

    # --- 10. Termination reason by job level ---
    job_level_shap = shap_with_metadata.groupby('job_level_name')[features].mean().reset_index()
    termination_reason_by_job_level = []
    for job_level in job_level_shap['job_level_name'].unique():
        num_emp_left = employee_metadata[employee_metadata['job_level_name'] == job_level][employee_metadata['termination_value'] > 0].shape[0]
        num_emp_predicted_to_leave = employee_metadata[(employee_metadata['job_level_name'] == job_level) & (employee_metadata['model_predicted_termination'] == True)].shape[0]
        avg_termination_probability = employee_metadata[employee_metadata['job_level_name'] == job_level]['model_predicted_termination_probability'].mean()
        level_id = employee_metadata[employee_metadata['job_level_name'] == job_level]['job_level'].iloc[0]
        _level_shap_t = job_level_shap[job_level_shap['job_level_name'] == job_level][features].T.reset_index()
        _level_shap_t.columns = ['feature', 'impact_value']
        abs_mean_shap_value = _level_shap_t['impact_value'].abs().mean()
        _level_shap_t = _level_shap_t[_level_shap_t['impact_value'].abs() > abs_mean_shap_value]
        total_abs_impact = _level_shap_t['impact_value'].abs().sum()
        _level_shap_t['impact_percentage'] = round((_level_shap_t['impact_value'].abs() / total_abs_impact) * 100, 2)
        _level_shap_t['feature_name'] = _level_shap_t['feature'].map(feature_mapper.FEARURES_MEANING_MAPPER)
        _level_shap_t['recommendation_action'] = _level_shap_t['feature'].map(feature_mapper.FEATURES_ACTION_MAPPER)

        termination_reason_by_job_level.append({
            'job_level': str(level_id),
            'level_name': str(job_level),
            'total_employee_left': num_emp_left,
            'total_employee_to_leave': num_emp_predicted_to_leave,
            'avg_termination_probability': round(avg_termination_probability, 2),
            'impact_factors': _level_shap_t[['feature_name', 'impact_percentage', 'recommendation_action']].sort_values(by='impact_percentage', ascending=False).to_dict(orient='records')
        })
    json_result["reason_by_job_level"] = termination_reason_by_job_level

    return json_result