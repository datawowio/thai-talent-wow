import os
import sys
import json
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config
from promotion_analysis import promotion_analysis

def main():
    # employee metadata
    emp_df = pd.read_csv(config.EMPLOYEE_DATA)
    movement_df = pd.read_csv(config.EMPLOYEE_MOVEMENT_DATA)
    # filter out employees who have left the company
    emp_df = emp_df.drop(columns=['id'])
    emp_df = emp_df.drop_duplicates(subset=['emp_id'], keep='last')
    emp_df = emp_df[~emp_df['emp_id'].isin(movement_df[movement_df['movement_type'].isin([1, 2])]['employee_id'])] # movement_type 1 == voluntary termination, movement_type 2 == involuntary termination

    # movement
    movement_df['effective_date'] = pd.to_datetime(movement_df['effective_date'], errors='coerce')
    movement_df = movement_df.sort_values(by=['employee_id', 'effective_date'], ascending=[True, True])

    # position
    position_df = pd.read_csv(config.POSITION_DATA)
    emp_pos_df = pd.read_csv(config.EMPLOYEE_POSITION_DATA)

    # evaluation
    evaluation_df = pd.read_csv(config.EVALUATION_RECORD_DATA)
    evaluation_df['evaluation_date'] = pd.to_datetime(evaluation_df['evaluation_date'], errors='coerce')

    # Run promotion analysis
    promotion_result = promotion_analysis(
        employee_df=emp_df,
        movement_df=movement_df,
        evaluation_df=evaluation_df,
        position_df=position_df,
        employee_position_df=emp_pos_df
    )
    
    # Write to JSON
    with open(config.PROMOTION_ANALYSIS_OUTPUT, 'w') as f:
        json.dump(promotion_result, f, indent=4)


if __name__ == "__main__":
    main()