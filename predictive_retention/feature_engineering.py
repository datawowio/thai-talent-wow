### create features for predictive retention model
import os
import sys
import pandas as pd
from dateutil.relativedelta import relativedelta
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config

def calculate_z_score(dataframe, group_column, value_column):
    return dataframe.groupby(group_column)[value_column].transform(lambda x: (x - x.mean()) / x.std()).fillna(0).tolist()


def feature_engineering():
    ### assuming that all of the data already validated the type and column_name
    emp_df = pd.read_csv(config.EMPLOYEE_DATA)
    manager_df = pd.read_csv(config.MANAGER_LOG_DATA)
    emp_skill_df = pd.read_csv(config.EMPLOYEE_SKILL_DATA)
    position_df = pd.read_csv(config.POSITION_DATA)
    position_skill_df = pd.read_csv(config.POSITION_SKILL_DATA)
    emp_movement_df = pd.read_csv(config.EMPLOYEE_MOVEMENT_DATA)
    engagement_df = pd.read_csv(config.ENGAGEMENT_DATA)
    event_df = pd.read_csv(config.EVENT_DATA)
    leave_df = pd.read_csv(config.LEAVE_DATA)
    evaluation_record_df = pd.read_csv(config.EVALUATION_RECORD_DATA)
    clock_in_out_df = pd.read_csv(config.CLOCK_IN_OUT_DATA)
    department_df = pd.read_csv(config.DEPARTMENT_DATA)
    engagement_df = engagement_df.merge(event_df[['id', 'event_type', 'start_date']], left_on='event_id', right_on='id', how='left')

    ### convert data to proper datetime format
    for df in [emp_df, manager_df, emp_skill_df, position_df, position_skill_df, event_df, emp_movement_df, engagement_df, leave_df, evaluation_record_df, clock_in_out_df, department_df]:
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], format='%Y-%m-%d')
        for col in df.columns:
            if 'date' in col.lower():
                df[col] = pd.to_datetime(df[col], format='%Y-%m-%d', errors='coerce')

    ### final data needs to be in a time-series format with monthly + employee as a row
    ### get data range of months + set the date to end of the month
    first_month = emp_df['hire_date'].min()
    current_month = pd.to_datetime('today')
    date_range = pd.date_range(start=first_month, end=current_month, freq='ME')

    ### calculate distance from home to office at first (since it takes time to calculate)
    geolocator = Nominatim(user_agent="thailand_distance_calc")
    def get_coordinates(postal_code, country='Thailand'):
        location = geolocator.geocode(f"{postal_code}, {country}")
        if location:
            return (location.latitude, location.longitude)  
        return None
    def calculate_distance(coord1, coord2):
        if coord1 and coord2:
            return geodesic(coord1, coord2).km
        return None
    company_postal_code = config.COMPANY_POSTAL_CODE
    company_coords = get_coordinates(company_postal_code)

    _distance_df = emp_df.drop_duplicates(subset=['emp_id', 'residence_postal_code'], keep='last')[['emp_id', 'residence_postal_code']].copy()
    _distance_df['residence_coordinates'] = _distance_df['residence_postal_code'].apply(get_coordinates)
    _distance_df['distance_from_home_to_office'] = _distance_df['residence_coordinates'].apply(lambda x: calculate_distance(x, company_coords))
    
    final_df = pd.DataFrame()
    for execution_date in date_range[1:]:
        execution_date = pd.to_datetime(execution_date)
        execution_emp_df = emp_df[['id', 'birth_date', 'education_level', 'parent', 'child', 'sibling', 'spouse', 'hire_date', 'created_at']].copy()
        execution_emp_df.rename(columns={'id': 'emp_id'}, inplace=True)
        execution_emp_df = execution_emp_df[emp_df['hire_date'] <= execution_date].drop_duplicates(subset=['emp_id'], keep='last')
        execution_manager_df = manager_df[manager_df['created_at'] <= execution_date]
        execution_salary_df = emp_movement_df[emp_movement_df['effective_date'] <= execution_date][['employee_id', 'salary', 'effective_date']]
        execution_movement_df = emp_movement_df[emp_movement_df['effective_date'] <= execution_date]
        execution_emp_skill_df = emp_skill_df[emp_skill_df['created_at'] <= execution_date]
        execution_evaluation_record_df = evaluation_record_df[evaluation_record_df['evaluation_date'] <= execution_date]

        ### filter out employee who has left the company
        execution_emp_df = execution_emp_df[~execution_emp_df['emp_id'].isin(execution_movement_df[execution_movement_df['movement_type'].isin([1, 2])]['employee_id'])] # movement_type 1 == voluntary termination, movement_type 2 == involuntary termination

        ### execution_emp_df will contains [emp_id, demographic-data, position_id, job_level, department_id, avg_position_salary, emp_at_that_time_salary, emp_at_that_time_manager_id]
        latest_position = execution_movement_df.sort_values(by=['employee_id', 'effective_date'], ascending=[True, False]).drop_duplicates(subset=['employee_id'], keep='first')[['employee_id', 'position_id']]
        execution_emp_df = execution_emp_df.merge(latest_position[['employee_id', 'position_id']], left_on='emp_id', right_on='employee_id', how='left').drop(columns=['employee_id'])
        execution_emp_df = execution_emp_df.merge(position_df[['id', 'job_level', 'department_id', 'avg_salary']], left_on='position_id', right_on='id', how='left').drop(columns=['id'])
        execution_emp_df.rename(columns={'avg_salary': 'avg_market_salary'}, inplace=True)

        latest_salary = execution_salary_df.sort_values(by=['employee_id', 'effective_date'], ascending=[True, False]).drop_duplicates(subset=['employee_id'], keep='first')
        execution_emp_df = execution_emp_df.merge(latest_salary[['employee_id', 'salary']], left_on='emp_id', right_on='employee_id', how='left').drop(columns=['employee_id'])

        latest_manager = execution_manager_df.sort_values(by=['employee_id', 'created_at'], ascending=[True, False]).drop_duplicates(subset=['employee_id'], keep='first')
        latest_manager.rename(columns={'created_at': 'start_date_with_manager'}, inplace=True)
        execution_emp_df = execution_emp_df.merge(latest_manager[['employee_id', 'manager_id', 'start_date_with_manager']], left_on='emp_id', right_on='employee_id', how='left').drop(columns=['employee_id'])

        execution_engagement_df = engagement_df[engagement_df['start_date'] <= execution_date][['employee_id', 'event_id', 'event_type', 'start_date']].copy()

        latest_skill_df = execution_emp_skill_df.sort_values(by=['employee_id', 'created_at'], ascending=[True, False]).drop_duplicates(subset=['employee_id', 'skill_id'], keep='first')


        ### Demographic Features
        demographic_feaure = execution_emp_df[['emp_id', 'birth_date', 'education_level', 'parent', 'child', 'sibling', 'spouse']].copy()
        demographic_feaure['age'] = execution_date.year - demographic_feaure['birth_date'].dt.year
        demographic_feaure[['parent', 'child', 'sibling', 'spouse']] = demographic_feaure[['parent', 'child', 'sibling', 'spouse']].fillna(0)
        demographic_feaure.rename(columns={'parent': 'num_parent', 'child': 'num_child', 'sibling': 'num_sibling', 'spouse': 'num_spouse'}, inplace=True)

        demographic_feaure = demographic_feaure[['emp_id', 'age', 'education_level', 'num_parent', 'num_child', 'num_sibling', 'num_spouse']]


        ### Position Related Features
        position_feature = execution_emp_df.copy()
        position_feature['total_working_year'] = pd.to_timedelta((execution_date.date() - position_feature['hire_date'].dt.date)).dt.days / 365
        position_feature['total_working_year_z_manager'] = calculate_z_score(position_feature, 'manager_id', 'total_working_year')
        position_feature['total_working_year_z_position'] = calculate_z_score(position_feature, 'position_id', 'total_working_year')
        position_feature['total_working_year_z_job_level'] = calculate_z_score(position_feature, 'job_level', 'total_working_year')
        position_feature['total_working_year_z_department'] = calculate_z_score(position_feature, 'department_id', 'total_working_year')
        position_feature['department_name'] = position_feature['department_id'].map(department_df.set_index('id')['name'])

        position_feature = position_feature[['emp_id', 'job_level', 'department_name', 'total_working_year', 'total_working_year_z_manager', 'total_working_year_z_position', 'total_working_year_z_job_level', 'total_working_year_z_department']]


        ### Manager/Team Related Features
        manager_feature = execution_emp_df.copy()
        manager_feature['num_employee_under_manager'] = manager_feature.groupby('manager_id')['emp_id'].transform('count')
        manager_feature['year_with_current_manager'] = pd.to_timedelta((execution_date.date() - manager_feature['start_date_with_manager'].dt.date)).dt.days / 365
        manager_feature['num_past_manager'] = execution_manager_df.groupby('employee_id')['manager_id'].transform('nunique')
        manager_feature['num_employee_under_position'] = manager_feature.groupby('position_id')['emp_id'].transform('count')
        manager_feature['num_employee_under_job_level'] = manager_feature.groupby('job_level')['emp_id'].transform('count')
        manager_feature['num_employee_under_department'] = manager_feature.groupby('department_id')['emp_id'].transform('count')

        manager_feature = manager_feature[['emp_id', 'num_employee_under_manager', 'year_with_current_manager', 'num_past_manager', 'num_employee_under_position', 'num_employee_under_job_level', 'num_employee_under_department']]


        ### Salary Related Features
        salary_feature = execution_emp_df.copy()
        _min_salary_df = execution_salary_df.groupby('employee_id')['salary'].min().to_frame('min_salary')
        salary_feature = salary_feature.merge(_min_salary_df, left_on='emp_id', right_index=True, how='left')
        _latest_special_adjustment = execution_movement_df[execution_movement_df['movement_type'] == 5] # movement_type 5 == special adjustment
        _latest_special_adjustment = _latest_special_adjustment.groupby('employee_id')['effective_date'].max().to_frame('last_salary_adjustment_date')
        salary_feature = salary_feature.merge(_latest_special_adjustment, left_on='emp_id', right_index=True, how='left')
        salary_feature['last_salary_adjustment_date'] = salary_feature['last_salary_adjustment_date'].fillna(salary_feature['hire_date']) # fill person with no special adjustment with hire date

        salary_feature['salary_z_manager'] = calculate_z_score(salary_feature, 'manager_id', 'salary')
        salary_feature['salary_z_position'] = calculate_z_score(salary_feature, 'position_id', 'salary')
        salary_feature['salary_z_job_level'] = calculate_z_score(salary_feature, 'job_level', 'salary')
        salary_feature['percentage_salary_increase_since_hire'] = (salary_feature['salary'] - salary_feature['min_salary']) / salary_feature['min_salary']
        salary_feature['year_since_last_salary_adjustment'] = pd.to_timedelta((execution_date.date() - salary_feature['last_salary_adjustment_date'].dt.date)).dt.days / 365
        salary_feature['salary_compare_market_rate'] = salary_feature['salary'] / salary_feature['avg_market_salary']

        salary_feature = salary_feature[['emp_id', 'salary_z_manager', 'salary_z_position', 'salary_z_job_level', 'percentage_salary_increase_since_hire', 'year_since_last_salary_adjustment', 'salary_compare_market_rate']]


        ### Promotion Related # EDIT created_at ไปใช้อย่างอื่นแทน
        promotion_feature = execution_emp_df[['emp_id', 'position_id', 'hire_date']].copy()
        _latest_movement = execution_movement_df[execution_movement_df['movement_type'] == 3] # movement_type 3 == promotion
        _latest_movement = _latest_movement.groupby('employee_id')['effective_date'].max().to_frame('latest_promotion_date')
        _first_position_entry_date = execution_movement_df.groupby(['employee_id', 'position_id'])['effective_date'].min().reset_index()
        promotion_feature['first_position_entry_date'] = promotion_feature[['emp_id', 'position_id']].apply(
            lambda row: _first_position_entry_date[(_first_position_entry_date['employee_id'] == row['emp_id']) & (_first_position_entry_date['position_id'] == row['position_id'])]['effective_date'].values[0], axis=1
        )
        _latest_promotion = execution_movement_df[execution_movement_df['movement_type'] == 3].groupby('employee_id')['position_id'].count().to_frame('num_past_promotion')
        promotion_feature = promotion_feature.merge(_latest_movement, left_on='emp_id', right_index=True, how='left')
        promotion_feature['latest_promotion_date'] = promotion_feature['latest_promotion_date'].fillna(promotion_feature['hire_date']) ### fill person with no promotion with hire date

        promotion_feature['year_in_current_position'] = pd.to_timedelta((execution_date.date() - promotion_feature['first_position_entry_date'].dt.date)).dt.days / 365
        promotion_feature['num_past_promotion'] = promotion_feature['emp_id'].map(_latest_promotion['num_past_promotion']).fillna(0)
        promotion_feature['time_since_last_promotion'] = pd.to_timedelta((execution_date.date() - promotion_feature['latest_promotion_date'].dt.date)).dt.days / 365
        promotion_feature['avg_time_to_promotion'] = promotion_feature.groupby('emp_id')['time_since_last_promotion'].transform('mean')

        promotion_feature = promotion_feature[['emp_id', 'year_in_current_position', 'num_past_promotion', 'time_since_last_promotion', 'avg_time_to_promotion']]


        ### Career Development Related
        career_dev_feature = execution_emp_df[['emp_id']].copy()
        _training_count = execution_engagement_df[execution_engagement_df['event_type'] == 1].groupby('employee_id')['start_date'].count().to_frame('num_training') # event_type 1 == training
        _activity_count = execution_engagement_df[execution_engagement_df['event_type'] == 0].groupby('employee_id')['start_date'].count().to_frame('num_activity') # event_type 0 == activity
        career_dev_feature = career_dev_feature.merge(_training_count, left_on='emp_id', right_index=True, how='left')
        career_dev_feature = career_dev_feature.merge(_activity_count, left_on='emp_id', right_index=True, how='left')

        career_dev_feature['num_training'] = career_dev_feature['num_training'].fillna(0)
        career_dev_feature['num_activity'] = career_dev_feature['num_activity'].fillna(0)
        # career_dev_feature['avg_training_per_year'] = career_dev_feature['num_training'] / position_feature['total_working_year']
        # career_dev_feature['avg_activity_per_year'] = career_dev_feature['num_activity'] / position_feature['total_working_year']

        # career_dev_feature = career_dev_feature[['emp_id', 'num_training', 'num_activity', 'avg_training_per_year', 'avg_activity_per_year']]
        career_dev_feature = career_dev_feature[['emp_id', 'num_training', 'num_activity']]


        ### Skills Related Features
        skill_feature = execution_emp_df[['emp_id', 'position_id']].copy()
        _skill_score = latest_skill_df.groupby('employee_id')['skill_id'].agg(['count'])
        _skill_score['mean'] = latest_skill_df.groupby('employee_id')['score'].mean()
        
        skill_feature['num_skills'] = skill_feature['emp_id'].map(_skill_score['count']).fillna(0).astype(int)
        skill_feature['avg_skills_score'] = skill_feature['emp_id'].map(_skill_score['mean']).fillna(0).astype(float)

        _skill_per_position = position_skill_df.groupby('position_id')['skill_id'].apply(list).to_frame('required_skill_for_position')
        skill_feature['num_skill_gap'] = skill_feature.apply(
            lambda row: len(set(_skill_per_position.loc[row['position_id'], 'required_skill_for_position']) - set(latest_skill_df[latest_skill_df['employee_id'] == row['emp_id']]['skill_id'].tolist())) if row['position_id'] in _skill_per_position.index else 0, axis=1
        )
        
        # calculate abg and median skill score for each position_id
        _avg_position_skill_score = skill_feature.groupby('position_id')['avg_skills_score'].mean().to_frame('avg_score_per_position')
        _median_position_skill_score = skill_feature.groupby('position_id')['avg_skills_score'].median().to_frame('median_score_per_position')
        # compare emp skill score with average position score
        skill_feature['skill_score_vs_avg_position_score'] = skill_feature.apply(
            lambda row: row['avg_skills_score'] / _avg_position_skill_score.loc[row['position_id'], 'avg_score_per_position'] if row['position_id'] in _avg_position_skill_score.index else 0, axis=1
        )
        skill_feature['skill_score_vs_median_position_score'] = skill_feature.apply(
            lambda row: row['avg_skills_score'] / _median_position_skill_score.loc[row['position_id'], 'median_score_per_position'] if row['position_id'] in _median_position_skill_score.index else 0, axis=1
        )

        skill_feature = skill_feature[['emp_id', 'num_skills', 'avg_skills_score', 'num_skill_gap', 'skill_score_vs_avg_position_score', 'skill_score_vs_median_position_score']]


        ### Performance Related
        performance_feature = execution_emp_df[['emp_id', 'manager_id', 'position_id', 'job_level', 'department_id']].copy()
        _performance_score = execution_evaluation_record_df.groupby('employee_id')['score'].mean()

        performance_feature['avg_performance_score'] = performance_feature['emp_id'].map(_performance_score).fillna(0).astype(float)
        performance_feature['performance_score_z_manager'] = calculate_z_score(performance_feature, 'manager_id', 'avg_performance_score')
        performance_feature['performance_score_z_position'] = calculate_z_score(performance_feature, 'position_id', 'avg_performance_score')
        performance_feature['performance_score_z_job_level'] = calculate_z_score(performance_feature, 'job_level', 'avg_performance_score')
        performance_feature['performance_score_z_department'] = calculate_z_score(performance_feature, 'department_id', 'avg_performance_score')

        performance_feature = performance_feature[['emp_id', 'avg_performance_score', 'performance_score_z_manager', 'performance_score_z_position', 'performance_score_z_job_level', 'performance_score_z_department']]


        ### Work-Life Balance Related
        work_life_balance_feature = execution_emp_df[['emp_id']].copy()

        # total OT hours
        n_months = 3
        TIME_WINDOW_START = execution_date - pd.DateOffset(months=n_months)
        _ot_hour_df = clock_in_out_df[
            (clock_in_out_df['start_date'] >= TIME_WINDOW_START) &
            (clock_in_out_df['start_date'] <= execution_date) &
            (clock_in_out_df['clock_type'] == 2) # clock_type 2 == overtime
        ].groupby('employee_id')['hours'].sum().to_frame('total_ot_hours')
        work_life_balance_feature[f'total_ot_hours_{n_months}_months'] = work_life_balance_feature['emp_id'].map(_ot_hour_df['total_ot_hours']).fillna(0).astype(float)

        # total sick leave in past 6 months
        n_months = 6
        TIME_WINDOW_START = execution_date - pd.DateOffset(months=n_months)
        _sick_leave_df = leave_df[
            (leave_df['start_date'] >= TIME_WINDOW_START) &
            (leave_df['start_date'] <= execution_date) &
            (leave_df['leave_type'] == 1)  # leave_type 1 == sick leave
        ].groupby('employee_id')['hours'].sum().to_frame('total_sick_leave_hours')
        _vacation_leave_df = leave_df[
            (leave_df['start_date'] >= TIME_WINDOW_START) &
            (leave_df['start_date'] <= execution_date) &
            (leave_df['leave_type'] == 0)  # leave_type 0 == vacation leave
        ].groupby('employee_id')['hours'].sum().to_frame('total_vacation_leave_hours')
        work_life_balance_feature[f'total_sick_leave_hours_{n_months}_months'] = work_life_balance_feature['emp_id'].map(_sick_leave_df['total_sick_leave_hours']).fillna(0).astype(float)
        work_life_balance_feature[f'total_vacation_leave_hours_{n_months}_months'] = work_life_balance_feature['emp_id'].map(_vacation_leave_df['total_vacation_leave_hours']).fillna(0).astype(float)

        work_life_balance_feature['distance_from_home_to_office'] = work_life_balance_feature['emp_id'].map(_distance_df.set_index('emp_id')['distance_from_home_to_office']).fillna(0).astype(float)


        ### Termination Value (For TARGET)
        termination_target = execution_emp_df[['emp_id']].copy()

        # filter termination movements in the past 3 months
        _termination_df = emp_movement_df[
            (emp_movement_df['movement_type'] == 1) | # movement_type 1 == voluntary termination
            (emp_movement_df['movement_type'] == 2)]  # movement_type 2 == involuntary termination
        next_n_months = 3
        TIME_WINDOW_START = pd.to_datetime(execution_date).replace(day=1)
        TIME_WINDOW_END =  TIME_WINDOW_START + pd.DateOffset(months=next_n_months) - pd.DateOffset(days=1)
        _termination_df = _termination_df[
            (_termination_df['effective_date'] >= pd.to_datetime(execution_date).replace(day=1)) &
            (_termination_df['effective_date'] < TIME_WINDOW_END)]

        #  calculate target
        termination_target = termination_target.merge(_termination_df[['employee_id', 'effective_date']], left_on='emp_id', right_on='employee_id', how='left').drop(columns=['employee_id'])
        termination_target['month_diff'] = termination_target.apply( 
            lambda row: relativedelta(row['effective_date'], TIME_WINDOW_START).months
            if pd.notnull(row['effective_date']) else None, 
            axis=1
            )
        termination_target['termination_value'] = (3 - termination_target['month_diff']) / 3
        termination_target['termination_value'] = termination_target['termination_value'].fillna(0)

        termination_target = termination_target[['emp_id', 'termination_value']]

        ### merge all features into final_df
        combined_df = demographic_feaure.merge(position_feature, on='emp_id', how='left')
        combined_df = combined_df.merge(manager_feature, on='emp_id', how='left')
        combined_df = combined_df.merge(salary_feature, on='emp_id', how='left')
        combined_df = combined_df.merge(promotion_feature, on='emp_id', how='left')
        combined_df = combined_df.merge(career_dev_feature, on='emp_id', how='left')
        combined_df = combined_df.merge(skill_feature, on='emp_id', how='left')
        combined_df = combined_df.merge(performance_feature, on='emp_id', how='left')
        combined_df = combined_df.merge(work_life_balance_feature, on='emp_id', how='left')
        combined_df['execution_date'] = execution_date
        combined_df = combined_df.merge(termination_target, on='emp_id', how='left') # target value
        final_df = pd.concat([final_df, combined_df], ignore_index=True)

    final_df = final_df.drop_duplicates(subset=['emp_id', 'execution_date'], keep='last')
    final_df.to_csv(config.FEATURE_ENGINEERED_PATH, index=False, encoding='utf-8')
    return final_df