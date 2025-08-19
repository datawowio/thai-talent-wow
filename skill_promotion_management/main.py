import os
import sys
import json
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config
from skill_gap_analysis import normalize_skill, analyze_current_position_gap, analyze_peer_gap, analyze_next_level_gap, recommend_roles_for_skills, analyze_department_skill_gap
from skill_rotation import generate_all_rotation_gaps
from promotion_analysis import promotion_analysis

def main():
    # normalize skill names and create mappings
    skill_df = pd.read_csv(config.SKILL_DATA)
    normalized_skill_df = normalize_skill(skill_df)
    id_to_canonical_map = normalized_skill_df.set_index('id')['canonical_id'].to_dict() # {skill_id: canonical_id}
    canonical_id_to_name_map = normalized_skill_df.drop_duplicates(subset=['canonical_id']).set_index('canonical_id')['canonical_name'].to_dict() # {canonical_id: canonical_name}

    # employee metadata
    emp_df = pd.read_csv(config.EMPLOYEE_DATA)
    movement_df = pd.read_csv(config.EMPLOYEE_MOVEMENT_DATA)
    # filter out employees who have left the company
    emp_df = emp_df.drop_duplicates(subset=['id'], keep='last')
    emp_df = emp_df[~emp_df['emp_id'].isin(movement_df[movement_df['movement_type'].isin([1, 2])]['employee_id'])] # movement_type 1 == voluntary termination, movement_type 2 == involuntary termination

    emp_skill_df = pd.read_csv(config.EMPLOYEE_SKILL_DATA)
    emp_skill_df = emp_skill_df.sort_values(by=['employee_id', 'skill_id', 'created_at'], ascending=[True, True, True])
    emp_skill_df = emp_skill_df.drop_duplicates(subset=['employee_id', 'skill_id'], keep='last')
    emp_skill_df['canonical_skill_id'] = emp_skill_df['skill_id'].map(id_to_canonical_map)
    emp_skill_df['canonical_skill_name'] = emp_skill_df['canonical_skill_id'].map(canonical_id_to_name_map)
    
    pos_skill_df = pd.read_csv(config.POSITION_SKILL_DATA)
    pos_skill_df['canonical_skill_id'] = pos_skill_df['skill_id'].map(id_to_canonical_map)
    pos_skill_df['canonical_skill_name'] = pos_skill_df['canonical_skill_id'].map(canonical_id_to_name_map)

    emp_pos_df = pd.read_csv(config.EMPLOYEE_MOVEMENT_DATA)
    emp_pos_df = emp_pos_df.sort_values(by=['employee_id', 'effective_date'], ascending=[True, True]).drop_duplicates(subset=['employee_id'], keep='last')[['employee_id', 'position_id']]

    position_df = pd.read_csv(config.POSITION_DATA)
    department_df = pd.read_csv(config.DEPARTMENT_DATA)

    # --- 1. Skill Gap by EMPLOYEE ---
    employee_analysis_result = []
    for emp_id in emp_df['emp_id']:
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

    #     # skills_to_learn = skill_gap_by_pos.get('missing_skills', []) + next_level_gap.get('skills_to_acquire', [])
    #     # skills_to_learn = sorted(list(set(skills_to_learn)))
    #     # recommendations = {}
    #     # if skills_to_learn:
    #     #     recommendations = recommend_roles_for_skills(
    #     #         employee_id=emp_id, 
    #     #         missing_skill_names=skills_to_learn, 
    #     #         emp_pos_df=emp_pos_df, 
    #     #         pos_skill_df=pos_skill_df, 
    #     #         pos_df=position_df, 
    #     #         id_map=canonical_id_to_name_map
    #     #     )


        employee_analysis_result.append({
            'employee_id': emp_id,
            'current_position': current_position,
            'next_position': next_position,
            'employee_skill': employee_skill_with_score,
            'current_missing_skill': current_missing_skill,
            'peer_missing_skill': peer_missing_skill,
            'next_missing_skill': next_missing_skill
        })

    with open(config.EMPLOYEE_SKILL_GAP_ANALYSIS_OUTPUT, 'w') as f:
        json.dump(employee_analysis_result, f, indent=4)


    # --- 2. Skill Gap by DEPARTMENT ---
    department_analysis_result = []
    for  department_id, department_name in department_df[['id', 'name']].values:
        total_employee, common_existing_skill, missing_skills_in_dept, skills_with_low_score = analyze_department_skill_gap(
            department_id=department_id,
            position_df=position_df,
            employee_position_df=emp_pos_df,
            employee_skill_df=emp_skill_df,
            position_skill_df=pos_skill_df,
        )

        department_analysis_result.append({
            'department_id': str(department_id),
            'department_name': department_name,
            'total_employee': total_employee,
            'common_existing_skill': common_existing_skill,
            'department_missing_skill': missing_skills_in_dept,
            'low_score_skill': skills_with_low_score
        })

    with open(config.DEPARTMENT_SKILL_GAP_ANALYSIS_OUTPUT, 'w') as f:
        json.dump(department_analysis_result, f, indent=4)


    # --- 3. Employee Rotation ---
    position_df = position_df.merge(department_df[['id', 'name']], left_on='department_id', right_on='id', how='left', suffixes=('', '_dept'))
    position_df = position_df.rename(columns={'name_dept': 'department_name'})
    position_df = position_df.drop(columns=['id_dept'])

    full_rotation_analysis = generate_all_rotation_gaps(
        employee_df=emp_df,
        position_df=position_df,
        employee_position_df=emp_pos_df,
        employee_skill_df=emp_skill_df,
        position_skill_df=pos_skill_df,
    )

    with open(config.ROTATION_SKILL_GAP_ANALYSIS_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(full_rotation_analysis, f, indent=4, ensure_ascii=False)
    

    # --- 4. Promotio Analysis ---
    # add movement data
    movement_df['effective_date'] = pd.to_datetime(movement_df['effective_date'], errors='coerce')
    movement_df = movement_df.sort_values(by=['employee_id', 'effective_date'], ascending=[True, True])
    # add evaluation data
    evaluation_df = pd.read_csv(config.EVALUATION_RECORD_DATA)
    evaluation_df['evaluation_date'] = pd.to_datetime(evaluation_df['evaluation_date'], errors='coerce')

    overlooked, disengaged, new_and_promising, on_track = promotion_analysis(
        employee_df=emp_df,
        movement_df=movement_df,
        evaluation_df=evaluation_df,
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
            'employee_id': employees
        })

    with open(config.PROMOTION_ANALYSIS_OUTPUT, 'w') as f:
        json.dump(promotion_result, f, indent=4)

if __name__ == "__main__":
    main()