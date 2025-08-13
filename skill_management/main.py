import os
import sys
import json
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config
from skill_gap_analysis import normalize_skill, analyze_current_role_gap, analyze_peer_skill_gap, analyze_next_level_gap, recommend_roles_for_skills, analyze_skill_gap_by_department

def main():
    employee_analysis_result = {}

    # normalize skill names and create mappings
    skill_df = pd.read_csv(config.SKILL_DATA)
    normalized_skill_df = normalize_skill(skill_df)
    id_to_canonical_map = normalized_skill_df.set_index('id')['canonical_id'].to_dict() # {skill_id: canonical_id}
    canonical_id_to_name_map = normalized_skill_df.drop_duplicates(subset=['canonical_id']).set_index('canonical_id')['canonical_name'].to_dict() # {skill_id: canonical_name}

    # employee metadata
    emp_df = pd.read_csv(config.EMPLOYEE_DATA)
    movement_df = pd.read_csv(config.EMPLOYEE_MOVEMENT_DATA)
    # filter out employees who have left the company
    emp_df = emp_df.drop_duplicates(subset=['id'], keep='last')
    emp_df = emp_df[~emp_df['emp_id'].isin(movement_df[movement_df['movement_type'].isin([1, 2])]['employee_id'])] # movement_type 1 == voluntary termination, movement_type 2 == involuntary termination

    emp_skill_df = pd.read_csv(config.EMPLOYEE_SKILL_DATA)
    emp_skill_df = emp_skill_df.drop_duplicates(subset=['employee_id', 'skill_id'], keep='last')
    emp_skill_df['canonical_skill_id'] = emp_skill_df['skill_id'].map(id_to_canonical_map)
    
    position_skill_df = pd.read_csv(config.POSITION_SKILL_DATA)
    position_skill_df['canonical_skill_id'] = position_skill_df['skill_id'].map(id_to_canonical_map)

    emp_pos_df = pd.read_csv(config.EMPLOYEE_POSITION_DATA)
    emp_pos_df = emp_pos_df.drop_duplicates(subset=['employee_id'], keep='last')

    position_df = pd.read_csv(config.POSITION_DATA)
    department_df = pd.read_csv(config.DEPARTMENT_DATA)

    # Run skill gap by employee
    for emp_id in emp_df['emp_id']:
        skill_gap_by_pos = analyze_current_role_gap(
            employee_id=emp_id,
            emp_pos_df=emp_pos_df,
            emp_skill_df=emp_skill_df,
            pos_skill_df=position_skill_df,
            id_map=canonical_id_to_name_map
        )

        peer_gap = analyze_peer_skill_gap(
            employee_id=emp_id,
            emp_pos_df=emp_pos_df,
            emp_skill_df=emp_skill_df,
            id_map=canonical_id_to_name_map,
        )

        next_level_gap = analyze_next_level_gap(
            employee_id=emp_id,
            emp_pos_df=emp_pos_df,
            pos_df=position_df,
            pos_skill_df=position_skill_df,
            emp_skill_df=emp_skill_df,
            id_map=canonical_id_to_name_map
        )

        # skills_to_learn = skill_gap_by_pos.get('missing_skills', []) + next_level_gap.get('skills_to_acquire', [])
        # skills_to_learn = sorted(list(set(skills_to_learn)))
        # recommendations = {}
        # if skills_to_learn:
        #     recommendations = recommend_roles_for_skills(
        #         employee_id=emp_id, 
        #         missing_skill_names=skills_to_learn, 
        #         emp_pos_df=emp_pos_df, 
        #         pos_skill_df=position_skill_df, 
        #         pos_df=position_df, 
        #         id_map=canonical_id_to_name_map
        #     )

        # write to JSON
        employee_analysis_result[str(emp_id)] = {
            'skill_gap_by_position': skill_gap_by_pos,
            'peer_skill_gap': peer_gap,
            'next_level_gap': next_level_gap,
            # 'recommendations': recommendations
        }

    with open(config.EMPLOYEE_SKILL_GAP_ANALYSIS_OUTPUT, 'w') as f:
        json.dump(employee_analysis_result, f, indent=4)


    # Run skill gap by Department
    department_analysis_result = {}
    for dept_id in department_df['id'].unique():
        analysis_result = analyze_skill_gap_by_department(
            department_id=dept_id,
            pos_df=position_df,
            emp_pos_df=emp_pos_df,
            emp_skill_df=emp_skill_df,
            pos_skill_df=position_skill_df,
            id_map=canonical_id_to_name_map
        )
        department_analysis_result[str(dept_id)] = analysis_result

    with open(config.DEPARTMENT_SKILL_GAP_ANALYSIS_OUTPUT, 'w') as f:
        json.dump(department_analysis_result, f, indent=4)



if __name__ == "__main__":
    main()