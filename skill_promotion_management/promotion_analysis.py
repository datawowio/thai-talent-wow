import pandas as pd
import numpy as np
from datetime import datetime


def promotion_analysis(employee_df, movement_df, evaluation_df, position_df, employee_position_df):
    """
    Analyze promotion readiness of employees based on their position, performance, and tenure.
    This function categorizes employees into four groups:
    1. Overlooked Employees: High potential but not promoted
    2. Disengaged Employees: Struggling / demotivated / not been promoted
    3. New & Promising Employees: Early signals of high potential
    4. On-track Employees: Everyone else


    Returns:
        A dictionary with lists of employee IDs for each category.
    """

    # get latest data
    latest_promotion = movement_df[movement_df['movement_type'] == 3].drop_duplicates(subset=['employee_id'], keep='last')[['employee_id', 'effective_date']] # movement_type 3 == promotion

    # get employee metadata from others df
    emp_df = pd.merge(employee_df, employee_position_df[['employee_id', 'position_id']], left_on='emp_id', right_on='employee_id', how='left').drop(columns=['emp_id', 'employee_id']) # position_id
    emp_df = emp_df.rename(columns={'id': 'emp_id'})
    emp_df = emp_df.merge(position_df[['id', 'name', 'department_id', 'job_level']], left_on='position_id', right_on='id', how='left').drop(columns=['id']) # position_name, department_id, job_level
    emp_df['latest_promotion_date'] = emp_df['emp_id'].map(latest_promotion.set_index('employee_id')['effective_date']) # latest_promotion_date
    emp_df['latest_promotion_date'].fillna(emp_df['hire_date'], inplace=True) # fill person with no promotion with hire date

    # calculate average time in role per position
    emp_df['years_since_last_promotion'] = (pd.to_datetime(datetime.now()) - pd.to_datetime(emp_df['latest_promotion_date'])).dt.days / 365
    emp_df['total_working_years'] = (pd.to_datetime(datetime.now()) - pd.to_datetime(emp_df['hire_date'])).dt.days / 365
    role_benchmark = emp_df.groupby(['position_id'])['years_since_last_promotion'].mean().reset_index()
    role_benchmark.rename(columns={'years_since_last_promotion': 'avg_years_in_role'}, inplace=True)
    emp_df = emp_df.merge(role_benchmark, on='position_id', how='left')

    # calculate recent average performance score (two years ago)
    two_years_ago = datetime.now() - pd.DateOffset(years=2)
    recent_evaluation = evaluation_df[
        (evaluation_df['evaluation_type'] == 0) & 
        (evaluation_df['evaluation_date'] >= two_years_ago)
    ].copy()
    avg_performance = recent_evaluation.groupby('employee_id')['score'].mean().reset_index()
    avg_performance.rename(columns={'score': 'avg_performance_score'}, inplace=True)
    emp_df = emp_df.merge(avg_performance, left_on='emp_id', right_on='employee_id', how='left').drop(columns=['employee_id'])

    # initialize lists for the four new categories
    overlooked_employees = []
    disengaged_employees = []
    on_track_employees = []
    new_and_promising_employees = []

    # define thresholds for categorization
    HIGH_PERFORMANCE_THRESHOLD = 3.5  # High performer if avg score > 3.5 (out of 5)
    LOW_PERFORMANCE_THRESHOLD = 2.5
    STALLED_MULTIPLIER = 1.5 # Stalled if 1.5x the average time for that level
    NEW_EMPLOYEE_YEARS = 1

    for _, row in emp_df.iterrows():
        is_stalled = row['years_since_last_promotion'] > (row['avg_years_in_role'] * STALLED_MULTIPLIER)
        is_high_performer = row['avg_performance_score'] >= HIGH_PERFORMANCE_THRESHOLD
        is_low_performer = row['avg_performance_score'] <= LOW_PERFORMANCE_THRESHOLD
        is_new = row['total_working_years'] < NEW_EMPLOYEE_YEARS

        # 1. Group Overlooked: High potential but not promoted
        if is_high_performer and is_stalled:
            overlooked_employees.append(row['emp_id'])

        # 2. Group Disengaged: Struggling / demotivated / not been promoted
        elif is_low_performer or is_stalled:
            disengaged_employees.append(row['emp_id'])

        # 4. Group New & Promising: Early signals of high potential
        elif is_high_performer and is_new:
            new_and_promising_employees.append(row['emp_id'])

        # 3. Group On-track: Everyone else
        else:
            on_track_employees.append(row['emp_id'])

    return overlooked_employees, disengaged_employees, new_and_promising_employees, on_track_employees