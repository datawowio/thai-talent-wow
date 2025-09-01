import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config

def categorize_employee_type(employee_df, movement_df, evaluation_df, position_df, employee_position_df):
    """
    Categorize employee type based on their position, performance, and tenure into four groups.
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
    recent_evaluation = evaluation_df[(evaluation_df['evaluation_date'] >= two_years_ago)].copy()
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



def calculate_avg_promotion_time(employee_df, movement_df, position_df, emp_pos_df):
    """
    Calculates the average years to promotion per department and job level.

    Returns:
        tuple: A tuple containing two DataFrames:
               - avg_time_by_department (pd.DataFrame): Average years to promotion by department.
               - avg_time_by_job_level (pd.DataFrame): Average years to promotion by job level.
    """
    # Filter for promotion events only
    promotions_df = movement_df[movement_df['movement_type'] == 3].copy() # movement_type 3 == promotion
    promotions_df = promotions_df.sort_values(by=['employee_id', 'effective_date'])

    # Create a DataFrame of all relevant events (hires and promotions)
    hire_events = employee_df[['id', 'hire_date']].rename(columns={'id': 'employee_id', 'hire_date': 'event_date'})
    hire_events['event_type'] = 'hire'

    promo_events = promotions_df[['employee_id', 'effective_date']].rename(columns={'effective_date': 'event_date'})
    promo_events['event_type'] = 'promotion'

    all_events = pd.concat([hire_events, promo_events]).sort_values(by=['employee_id', 'event_date'])

    # Calculate the date of the previous event for each promotion
    all_events['previous_event_date'] = all_events.groupby('employee_id')['event_date'].shift(1)
    
    # Keep only the promotion rows, which now have the start date of that role
    promotion_durations = all_events[all_events['event_type'] == 'promotion'].copy()
    promotion_durations['years_to_promotion'] = (
        promotion_durations['event_date'] - promotion_durations['previous_event_date']
    ).dt.days / 365

    # Add Department and Job Level Information
    # Note: This assumes the department/level at the time of the last role is what matters.
    promotion_durations = pd.merge(promotion_durations, emp_pos_df, on='employee_id')
    promotion_durations = pd.merge(promotion_durations, position_df, left_on='position_id', right_on='id')

    # Aaverage time to promotion by department
    avg_time_by_department = promotion_durations.groupby(['department_id', 'department_name'])['years_to_promotion'].mean().reset_index()
    avg_time_by_department['years_to_promotion'] = avg_time_by_department['years_to_promotion'].round(2)
    avg_time_by_department.sort_values(by=['years_to_promotion', 'department_id'], ascending=[False, True], inplace=True)
    # Average time to promotion by job level
    avg_time_by_job_level = promotion_durations.groupby('job_level')['years_to_promotion'].mean().reset_index()
    avg_time_by_job_level['years_to_promotion'] = avg_time_by_job_level['years_to_promotion'].round(2)
    avg_time_by_job_level['level_name'] = avg_time_by_job_level['job_level'].map(config.JOB_LEVEL_MAPPER)
    avg_time_by_job_level = avg_time_by_job_level[['job_level', 'level_name', 'years_to_promotion']]
    avg_time_by_job_level.sort_values(by=['years_to_promotion', 'job_level'], ascending=[False, True], inplace=True)

    return avg_time_by_department, avg_time_by_job_level


def calculate_promotion_rate_by_department(employee_df, movement_df, emp_pos_df, position_df):
    """
    Calculates the percentage of employees in each department who were promoted across all history.

    Returns:
        pd.DataFrame: A DataFrame with columns ['department_id', 'department_name', 'promotion_rate_percent'].
    """
    # Get all promotion events from history
    promotion_df = movement_df[movement_df['movement_type'] == 3].copy()

    # Get current employee and department info
    employee_df = employee_df.drop(columns=['emp_id']).rename(columns={'id': 'employee_id'})
    employee_df = pd.merge(employee_df[['employee_id']], emp_pos_df, left_on='employee_id', right_on='employee_id')
    employee_df = pd.merge(employee_df, position_df, left_on='position_id', right_on='id').drop(columns=['id'])

    # Count total employees per department
    employees_per_dept = employee_df.groupby(['department_id', 'department_name']).size().reset_index(name='total_employees')

    # Count total promotions per department
    promotions_per_dept = pd.merge(promotion_df, employee_df[['employee_id', 'department_name']], on='employee_id')
    promotions_per_dept = promotions_per_dept.groupby('department_name').size().reset_index(name='promotion_count')

    # Merge and calculate promotion rate
    dept_promotion_rates = pd.merge(employees_per_dept, promotions_per_dept, on='department_name', how='left').fillna(0)
    dept_promotion_rates['promotion_rate_percent'] = (
        dept_promotion_rates['promotion_count'] / dept_promotion_rates['total_employees']
    ) * 100
    dept_promotion_rates['promotion_rate_percent'] = dept_promotion_rates['promotion_rate_percent'].round(2)
    dept_promotion_rates.sort_values(by=['promotion_rate_percent', 'department_id'], ascending=[False, True], inplace=True)

    return dept_promotion_rates[['department_id', 'department_name', 'promotion_rate_percent']]
