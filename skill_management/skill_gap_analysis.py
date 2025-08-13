import json
import numpy as np
import pandas as pd
from collections import defaultdict
from sentence_transformers import SentenceTransformer, util


def normalize_skill(skill_dataframe: pd.DataFrame, threshold: float = 0.66):
    """
    Normalizes skill names by clustering and adds 'canonical_id' and 'canonical_name' columns directly to the input DataFrame.

    Returns:
        pd.DataFrame: The original DataFrame with two new columns added:
                      'canonical_id' and 'canonical_name'.
    """
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    skill_ids = skill_dataframe['id'].tolist()
    skill_names = skill_dataframe['name'].tolist()

    embeddings = model.encode(skill_names, convert_to_tensor=True)
    embeddings = util.normalize_embeddings(embeddings)
    embeddings = embeddings.cpu() # Move to CPU for compatibility with NumPy

    clustered_skills = {}
    processed_ids = set()
    # perform clustering
    for i, anchor_id in enumerate(skill_ids):
        if anchor_id in processed_ids:
            continue
        
        # search for similar skills
        anchor_embedding = embeddings[i]
        cosine_scores = util.cos_sim(anchor_embedding, embeddings)[0]
        similar_indices = np.where(cosine_scores >= threshold)[0]
        
        cluster_skill_ids = [skill_ids[j] for j in similar_indices]
        # Use the first skill name in the cluster as the canonical name
        clustered_skills[anchor_id] = sorted([skill_names[j] for j in similar_indices])
        processed_ids.update(cluster_skill_ids)
        
    # Create a mapping from any skill_id to its group's canonical info
    id_to_canonical_info_map = {}
    for canonical_id, skill_names_in_cluster in clustered_skills.items():
        canonical_name = skill_names_in_cluster[0] # The standard name for the group
        # Find all original skill_ids that belong to this cluster
        group_skill_ids = skill_dataframe[skill_dataframe['name'].isin(skill_names_in_cluster)]['id'].tolist()
        for skill_id in group_skill_ids:
            id_to_canonical_info_map[skill_id] = {'id': canonical_id, 'name': canonical_name}

    skill_dataframe['canonical_id'] = skill_dataframe['id'].map(lambda x: id_to_canonical_info_map.get(x, {}).get('id'))
    skill_dataframe['canonical_name'] = skill_dataframe['id'].map(lambda x: id_to_canonical_info_map.get(x, {}).get('name'))
    
    return skill_dataframe

### ANALYSIS PER EMPLOYEE
def analyze_current_role_gap(employee_id: int, emp_pos_df, emp_skill_df, pos_skill_df, id_map):
    """
    Analyzes the skill gap for a given employee based on their current position and position_skills.

    Returns:
        dict: A dictionary containing:
              - employee_skills: List of dictionaries with 'skill' and 'score' for each skill the employee has
              - missing_skills: List of skills required for the position that the employee is missing
    """
    
    current_pos_id = emp_pos_df.loc[emp_pos_df['employee_id'] == employee_id, 'position_id'].iloc[0]
    employee_skills_df = emp_skill_df.loc[emp_skill_df['employee_id'] == employee_id]

    required_skills_ids = set(pos_skill_df.loc[pos_skill_df['position_id'] == current_pos_id, 'canonical_skill_id'])
    employee_skills_ids = set(employee_skills_df['canonical_skill_id'])
    missing_skills_ids = required_skills_ids - employee_skills_ids

    employee_scores = employee_skills_df.groupby('canonical_skill_id')['score'].max()

    employee_skills_with_scores = [
        {'skill': id_map[sid], 'score': int(employee_scores.get(sid, 0))}
        for sid in employee_skills_ids if sid in id_map
    ]
    employee_skills_with_scores = sorted(employee_skills_with_scores, key=lambda x: x['score'], reverse=True) # sort by score in descending order

    return {
        "employee_skills": employee_skills_with_scores,
        "missing_skills": sorted([id_map[sid] for sid in missing_skills_ids if sid in id_map])
    }


