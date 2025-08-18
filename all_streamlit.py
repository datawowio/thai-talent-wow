import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go

from config import config

# --- Page Configuration ---
st.set_page_config(
    page_title="Talent Wow",
    page_icon="👥",
    layout="wide"
)

# --- Helper Functions ---
def style_chart(fig):
    """Applies consistent styling to a Plotly figure."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#c7c7c7'),
        xaxis=dict(gridcolor='#e3e1e1', showgrid=False),
        yaxis=dict(gridcolor='#e3e1e1')
    )
    return fig

@st.cache_data
def load_json_data(filepath):
    """Loads and caches JSON data from a file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.sidebar.error(f"File not found: {filepath}")
        return None
    except json.JSONDecodeError:
        st.sidebar.error(f"Invalid JSON in file: {filepath}")
        return None
    
# --- Data Loading ---
raw_termination_data = load_json_data(config.TERMINATION_ANALYSIS_OUTPUT)
raw_promotion_data = load_json_data(config.PROMOTION_ANALYSIS_OUTPUT)
raw_employee_skill_data = load_json_data(config.EMPLOYEE_SKILL_GAP_ANALYSIS_OUTPUT)
raw_department_skill_data = load_json_data(config.DEPARTMENT_SKILL_GAP_ANALYSIS_OUTPUT)
rotation_data = load_json_data(config.ROTATION_SKILL_GAP_ANALYSIS_OUTPUT)

termination_data = {}
if raw_termination_data:
    termination_data = raw_termination_data
    if 'termination_reason_by_employee' in termination_data and isinstance(termination_data['termination_reason_by_employee'], list):
        termination_data['termination_reason_by_employee'] = {str(item['employee_id']): item for item in termination_data['termination_reason_by_employee']}
    if 'termination_reason_by_department' in termination_data and isinstance(termination_data['termination_reason_by_department'], list):
        termination_data['termination_reason_by_department'] = {item['department_name']: item for item in termination_data['termination_reason_by_department']}

promotion_data = {}
if raw_promotion_data:
    promotion_data = {item['employee_type']: item.get('employee_ids', []) for item in raw_promotion_data}
    # For UI display, create a list of dicts for overlooked/disengaged employees
    # Note: This version only has IDs. We'll look up names from the skill data if available.
    promotion_data["overlooked_employees"] = [{'employee_id': eid} for eid in promotion_data.get("Overlooked Talent", [])]
    promotion_data["disengaged_employees"] = [{'employee_id': eid} for eid in promotion_data.get("Disengaged Employee", [])]
    promotion_data["new_and_promising_employees"] = [{'employee_id': eid} for eid in promotion_data.get("New and Promising", [])]

employee_skill_data = {}
if raw_employee_skill_data:
    employee_skill_data = {str(emp['employee_id']): emp for emp in raw_employee_skill_data}

department_skill_data = {}
if raw_department_skill_data:
    department_skill_data = {dept['department_name']: dept for dept in raw_department_skill_data}


# --- Sidebar Navigation ---
st.sidebar.title("👥 Talent Wow")
page = st.sidebar.radio("Go to", ["OVERALL", "EMPLOYEE", "DEPARTMENT", "SKILL SEARCH FOR ROTATION"])

