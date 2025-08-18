import os
import sys
import json
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config

def analyze_rotation_skill_gap(employee_id, target_department_id, employee_skill_df, position_skill_df, position_df):
    """
    Analyzes the skill gap for an employee wanting to rotate to a new department (a larger group of positions).
    """
    # employee skills
    employee_skill_name = set(
        employee_skill_df.loc[employee_skill_df['employee_id'] == employee_id, 'canonical_skill_name'].dropna()
    )
    
    # position IDs within the target department
    position_id_in_dept = position_df.loc[position_df['department_id'] == target_department_id, 'id'].unique()
    # all unique skills required by those positions in department
    required_skill_name = set(
        position_skill_df.loc[position_skill_df['position_id'].isin(position_id_in_dept), 'canonical_skill_name'].dropna()
    )
    
    # calculate skill gap
    skills_to_acquire = required_skill_name - employee_skill_name

    return list(skills_to_acquire)


def generate_all_rotation_gaps(employee_df, position_df, employee_position_df, employee_skill_df, position_skill_df):
    """
    Calculates the skill gap for every employee against every possible rotation role.

    Returns:
        dict: A nested dictionary containing the skill gaps for all possible rotations.
              Structure: {employee_id: {target_department_id: {analysis_data}}}
    """    
    all_employees = employee_df['emp_id'].unique()
    all_departments = position_df['department_id'].unique() # use department_id instead; since position_id contains too various possible position (e.g. Junior,Mid,Senior,Lead,Chief xxxx)
    
    # Create a quick lookup for an employee's current department
    employee_position_df = employee_position_df.merge(position_df[['id', 'department_id', 'department_name']], left_on='position_id', right_on='id', how='left')
    current_employee_department = employee_position_df.set_index('employee_id')['department_id'].to_dict()
    
    full_rotation_analysis = []
    for emp_id in all_employees:
        current_dept_id = current_employee_department.get(emp_id)

        for target_dept_id in all_departments:
            if target_dept_id == current_dept_id:
                continue
            
            # calculate skill gap for this specific rotation
            rotation_gap = analyze_rotation_skill_gap(
                employee_id=emp_id,
                target_department_id=target_dept_id,
                employee_skill_df=employee_skill_df,
                position_skill_df=position_skill_df,
                position_df=position_df,
            )

            full_rotation_analysis.append({
                'employee_id': str(emp_id),
                'target_department_name': position_df.loc[position_df['department_id'] == target_dept_id, 'department_name'].values[0],
                'skills_to_acquire': rotation_gap,
            })
            
    return full_rotation_analysis