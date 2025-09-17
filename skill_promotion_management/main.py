import os
import sys
import json
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config
from skill_gap_analysis import normalize_skill, analyze_current_position_gap, analyze_peer_gap, analyze_next_level_gap, analyze_department_skill_gap, recommend_future_skills_for_department
from skill_rotation import generate_all_rotation_gaps
from promotion_analysis import categorize_employee_type, calculate_avg_promotion_time, calculate_promotion_rate_by_department
from performance_analysis import analyze_performance_trends

def main():
    # normalize skill names and create mappings
    skill_df = pd.read_csv(config.SKILL_DATA)
    normalized_skill_df = normalize_skill(skill_df)

    # employee metadata
    emp_df = pd.read_csv(config.EMPLOYEE_DATA)
    movement_df = pd.read_csv(config.EMPLOYEE_MOVEMENT_DATA)
    # filter out employees who have left the company
    emp_df['hire_date'] = pd.to_datetime(emp_df['hire_date'], errors='coerce')
    emp_df = emp_df.drop_duplicates(subset=['emp_id'], keep='last')
    active_emp_df = emp_df[~emp_df['id'].isin(movement_df[movement_df['movement_type'].isin([1, 2])]['employee_id'])] # movement_type 1 == voluntary termination, 2 == involuntary termination

    emp_skill_df = pd.read_csv(config.EMPLOYEE_SKILL_DATA)
    emp_skill_df = emp_skill_df.sort_values(by=['employee_id', 'skill_id', 'created_at'], ascending=[True, True, True])
    emp_skill_df = emp_skill_df.drop_duplicates(subset=['employee_id', 'skill_id'], keep='last')
    emp_skill_df['canonical_skill_id'] = emp_skill_df['skill_id'].map(normalized_skill_df.set_index('id')['canonical_id'])
    emp_skill_df['canonical_skill_name'] = emp_skill_df['canonical_skill_id'].map(normalized_skill_df.groupby('canonical_id')['canonical_name'].first())
    
    pos_skill_df = pd.read_csv(config.POSITION_SKILL_DATA)
    pos_skill_df['canonical_skill_id'] = pos_skill_df['skill_id'].map(normalized_skill_df.set_index('id')['canonical_id'])
    pos_skill_df['canonical_skill_name'] = pos_skill_df['canonical_skill_id'].map(normalized_skill_df.groupby('canonical_id')['canonical_name'].first())

    emp_pos_df = pd.read_csv(config.EMPLOYEE_MOVEMENT_DATA)
    emp_pos_df = emp_pos_df.sort_values(by=['employee_id', 'effective_date'], ascending=[True, True]).drop_duplicates(subset=['employee_id'], keep='last')[['employee_id', 'position_id']]

    position_df = pd.read_csv(config.POSITION_DATA)
    department_df = pd.read_csv(config.DEPARTMENT_DATA)
    department_df = department_df.sort_values(by=['id'])

    # --- 1. Skill Gap by EMPLOYEE ---
    employee_analysis_result = []
    for emp_id in active_emp_df['id']:
        current_position_id = emp_pos_df[emp_pos_df['employee_id'] == emp_id]['position_id'].values[0]
        employee_skill_with_score, current_missing_skill = analyze_current_position_gap(
            employee_id=emp_id,
            employee_position_id=current_position_id,
            employee_skill_df=emp_skill_df,
            position_skill_df=pos_skill_df,
        )

        peer_missing_skill = analyze_peer_gap(
            employee_id=emp_id,
            current_position_id=current_position_id,
            employee_position_df=emp_pos_df,
            employee_skill_df=emp_skill_df,
        )

        current_position, next_position, next_missing_skill = analyze_next_level_gap(
            employee_id=emp_id,
            current_position_id=current_position_id,
            position_df=position_df,
            position_skill_df=pos_skill_df,
            employee_skill_df=emp_skill_df,
        )

        employee_analysis_result.append({
            'employee_id': emp_id,
            'current_position': current_position,
            'next_position': next_position,
            'employee_skills': employee_skill_with_score,
            'current_missing_skills': current_missing_skill,
            'peer_missing_skills': peer_missing_skill,
            'next_missing_skills': next_missing_skill
        })

    with open(config.EMPLOYEE_SKILL_GAP_ANALYSIS_OUTPUT, 'w') as f:
        json.dump(employee_analysis_result, f, indent=4)


    # --- 2. Department Performance Trend ---
    # add evaluation data
    evaluation_df = pd.read_csv(config.EVALUATION_RECORD_DATA)
    evaluation_df['evaluation_date'] = pd.to_datetime(evaluation_df['evaluation_date'], errors='coerce')
    performance_evaluation_df = evaluation_df[evaluation_df['evaluation_type'] == 0] # evaluation_type 0 == performance review
    # merge department details into position_df
    position_df = position_df.merge(department_df[['id', 'name']], left_on='department_id', right_on='id', how='left', suffixes=('', '_dept'))
    position_df = position_df.rename(columns={'name_dept': 'department_name'})
    position_df = position_df.drop(columns=['id_dept'])

    department_analysis_result = []
    dept_performance_trends = analyze_performance_trends(
        evaluation_df=performance_evaluation_df,
        employee_df=emp_df,
        emp_pos_df=emp_pos_df,
        position_df=position_df
    )

    # --- 2. Department Skill Gap ---
    for department_id, department_name in department_df[['id', 'name']].values:
        total_employee, common_existing_skill, missing_skills_in_dept, skills_with_low_score = analyze_department_skill_gap(
            department_id=department_id,
            employee_df=active_emp_df,
            position_df=position_df,
            employee_position_df=emp_pos_df,
            employee_skill_df=emp_skill_df,
            position_skill_df=pos_skill_df,
        )

        dept_performance_trend = dept_performance_trends[dept_performance_trends['department_id'] == department_id]

        department_analysis_result.append({
            'department_id': str(department_id),
            'department_name': department_name,
            'total_employee': total_employee,
            'common_existing_skills': common_existing_skill,
            'department_missing_skills': missing_skills_in_dept,
            'low_score_skills': skills_with_low_score,
            'performance_trends': dept_performance_trend[['year_month', 'average_score']].to_dict(orient='records')
        })
    
    # --- 2. Recommend Future / Essential skills based on department skill gap ---
    department_analysis_df = pd.DataFrame(department_analysis_result)
    future_skills_recommendation = recommend_future_skills_for_department(
        department_analysis_df=department_analysis_df,
    )

    if isinstance(future_skills_recommendation, list):
        new_skills_df = pd.DataFrame(future_skills_recommendation)
        department_analysis_df = department_analysis_df.merge(new_skills_df, left_on='department_name', right_on='department_name', how='left')
        department_analysis_df['recommended_skills'] = department_analysis_df['recommended_skills'].apply(lambda x: x if isinstance(x, list) else [])
    else:
        department_analysis_df['recommended_skills'] = []
    
    with open(config.DEPARTMENT_SKILL_GAP_ANALYSIS_OUTPUT, 'w') as f:
        json.dump(department_analysis_df.to_dict(orient='records'), f, indent=4)

    # --- 3. Employee Rotation Skill Gap ---
    full_rotation_analysis = generate_all_rotation_gaps(
        employee_df=active_emp_df,
        position_df=position_df,
        employee_position_df=emp_pos_df,
        employee_skill_df=emp_skill_df,
        position_skill_df=pos_skill_df,
    )

    with open(config.ROTATION_SKILL_GAP_ANALYSIS_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(full_rotation_analysis, f, indent=4, ensure_ascii=False)
    

    # --- 4. Employee Promotion Analysis ---
    # add movement data
    movement_df['effective_date'] = pd.to_datetime(movement_df['effective_date'], errors='coerce')
    movement_df = movement_df.sort_values(by=['employee_id', 'effective_date'], ascending=[True, True])

    overlooked, disengaged, new_and_promising, on_track = categorize_employee_type(
        employee_df=active_emp_df,
        movement_df=movement_df,
        evaluation_df=performance_evaluation_df,
        position_df=position_df,
        employee_position_df=emp_pos_df
    )

    promotion_result = []
    for employee_type, employees in [
        ('Overlooked Talent', overlooked),
        ('Disengaged Employee', disengaged),
        ('New and Promising', new_and_promising),
        ('On Track', on_track)
    ]:
        promotion_result.append({
            'employee_type': employee_type,
            'total_employee': len(employees),
            'employee_ids': employees
        })

    promotion_analysis_result = {"employee_data": promotion_result}
    
    # --- 4. Average Time Taken for Promotion per Department, Job Level ---
    avg_time_by_department, avg_time_by_job_level = calculate_avg_promotion_time(
        employee_df=emp_df,
        movement_df=movement_df,
        position_df=position_df,
        emp_pos_df=emp_pos_df
    )
    promotion_analysis_result['avg_promotion_time_by_department'] = avg_time_by_department.to_dict(orient='records')
    promotion_analysis_result['avg_promotion_time_by_job_level'] = avg_time_by_job_level.to_dict(orient='records')
    
    # --- 4. Department Promomtion Rates ---
    department_promotion_rate = calculate_promotion_rate_by_department(
        employee_df=emp_df,
        movement_df=movement_df,
        position_df=position_df,
        emp_pos_df=emp_pos_df
    )
    promotion_analysis_result['department_promotion_rate'] = department_promotion_rate.to_dict(orient='records')

    with open(config.PROMOTION_ANALYSIS_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(promotion_analysis_result, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()