# ==============================================================================
# --- OVERALL PAGE ---
# ==============================================================================
if page == "OVERALL":
    st.subheader("📊 Overall Company Insights")

    if termination_data and promotion_data:
        # --- High-Level Conclusion ---
        summary = termination_data.get("overall_summary", {})
        # --- Key Metrics for RETENTION ANALYSIS ---
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            with st.container(border=True):
                st.metric("Total Employees", summary.get("total_employees", 0))
        with c2:
            with st.container(border=True):
                st.metric("Total Left (Historical)", summary.get("total_employees_left", 0))
        with c3:
            with st.container(border=True):
                st.metric("Predicted to Leave", summary.get("employees_predicted_to_leave", 0), help="In the next 3 months")
        with c4:
            with st.container(border=True):
                st.metric("Avg. Termination Risk", f"{round(summary.get('average_termination_probability', 0), 2)}", help="Across all employees")

        # --- Key Metrics for PROMOTION READINESS ---
        c1, c2, c3, _ = st.columns(4)
        with c1:
            with st.container(border=True):
                st.metric("Overlooked Talent", len(promotion_data.get("overlooked_employees", [])))
        with c2:
            with st.container(border=True):
                st.metric("Disengaged Employees", len(promotion_data.get("disengaged_employees", [])))
        with c3:
            with st.container(border=True):
                st.metric("New & Promising Employees", len(promotion_data.get("new_and_promising_employees", [])))
        
        st.markdown("---")

        # --- Termination by Department ---
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Historical Terminations per Department")
            dept_data = termination_data.get("termination_proportion_by_department", [])
            if dept_data:
                df_dept = pd.DataFrame(dept_data)
                fig_dept = px.bar(
                    df_dept, 
                    x="department_name", 
                    y="termination_count",
                    color_discrete_sequence=['#a0c4ff'],
                    labels={'department_name': 'Department', 'termination_count': 'Number of Terminations'}
                )
                fig_dept.update_layout(xaxis_title=None)
                st.plotly_chart(style_chart(fig_dept), use_container_width=True)
            else:
                st.warning("No department termination data available.")

        with col2:
            st.markdown("##### Historical Terminations per Job Level")
            level_data = termination_data.get("termination_proportion_by_job_level", [])
            if level_data:
                df_level = pd.DataFrame(level_data)
                fig_level = px.bar(
                    df_level, 
                    x="level_name", 
                    y="termination_count",
                    color_discrete_sequence=['#a0c4ff'],
                    labels={'level_name': 'Job Level', 'termination_count': 'Number of Terminations'}
                )
                fig_level.update_layout(xaxis_title=None)
                st.plotly_chart(style_chart(fig_level), use_container_width=True)
            else:
                st.warning("No job level termination data available.")

        # --- Termination Probability Distribution ---
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("##### Termination Risk Distribution by Department")
            prob_dist_data = termination_data.get("termination_probability_distribution_by_department", [])
            if prob_dist_data:
                dept_probs_data = []
                for dept in prob_dist_data:
                    for prob in dept.get('probabilities', []):
                        dept_probs_data.append({'Department': dept.get('department_name', 'N/A'), 'Probability': prob})
                
                if dept_probs_data:
                    df_dept_probs = pd.DataFrame(dept_probs_data)
                    fig_dept_dist = px.strip(
                        df_dept_probs, x='Department', y='Probability', 
                        color_discrete_sequence=['#a0c4ff'],
                        labels={'Probability': 'Individual Termination Probability'}
                    )
                    # add reference line
                    threshold = summary.get('termination_threshold', 0.0)
                    fig_dept_dist.add_hline(y=threshold, line_dash="dash", line_color="lightgray", annotation_text="Threshold")

                    fig_dept_dist.update_layout(xaxis_title=None)
                    st.plotly_chart(style_chart(fig_dept_dist), use_container_width=True)
                else:
                    st.info("No probability data available for departments.")
            else:
                st.warning("No department probability distribution data available.")

        with col4:
            st.markdown("##### Termination Risk Distribution by Job Level")
            level_prob_data = termination_data.get("termination_probability_distribution_by_job_level", [])
            if level_prob_data:
                level_probs_data = []
                for level in level_prob_data:
                    for prob in level.get('probabilities', []):
                        level_probs_data.append({'Job Level': level.get('level_name', 'N/A'), 'Probability': prob})

                if level_probs_data:
                    df_level_probs = pd.DataFrame(level_probs_data)
                    fig_level_dist = px.strip(
                        df_level_probs, x='Job Level', y='Probability', 
                        color_discrete_sequence=['#a0c4ff'],
                        labels={'Probability': 'Individual Termination Probability'}
                        )
                    # add reference line
                    threshold = summary.get('termination_threshold', 0.0)
                    fig_level_dist.add_hline(y=threshold, line_dash="dash", line_color="lightgray", annotation_text="Threshold")
                    
                    fig_level_dist.update_layout(xaxis_title=None)
                    st.plotly_chart(style_chart(fig_level_dist), use_container_width=True)
                else:
                    st.info("No probability data available for job levels.")
            else:
                st.warning("No job level probability distribution data available.")

        st.markdown("---")


    # --- Top Reasons for Quitting & Recommendations ---
        top_reasons = termination_data.get("top_reasons_for_quitting", [])
        if top_reasons:
            df_reasons = pd.DataFrame(top_reasons).dropna()
            df_reasons = df_reasons.sort_values("impact_percentage", ascending=True)
            
            col1, col2 = st.columns([1.5, 1])
            with col1:
                st.markdown("##### Top Factors Driving Termination Risk (Company-Wide)")
                fig = px.bar(df_reasons, x='impact_percentage', y='feature_name', orientation='h', 
                             labels={'impact_percentage': 'How Much This Factor Matters (%)'})
                fig.update_layout(yaxis_title=None)
                fig.update_traces(marker_color='#e88989')
                st.plotly_chart(style_chart(fig), use_container_width=True)
            with col2:
                st.markdown("##### Top Recommendation")
                for index, row in df_reasons.iloc[::-1].iterrows():
                    st.info(row['recommendation_action'])


