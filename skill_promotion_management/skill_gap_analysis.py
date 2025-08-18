import json
import numpy as np
import pandas as pd
from collections import defaultdict
from sentence_transformers import SentenceTransformer, util


def normalize_skill(skill_dataframe, threshold=0.66):
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
def analyze_current_position_gap(employee_id, employee_position_id, employee_skill_df, position_skill_df):
    """
    Analyzes the skill gap for a given employee based on their current position and position_skills.

    Returns:
        dict: A dictionary containing:
              - employee_skills: List of dictionaries with 'skill_name' and 'skill_score' for each skill the employee has
              - missing_skills_vs_current_position: List of skills required for the position that the employee is missing
    """
    # get skill for the employee
    indiv_skill_df = employee_skill_df.loc[employee_skill_df['employee_id'] == employee_id]

    # calculate missing skills for current position
    required_skill_ids = set(position_skill_df.loc[position_skill_df['position_id'] == employee_position_id, 'canonical_skill_id'])
    indiv_skill_ids = set(indiv_skill_df['canonical_skill_id'])
    missing_skill_ids = required_skill_ids - indiv_skill_ids
    missing_skill_name = position_skill_df[position_skill_df['skill_id'].isin(missing_skill_ids)]['canonical_skill_name'].unique().tolist()

    indiv_skill_with_score = [
        {'skill_name': row['canonical_skill_name'], 'skill_score': int(row['score'])}
        for _, row in indiv_skill_df.iterrows()
    ]
    indiv_skill_with_score = sorted(indiv_skill_with_score, key=lambda x: x['skill_score'], reverse=True)

    return indiv_skill_with_score, missing_skill_name


def analyze_peer_gap(employee_id, current_position_id, employee_position_df, employee_skill_df, common_threshold=0.1):
    """
    Analyzes the skill gap of an employee compared to their peers in the same position.
    
    Returns:
        dict: A dictionary containing:
              - missing_skills_vs_peers: A dictionary with skill names, percentage_of_peer, peer_count as keys
    """
    # get peer IDs in the same position
    peer_ids = employee_position_df.loc[(employee_position_df['position_id'] == current_position_id) & (employee_position_df['employee_id'] != employee_id), 'employee_id']
    
    if peer_ids.empty:
        return []

    # get skills for the peers
    peer_skills = employee_skill_df[employee_skill_df['employee_id'].isin(peer_ids)]
    employee_skills_id = set(employee_skill_df.loc[employee_skill_df['employee_id'] == employee_id, 'canonical_skill_id'])
    # calculate both percentage and absolute counts of employee having each skill
    peer_skill_freq = peer_skills['canonical_skill_id'].value_counts(normalize=True)
    peer_skill_abs_counts = peer_skills['canonical_skill_id'].value_counts(normalize=False)
    
    common_missing_skill = []
    for skill_id, freq in peer_skill_freq.items():
        if freq >= common_threshold and skill_id not in employee_skills_id:
            common_missing_skill.append({
                'skill_name': peer_skills.loc[peer_skills['canonical_skill_id'] == skill_id, 'canonical_skill_name'].iloc[0],
                'percentage_of_peer': f"{round(freq * 100, 2)}",
                'peer_count': int(peer_skill_abs_counts[skill_id])
            })

    return common_missing_skill


def analyze_next_level_gap(employee_id, current_position_id, position_df, position_skill_df, employee_skill_df):
    """
    Analyzes the next level position and the skills required for promotion for a specific employee.

    Returns:
        dict: A dictionary containing:
            - current_position: Current position of the employee
            - next_position: Next level position available for the employee
            - skills_to_acquire: List of skills required for the next level position that the employee does not have
    """
    # get the current position details
    current_position_details = position_df.loc[position_df['id'] == current_position_id]
    current_level = current_position_details['job_level'].iloc[0]
    current_department_id = current_position_details['department_id'].iloc[0]
    current_name = current_position_details['name'].iloc[0]
    current_position_name = f"{current_name} (L{current_level})"

    # get the next level position in the same department
    next_level_position = position_df[(position_df['department_id'] == current_department_id) & (position_df['job_level'] > current_level)].sort_values('job_level')

    if next_level_position.empty:
        return current_name, "No next level position available", []
    
    # calculate the next level skill details
    next_position_name = f"{next_level_position['name'].iloc[0]} (L{next_level_position['job_level'].iloc[0]})"
    next_level_position_id = next_level_position['id'].iloc[0]
    next_level_skill_name = set(position_skill_df.loc[position_skill_df['position_id'] == next_level_position_id, 'canonical_skill_name'])
    employee_skill_name = set(employee_skill_df.loc[employee_skill_df['employee_id'] == employee_id, 'canonical_skill_name'])
    missing_skills = next_level_skill_name - employee_skill_name

    return current_position_name, next_position_name, sorted(list(missing_skills))


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
def analyze_department_skill_gap(department_id, position_df, employee_position_df, employee_skill_df, position_skill_df, common_threshold=0.1):
   
    # get available positions/employee in the department
    position_id_in_dept = position_df[position_df['department_id'] == department_id]['id'].unique()
    employee_id_in_dept = employee_position_df[employee_position_df['position_id'].isin(position_id_in_dept)]
    employee_id_in_dept = employee_id_in_dept['employee_id'].unique()

    if len(employee_id_in_dept) == 0:
        return 0, [], [], []

    # gather all existing skills for employees in the department
    existing_skill_df = employee_skill_df[employee_skill_df['employee_id'].isin(employee_id_in_dept)]
    
    # --- 1. Common Existing Skills ---
    common_existing_skills = []
    skill_with_low_score = []
    if not existing_skill_df.empty:
        total_employee_in_dept = len(employee_id_in_dept)
        
        # Group by skill to calculate stats and frequency
        skill_group = existing_skill_df.groupby('canonical_skill_name')
        
        for skill_name, group in skill_group:
            # check skill with low average score
            average_score = group['score'].mean()
            if average_score < 2.5:
                skill_with_low_score.append(skill_name)

            # calculate score statistics (for the box plot)
            employee_count_for_skill = group['employee_id'].nunique()
            frequency = employee_count_for_skill / total_employee_in_dept
            if frequency >= common_threshold:
                scores = group['score']
                stats = scores.describe()
                
                common_existing_skills.append({
                    'skill_name': skill_name,
                    'percentage_of_employee': f"{round(frequency * 100, 2)}",
                    'statistics': {
                        'min': int(stats['min']),
                        'q1': float(stats['25%']),
                        'median': float(stats['50%']),
                        'q3': float(stats['75%']),
                        'max': int(stats['max'])
                    }
                })

    # --- 2. Missing Required Skills in DEPARTMENT ---
    # gather all required skills for the department
    required_skill = position_skill_df[position_skill_df['position_id'].isin(position_id_in_dept)]
    required_skill = set(required_skill['canonical_skill_name'].dropna())
    
    # calculate the skill gap
    existing_skill = set(existing_skill_df['canonical_skill_name'].dropna())
    missing_skills = required_skill - existing_skill

    return total_employee_in_dept, common_existing_skills, sorted(list(missing_skills)), skill_with_low_score