def analyze_peer_skill_gap(employee_id: int, emp_pos_df, emp_skill_df, id_map, common_threshold=0.1):
    """
    Analyzes the skill gap of an employee compared to their peers in the same position.
    
    Returns:
        dict: A dictionary containing:
              - missing_skills_vs_peers: A dictionary with skill IDs as keys and their percentage and peer count as values
    """
    current_pos_id = emp_pos_df.loc[emp_pos_df['employee_id'] == employee_id, 'position_id'].iloc[0]
    peer_ids = emp_pos_df.loc[(emp_pos_df['position_id'] == current_pos_id) & (emp_pos_df['employee_id'] != employee_id), 'employee_id']
    
    if peer_ids.empty:
        return {"missing_skills_vs_peers": "No peers found in this position."}

    peer_skills = emp_skill_df[emp_skill_df['employee_id'].isin(peer_ids)]
    
    # Calculate both percentage and absolute counts
    peer_skill_freq = peer_skills['canonical_skill_id'].value_counts(normalize=True)
    peer_skill_abs_counts = peer_skills['canonical_skill_id'].value_counts(normalize=False)
    
    employee_skills_ids = set(emp_skill_df.loc[emp_skill_df['employee_id'] == employee_id, 'canonical_skill_id'])
    
    common_skills_missing = {
        id_map[skill_id]: {
            'percentage': f"{peer_skill_freq[skill_id]:.0%}",
            'peer_count': int(peer_skill_abs_counts[skill_id])
        }
        for skill_id in peer_skill_freq.index
        if peer_skill_freq[skill_id] >= common_threshold and skill_id not in employee_skills_ids and skill_id in id_map # only show skills that at least 10% of peers have
    }

    return {"missing_skills_vs_peers": common_skills_missing}


def analyze_next_level_gap(employee_id: int, emp_pos_df, pos_df, pos_skill_df, emp_skill_df, id_map):
    """
    Analyzes the next level position and the skills required for promotion for a specific employee.

    Returns:
        dict: A dictionary containing:
            - current_position: Current position of the employee
            - next_position: Next level position available for the employee
            - skills_to_acquire: List of skills required for the next level position that the employee does not have
    """
    current_pos_id = emp_pos_df.loc[emp_pos_df['employee_id'] == employee_id, 'position_id'].iloc[0]
    current_pos_details = pos_df.loc[pos_df['id'] == current_pos_id]
    current_level = current_pos_details['job_level'].iloc[0]
    current_department_id = current_pos_details['department_id'].iloc[0]
    current_name = current_pos_details['name'].iloc[0]

    next_level_pos = pos_df[(pos_df['department_id'] == current_department_id) & (pos_df['job_level'] > current_level)].sort_values('job_level')
    
    if next_level_pos.empty:
        return {
            "current_position": f"{current_name} (L{current_level})",
            "next_position": "No next level position available",
            "skills_to_acquire": []
        }
            
    next_level_pos_id = next_level_pos['id'].iloc[0]
    
    next_level_skills_ids = set(pos_skill_df.loc[pos_skill_df['position_id'] == next_level_pos_id, 'canonical_skill_id'])
    employee_skills_ids = set(emp_skill_df.loc[emp_skill_df['employee_id'] == employee_id, 'canonical_skill_id'])
    
    promotion_gap_ids = next_level_skills_ids - employee_skills_ids

    return {
        "current_position": f"{current_name} (L{current_level})",
        "next_position": f"{next_level_pos['name'].iloc[0]} (L{next_level_pos['job_level'].iloc[0]})",
        "skills_to_acquire": sorted([id_map[sid] for sid in promotion_gap_ids if sid in id_map])
    }