# ==============================================================================
# --- EMPLOYEE PAGE ---
# ==============================================================================
elif page == "EMPLOYEE":
    st.subheader("👤 Employee Analysis")

    # --- Key Metrics ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.metric("🚨 Overlooked Talent", len(promotion_data.get("overlooked_employees", [])))
    with c2:
        with st.container(border=True):
            st.metric("⚠️ Disengaged Employees", len(promotion_data.get("disengaged_employees", [])))
    with c3:
        with st.container(border=True):
            st.metric("🌟 New & Promising Employees", len(promotion_data.get("new_and_promising_employees", [])))
    with c4:
        with st.container(border=True):
            st.metric("✅ On-Track Employees", len(promotion_data.get("on_track_employees", [])))

    st.markdown("---")
    
    st.subheader("Individual Employee Analysis")
    if employee_skill_data and promotion_data and termination_data:
        emp_ids = list(employee_skill_data.keys())
        selected_emp_id = st.selectbox("Select an Employee ID", options=emp_ids, index=None)
        
        if selected_emp_id:
            emp_info = employee_skill_data[selected_emp_id]

            col1, col2 = st.columns(2)
            # --- Termination Risk ---
            with col1:
                if selected_emp_id in termination_data.get("termination_reason_by_employee", {}):
                    term_info = termination_data["termination_reason_by_employee"][selected_emp_id]
                    prob = term_info.get("predicted_termination_probability", 0)
                    st.error(f"**Predicted Termination Risk Probability:** {round(prob, 2)}")

                    st.markdown("###### Termination Risk Factors")
                    df_factors = pd.DataFrame(term_info.get("impact_factors", [])).dropna()
                    df_factors = df_factors.sort_values("impact_percentage", ascending=True)
                    fig = px.bar(df_factors, x='impact_percentage', y='feature_name', orientation='h',
                                labels={'feature_name': 'Factor', 'impact_percentage': 'How Much This Factor Matters (%)'})
                    fig.update_traces(marker_color='#e88989')
                    fig.update_layout(yaxis_title=None)
                    st.plotly_chart(style_chart(fig), use_container_width=True)

                else:
                    st.success("**Predicted Termination Risk:** Low")

            # --- Promotion Status ---
            with col2:
                status = "N/A"
                if int(selected_emp_id) in promotion_data.get("Overlooked Talent", []):
                    status = "🚨 Overlooked"
                elif int(selected_emp_id) in promotion_data.get("Disengaged Employee", []):
                    status = "⚠️ Disengaged"
                elif int(selected_emp_id) in promotion_data.get("On Track", []):
                    status = "✅ On-Track"
                elif int(selected_emp_id) in promotion_data.get("New and Promising", []):
                    status = "🌟 New & Promising"
                st.info(f"**Status:** {status}")

                if selected_emp_id in termination_data.get("termination_reason_by_employee", {}):
                    st.markdown("###### Top Recommendation")
                    for index, row in df_factors.iloc[::-1].iterrows():
                        st.info(row['recommendation_action'])
            
            # --- Skill Gap Analysis ---
            st.markdown("##### Skill Gap Analysis")
        
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("###### Skills Acquired")
                emp_skills = emp_info.get("employee_skills", [])
                if emp_skills:
                    df_emp_skills = pd.DataFrame(emp_skills)  # columns: 'skill', 'score'
                    fig = px.bar(
                        df_emp_skills,
                        x="skill_score",
                        y="skill_name",
                        orientation="h",
                        color="skill_score",
                        color_continuous_scale="Blues"
                    )
                    fig.update_layout(
                        yaxis=dict(autorange="reversed"),  # first skill at the top
                        yaxis_title=None,
                    )
                    st.plotly_chart(fig)

            with col2:
                st.markdown("###### Skills Missing for Current Role")
                missing_skills = emp_info.get("missing_skills_vs_current_position", [])
                if missing_skills:
                    st.warning("\n".join([f"- {s}" for s in missing_skills]))
                else:
                    st.success("No skills missing for current role.")
            

            # --- Skill VS. Peers ---
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("###### Gap vs. Peers")
                peer_gap = emp_info.get("missing_skills_vs_peers", {})
                if isinstance(peer_gap, str):
                    st.info(peer_gap)
                elif isinstance(peer_gap, list) and len(peer_gap) > 0:
                    for skill in peer_gap:
                        st.warning(f"- **{skill['skill_name']}**: Held by {skill['peer_count']} peers ({skill['percentage_of_peer']}%)")
                else:
                    st.success("No common skills missing compared to peers.")

            with col2:
                st.markdown("###### Gap vs. Next Level")
                skills_to_acquire = emp_info.get("missing_skills_vs_next_level", [])
                st.markdown(f"**Current:** {emp_info.get('current_position', 'N/A')}")
                st.markdown(f"**Next:** {emp_info.get('next_position', 'N/A')}")
                if skills_to_acquire:
                    st.warning("**Skills to Acquire:**\n\n" + "\n".join([f"- {s}" for s in skills_to_acquire]))
                else:
                    st.success("No additional skills identified for the next level.")

