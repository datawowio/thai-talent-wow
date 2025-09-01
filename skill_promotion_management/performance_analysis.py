import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config

def analyze_performance_trends(evaluation_df, employee_df, emp_pos_df, position_df):
    """
    Analyzes and calculates the overall performance trend for each department over time.

    Returns:
        pd.DataFrame: with columns ['department_id', 'department_name', 'year_month', 'average_score']
    """

    # Merge dataframes to link evaluations to departments
    employee_df = employee_df.drop(columns=['emp_id'])
    employee_df = employee_df.rename(columns={'id': 'employee_id'})
    evaluation_df = pd.merge(evaluation_df[['employee_id', 'score', 'evaluation_date']], employee_df[['employee_id']], left_on='employee_id', right_on='employee_id')
    evaluation_df = pd.merge(evaluation_df, emp_pos_df, on='employee_id')
    evaluation_df = pd.merge(evaluation_df, position_df, left_on='position_id', right_on='id')
    evaluation_df['evaluation_date'] = pd.to_datetime(evaluation_df['evaluation_date'])

    # Convert evaluation_date to datetime and extract the year-month for trend analysis
    evaluation_df['year_month'] = evaluation_df['evaluation_date'].dt.to_period('M').astype(str)

    # Calculate the average performance score per department per month
    dept_performance_trend = evaluation_df.groupby(['department_id', 'department_name', 'year_month'])['score'].mean().reset_index()
    dept_performance_trend.rename(columns={'name_dept': 'department_name', 'score': 'average_score'}, inplace=True)
    
    return dept_performance_trend