def recommend_roles_for_skills(employee_id: int, missing_skill_names: list, emp_pos_df, pos_skill_df, pos_df, id_map):
    """
    Recommend roles based on missing skills for a specific employee.
        
    Returns:
        dict: A dictionary where keys are skill names and values are lists of recommended roles.
    """
    current_pos_id = emp_pos_df.loc[emp_pos_df['employee_id'] == employee_id, 'position_id'].iloc[0]
    current_level = pos_df.loc[pos_df['id'] == current_pos_id, 'job_level'].iloc[0]

    name_to_canonical_id_map = {v: k for k, v in id_map.items()}
    
    skill_to_roles_map = defaultdict(list)
    merged_df = pd.merge(pos_skill_df, pos_df, left_on='position_id', right_on='id')

    for _, row in merged_df.iterrows():
        role_info = {
            'name': f"{row['name']} (L{row['job_level']})",
            'level': row['job_level']
        }
        if role_info not in skill_to_roles_map[row['canonical_skill_id']]:
            skill_to_roles_map[row['canonical_skill_id']].append(role_info)
        
    recommendations = {}
    for skill_name in missing_skill_names:
        canonical_id = name_to_canonical_id_map.get(skill_name)
        
        if canonical_id and canonical_id in skill_to_roles_map:
            potential_roles = skill_to_roles_map[canonical_id]
            
            # Filter roles based on the level condition: role_level <= current_level + 1
            filtered_roles = [role for role in potential_roles if role['level'] <= current_level + 1] 
            # Sort the filtered roles: same level first, then by level, then by name
            def sort_key(role):
                is_same_level = 0 if role['level'] == current_level else 1
                return (is_same_level, role['level'], role['name'])

            sorted_roles = sorted(filtered_roles, key=sort_key)            
            recommendations[skill_name] = [role['name'] for role in sorted_roles]
            if not recommendations[skill_name]:
                 recommendations[skill_name] = ["No suitable positions found within the level constraints."]

        else:
            recommendations[skill_name] = ["No position in the database explicitly requires this skill."]

    return recommendations


### ANALYSIS PER DEPARTMENT
def analyze_skill_gap_by_department(department_id, pos_df, emp_pos_df, emp_skill_df, pos_skill_df, id_map, common_threshold=0.1):

    position_ids_in_dept = pos_df[pos_df['department_id'] == department_id]['id'].unique()

    employees_in_dept = emp_pos_df[emp_pos_df['position_id'].isin(position_ids_in_dept)]
    employee_ids_in_dept = employees_in_dept['employee_id'].unique()
    # if len(employee_ids_in_dept) == 0:
        # return {"message": "No employees found in this department."}

    # gather all existing skills for employees in the department
    existing_skills_df = emp_skill_df[emp_skill_df['employee_id'].isin(employee_ids_in_dept)]
    
    # calculate common skills and their score statistics
    common_existing_skills = {}
    skills_with_low_score = []
    if not existing_skills_df.empty:
        total_employees_in_dept = len(employee_ids_in_dept)
        
        # Group by skill to calculate stats and frequency
        skill_groups = existing_skills_df.groupby('canonical_skill_id')
        
        for sid, group in skill_groups:
            skill_name = id_map.get(sid, f"Unknown Skill ID {sid}")
            
            # Check for low average score
            average_score = group['score'].mean()
            if average_score < 2.5:
                skills_with_low_score.append(skill_name)

            # Calculate score statistics for the box plot
            employee_count_for_skill = group['employee_id'].nunique()
            frequency = employee_count_for_skill / total_employees_in_dept
            
            if frequency >= common_threshold:
                scores = group['score']
                stats = scores.describe()
                
                common_existing_skills[skill_name] = {
                    'emp_percentage': f"{frequency:.0%}",
                    'stats': {
                        'min': int(stats.get('min', 0)),
                        'q1': float(stats.get('25%', 0)),
                        'median': float(stats.get('50%', 0)),
                        'q3': float(stats.get('75%', 0)),
                        'max': int(stats.get('max', 0))
                    }
                }

    # gather all required skills for the department
    required_skills_df = pos_skill_df[pos_skill_df['position_id'].isin(position_ids_in_dept)]
    all_required_skill_ids = set(required_skills_df['canonical_skill_id'].dropna())
    # calculate the skill gap
    existing_skill_ids = set(sid for sid, name in id_map.items() if name in common_existing_skills.keys())
    missing_skills_ids = all_required_skill_ids - existing_skill_ids
    missing_skills_names = sorted([id_map[sid] for sid in missing_skills_ids if sid in id_map])

    return {
        "total_employees": len(employee_ids_in_dept),
        "common_existing_skills": common_existing_skills,
        "missing_required_skills": missing_skills_names,
        "skills_with_low_score": sorted(skills_with_low_score)
    }