# ==============================================================================
# --- DEPARTMENT PAGE ---
# ==============================================================================
elif page == "DEPARTMENT":
    st.subheader("🏢 Department-Level Analysis")

    if department_skill_data and termination_data:
        dept_name_map = {item['department_name']: item['department_name'] for item in termination_data.get("termination_proportion_by_department", [])}
        selected_dept_name = st.selectbox("Select a Department", options=list(dept_name_map.keys()), index=None)

        if selected_dept_name:
            st.markdown("##### Termination Insights")
            term_dept_info = termination_data.get("termination_reason_by_department", {}).get(selected_dept_name)
            if term_dept_info:
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.container(border=True):
                        st.metric("Historical Departures", term_dept_info.get("number_of_employees_left", 0))
                with c2:
                    with st.container(border=True):
                        st.metric("Predicted to Leave", term_dept_info.get("number_of_employees_predicted_to_leave", 0))
                with c3:
                    with st.container(border=True):
                        st.metric("Avg. Termination Risk", f"{round(term_dept_info.get('avg_termination_probability', 0), 2)}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("###### Top Termination Factors for this Department")
                    df_factors = pd.DataFrame(term_dept_info.get("impact_factors", [])).dropna()
                    df_factors = df_factors.sort_values("impact_percentage", ascending=True)
                    fig = px.bar(df_factors, x='impact_percentage', y='feature_name', orientation='h',
                                labels={'feature_name': 'Factor', 'impact_percentage': 'How Much This Factor Matters (%)'})
                    fig.update_traces(marker_color='#e88989')
                    st.plotly_chart(style_chart(fig), use_container_width=True)
                with col2:
                    st.markdown("###### Top Recommendation")
                    for index, row in df_factors.iterrows():
                        st.info(row['recommendation_action'])
            else:
                st.info("No specific termination data available for this department.")
                
            st.markdown("---")

            st.markdown("##### Skill Gap Insights")
            skill_dept_info = department_skill_data.get(selected_dept_name)
            if skill_dept_info:
                c1, c2 = st.columns(2)
                with c1:
                    with st.container(border=True):
                        st.metric("Missing Required Skills", len(skill_dept_info.get("missing_skills_in_dept", [])))
                with c2:
                    with st.container(border=True):
                        st.metric("Skills with Low Scores", len(skill_dept_info.get("skills_with_low_score", [])))
                
                st.markdown("###### Score Distribution for Common Skills")
                common_skills = skill_dept_info.get("common_existing_skills", [])
                if common_skills:
                    fig = go.Figure()
                    for skill in common_skills:
                        stats = skill.get("statistics", {})
                        if all(k in stats for k in ['min', 'q1', 'median', 'q3', 'max']):
                            fig.add_trace(go.Box(y=[stats[k] for k in ['min', 'q1', 'median', 'q3', 'max']], name=skill['skill_name'], boxpoints=False))
                    fig.update_layout(yaxis_title="Skill Score")
                    st.plotly_chart(style_chart(fig), use_container_width=True)


# ==============================================================================
# --- SKILL SEARCH FOR ROTATION PAGE ---
# ==============================================================================
elif page == "SKILL SEARCH FOR ROTATION":
    st.subheader("🔄 Skill Search for Rotation")
    st.markdown("Find out what skills are needed for an employee to move to a different department.")

    if rotation_data and employee_skill_data:
        df_rotation = pd.DataFrame(rotation_data)
        
        col1, col2 = st.columns(2)
        with col1:
            employee_ids = sorted(df_rotation['employee_id'].unique())
            selected_employee_id = st.selectbox("Select Employee ID", options=employee_ids, index=None)
        
        with col2:
            if selected_employee_id:
                available_depts = df_rotation[df_rotation['employee_id'] == selected_employee_id]['target_department_name'].unique()
                selected_department_name = st.selectbox("Select Target Department", options=sorted(available_depts), index=None)

        st.markdown("---")

        if selected_employee_id and selected_department_name:
            result = df_rotation[
                (df_rotation['employee_id'] == selected_employee_id) &
                (df_rotation['target_department_name'] == selected_department_name)
            ]
            
            if not result.empty:
                skills_to_acquire = result.iloc[0]['skills_to_acquire']
                st.markdown("##### Skills to Acquire")
                if skills_to_acquire:
                    st.warning("\n".join([f"- {skill}" for skill in skills_to_acquire]))
                else:
                    st.success("This employee already possesses all the required skills for this department.")
            else:
                st.info("No rotation path data found for this specific selection.")