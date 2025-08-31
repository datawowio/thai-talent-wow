import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go

from config import config

# --- Page Configuration ---
st.set_page_config(
    page_title="TalentWow",
    page_icon="🧑‍🧑‍🧒‍🧒",
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
    if 'reason_by_employee' in termination_data and isinstance(termination_data['reason_by_employee'], list):
        termination_data['reason_by_employee'] = {str(item['employee_id']): item for item in termination_data['reason_by_employee']}
    if 'reason_by_department' in termination_data and isinstance(termination_data['reason_by_department'], list):
        termination_data['reason_by_department'] = {item['department_name']: item for item in termination_data['reason_by_department']}

promotion_data = {}
if raw_promotion_data:
    promotion_data = {item['employee_type']: item.get('employee_ids', []) for item in raw_promotion_data['employees_type']}
    promotion_data['avg_promotion_time_by_department'] = raw_promotion_data.get('avg_promotion_time_by_department', [])
    promotion_data['avg_promotion_time_by_job_level'] = raw_promotion_data.get('avg_promotion_time_by_job_level', [])
    promotion_data['department_promotion_rate'] = raw_promotion_data.get('department_promotion_rate', [])

employee_skill_data = {}
if raw_employee_skill_data:
    employee_skill_data = {str(emp['employee_id']): emp for emp in raw_employee_skill_data}

department_skill_data = {}
if raw_department_skill_data:
    department_skill_data = {dept['department_name']: dept for dept in raw_department_skill_data}

emp_df = pd.read_csv(config.EMPLOYEE_DATA)
emp_position_df = pd.read_csv(config.EMPLOYEE_MOVEMENT_DATA)
position_df = pd.read_csv(config.POSITION_DATA)
department_df = pd.read_csv(config.DEPARTMENT_DATA)
emp_df = emp_df.drop_duplicates(subset=['emp_id'], keep='last')
emp_df.drop(columns=['emp_id'], inplace=True)
emp_df.rename(columns={'id': 'emp_id'}, inplace=True)
emp_position_df = emp_position_df.sort_values(by=['employee_id', 'effective_date'], ascending=[True, True]).drop_duplicates(subset=['employee_id'], keep='last')[['employee_id', 'position_id']]
emp_df = emp_df.merge(emp_position_df, left_on='emp_id', right_on='employee_id', how='left').drop(columns=['employee_id'])
emp_df = emp_df.merge(position_df[['id', 'name', 'department_id']], left_on='position_id', right_on='id', how='left').drop(columns=['id'])
emp_df = emp_df.merge(department_df[['id', 'name']], left_on='department_id', right_on='id', how='left', suffixes=('', '_department')).drop(columns=['id', 'department_id'])
emp_df.rename(columns={'name': 'position_name', 'name_department': 'department_name'}, inplace=True)

# --- Sidebar Navigation ---
st.sidebar.title("🧑‍🧑‍🧒‍🧒 TalentWow")
page = st.sidebar.radio('', ["Termination Insights", "Department Insights", "Career & Promotion Insights", "Employee Insights", "Skills for Rotation"])

# ==============================================================================
# --- OVERALL PAGE ---
# ==============================================================================
if page == "Termination Insights":
    st.subheader("Employee Retention Analysis Insights")

    if termination_data and promotion_data:
        # --- High-Level Conclusion ---
        summary = termination_data.get("overall_summary", {})
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            with st.container(border=True):
                st.metric("Company Headcount", summary.get("total_employees", 0))
        with c2:
            with st.container(border=True):
                st.metric("Past Departures", summary.get("total_employees_left", 0))
        with c3:
            with st.container(border=True):
                st.metric("At-Risk Talent", summary.get("employees_predicted_to_leave", 0), help=f"Prediction period {summary.get('prediction_start_date')} ~ {summary.get('prediction_end_date')}")
        with c4:
            with st.container(border=True):
                st.metric("Company Risk Score", f"{round(summary.get('average_termination_probability', 0), 2)}", help="Average retention probability across all employees")        

        # --- Table of Employees Predicted to Leave ---
        st.markdown("##### At-Risk Employee Watchlist")
        st.caption(f"Prediction Period: {summary.get('prediction_start_date')} ~ {summary.get('prediction_end_date')}")
        emp_to_leave = pd.DataFrame(termination_data.get("reason_by_employee", []).keys(), columns=['employee_id'])
        emp_to_leave['predicted_probability'] = emp_to_leave['employee_id'].map(lambda x: termination_data.get("reason_by_employee", {}).get(str(x), {}).get("predicted_termination_probability", 0))
        emp_to_leave['employee_id'] = emp_to_leave['employee_id'].astype(int)
        emp_to_leave = emp_to_leave.merge(emp_df[['emp_id', 'first_name', 'last_name', 'birth_date', 'hire_date', 'position_name', 'department_name']], left_on='employee_id', right_on='emp_id', how='left').drop(columns=['emp_id'])
        emp_to_leave['age'] = pd.to_datetime('today').year - pd.to_datetime(emp_to_leave['birth_date'], errors='coerce').dt.year
        emp_to_leave['total_working_year'] = (pd.to_datetime('today') - pd.to_datetime(emp_to_leave['hire_date'], errors='coerce')).dt.days / 365

        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns([1, 0.3, 1, 1, 0.5, 0.75], vertical_alignment='top')
            col1.markdown("<div style='margin-top:0px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>Name</div>", unsafe_allow_html=True)
            col1.markdown('---')
            col2.markdown("<div style='margin-top:0px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>Age</div>", unsafe_allow_html=True)
            col2.markdown('---')
            col3.markdown("<div style='margin-top:0px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>Position</div>", unsafe_allow_html=True)
            col3.markdown('---')
            col4.markdown("<div style='margin-top:0px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>Department</div>", unsafe_allow_html=True)
            col4.markdown('---')
            col5.markdown("<div style='margin-top:0px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>Working Year</div>", unsafe_allow_html=True)
            col5.markdown('---')
            col6.markdown("<div style='margin-top:0px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>Predicted Probability</div>", unsafe_allow_html=True)
            col6.markdown('---')

            for i, row in emp_to_leave.iterrows():
                col1, col2, col3, col4, col5, col6 = st.columns([1, 0.3, 1, 1, 0.5, 0.75], vertical_alignment='top')
                col1.markdown(f"<div style='margin-top:10px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>{row['first_name']} {row['last_name']}</div>", unsafe_allow_html=True)
                col2.markdown(f"<div style='margin-top:10px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>{int(row['age']) if pd.notnull(row['age']) else 'N/A'}</div>", unsafe_allow_html=True)
                col3.markdown(f"<div style='margin-top:10px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>{row['position_name'] if pd.notnull(row['position_name']) else 'N/A'}</div>", unsafe_allow_html=True)
                col4.markdown(f"<div style='margin-top:10px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>{row['department_name'] if pd.notnull(row['department_name']) else 'N/A'}</div>", unsafe_allow_html=True)
                col5.markdown(f"<div style='margin-top:10px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>{round(row['total_working_year'], 1) if pd.notnull(row['total_working_year']) else 'N/A'}</div>", unsafe_allow_html=True)
                col6.markdown(f"<div style='margin-top:10px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>{round(row['predicted_probability'], 2)}</div>", unsafe_allow_html=True)
        st.markdown("---")


        # --- Termination by Department ---
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Which Departments Have the Highest Turnover?")
            dept_data = termination_data.get("department_proportion", [])
            df_dept = pd.DataFrame(dept_data)
            fig_dept = px.bar(
                df_dept, 
                x="department_name", 
                y="termination_count",
                color_discrete_sequence=['#a0c4ff'],
                labels={'department_name': 'Department', 'termination_count': 'Employee Departures'}
            )
            fig_dept.update_layout(xaxis_title=None)
            st.plotly_chart(style_chart(fig_dept), use_container_width=True)

        with col2:
            st.markdown("##### Turnover Trends by Seniority Level")
            level_data = termination_data.get("job_level_proportion", [])
            df_level = pd.DataFrame(level_data)
            fig_level = px.bar(
                df_level, 
                x="level_name", 
                y="termination_count",
                color_discrete_sequence=['#a0c4ff'],
                labels={'level_name': 'Job Level', 'termination_count': 'Employee Departures'}
            )
            fig_level.update_layout(xaxis_title=None)
            st.plotly_chart(style_chart(fig_level), use_container_width=True)


        # --- Termination Probability Distribution ---
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("##### Termination Risk Distribution by Department")
            prob_dist_data = termination_data.get("department_distribution", [])
            dept_probs_data = []
            for dept in prob_dist_data:
                for prob in dept.get('probabilities', []):
                    dept_probs_data.append({'Department': dept.get('department_name', 'N/A'), 'Probability': prob})
            
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

        with col4:
            st.markdown("##### Termination Risk Distribution by Job Level")
            level_prob_data = termination_data.get("job_level_distribution", [])
            level_probs_data = []
            for level in level_prob_data:
                for prob in level.get('probabilities', []):
                    level_probs_data.append({'Job Level': level.get('level_name', 'N/A'), 'Probability': prob})

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

        st.markdown("---")


        # --- Top Reasons for Quitting & Recommendations ---
        top_reasons = termination_data.get("top_quitting_reason", [])
        if top_reasons:
            df_reasons = pd.DataFrame(top_reasons).dropna()
            df_reasons = df_reasons.sort_values("impact_percentage", ascending=True)
            
            col1, col2 = st.columns([1.5, 1])
            with col1:
                st.markdown("##### Key Risk Factors -  What's Driving Attrition?")
                fig = px.bar(df_reasons, x='impact_percentage', y='feature_name', orientation='h', 
                             labels={'impact_percentage': 'How Much This Factor Matters (%)'})
                fig.update_layout(yaxis_title=None)
                fig.update_traces(marker_color='#e88989')
                st.plotly_chart(style_chart(fig), use_container_width=True)
            with col2:
                st.markdown("##### Actionable Insights - How to Respond?")
                for index, row in df_reasons.iloc[::-1].iterrows():
                    st.info(row['recommendation_action'])

# ==============================================================================
# --- CAREER & PROMOTION PAGE ---
# ==============================================================================
elif page == "Career & Promotion Insights":
    st.subheader("Career Velocity & Performance Pulse")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            overlooked_talent = promotion_data.get("Overlooked Talent", [])
            st.metric("💎 Overlooked Talent", len(overlooked_talent), help='Hidden Gems: High-Performers Awaiting Promotion')

    with c2:
        with st.container(border=True):
            disengaged_employee = promotion_data.get("Disengaged Employee", [])
            st.metric("⚠️ Disengaged Employees", len(disengaged_employee), help='Engagement Alert: At-Risk of Stagnation')
    with c3:
        with st.container(border=True):
            new_and_promising = promotion_data.get("New and Promising", [])
            st.metric("🌟 New & Promising Employees", len(new_and_promising), help='Rising Stars: Early High-Potential')
    with c4:
        with st.container(border=True):
            on_track = promotion_data.get("On Track", [])
            st.metric("✅ On-Track Employees", len(on_track), help='Steady Progress: On a Healthy Career Path')
    
    # --- Table of Employees in Overlooked, Disengaged, New & Promising ---
    emp_performance = pd.DataFrame(columns=['employee_id', 'performance_type'])
    emp_performance['employee_id'] = overlooked_talent + disengaged_employee + new_and_promising
    emp_performance['performance_type'] = (['Overlooked Talent'] * len(overlooked_talent) +
                                          ['Disengaged Employee'] * len(disengaged_employee) +
                                          ['New and Promising'] * len(new_and_promising))
    emp_performance['employee_id'] = emp_performance['employee_id'].astype(int)
    emp_performance = emp_performance.merge(emp_df[['emp_id', 'first_name', 'last_name', 'position_name', 'department_name']], left_on='employee_id', right_on='emp_id', how='left').drop(columns=['emp_id'])
    st.markdown("##### Employees in Need of Attention")
    with st.container():
        col1, col2, col3, col4 = st.columns([0.75, 1, 1, 1], vertical_alignment='top')
        col1.markdown("<div style='margin-top:0px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>Performance Type</div>", unsafe_allow_html=True)
        col1.markdown('---')
        col2.markdown("<div style='margin-top:0px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>Name</div>", unsafe_allow_html=True)
        col2.markdown('---')
        col3.markdown("<div style='margin-top:0px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>Position</div>", unsafe_allow_html=True)
        col3.markdown('---')
        col4.markdown("<div style='margin-top:0px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>Department</div>", unsafe_allow_html=True)
        col4.markdown('---')

        for i, row in emp_performance.iterrows():
            col1, col2, col3, col4 = st.columns([0.75, 1, 1, 1], vertical_alignment='top')
            with col1:
                st.badge(row['performance_type'], color='red', width='stretch')
            col2.markdown(f"<div style='margin-top:10px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>{row['first_name']} {row['last_name']}</div>", unsafe_allow_html=True)
            col3.markdown(f"<div style='margin-top:10px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>{row['position_name'] if pd.notnull(row['position_name']) else 'N/A'}</div>", unsafe_allow_html=True)
            col4.markdown(f"<div style='margin-top:10px; margin-bottom:0px; padding-bottom:0px; padding-top:0px; text-align:center;'>{row['department_name'] if pd.notnull(row['department_name']) else 'N/A'}</div>", unsafe_allow_html=True)
    
    st.markdown("---")

    # --- Avg. Year Taken for Promotion ---
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Department Velocity - Which Teams Promote Fastest?")
        promo_dept_data = promotion_data.get("avg_promotion_time_by_department", [])
        df_promo_dept = pd.DataFrame(promo_dept_data)
        df_promo_dept = df_promo_dept.sort_values(by="years_to_promotion", ascending=False)
        fig_promo_dept = px.bar(
            df_promo_dept, 
            x="department_name", 
            y="years_to_promotion",
            color_discrete_sequence=['#a0c4ff'],
            labels={'department_name': 'Department', 'years_to_promotion': 'Average Time Between Promotions (Years)'}
        )
        fig_promo_dept.update_layout(xaxis_title=None)
        st.plotly_chart(style_chart(fig_promo_dept), use_container_width=True)
    
    with col2:
        st.markdown("##### The Corporate Ladder - How Long at Each Rung?")
        promo_level_data = promotion_data.get("avg_promotion_time_by_job_level", [])
        df_promo_level = pd.DataFrame(promo_level_data)
        df_promo_level = df_promo_level.sort_values(by="years_to_promotion", ascending=False)
        fig_promo_level = px.bar(
            df_promo_level, 
            x="level_name", 
            y="years_to_promotion",
            color_discrete_sequence=['#a0c4ff'],
            labels={'level_name': 'Job Level', 'years_to_promotion': 'Average Time at Level Before Promotion (Years)'}
        )
        fig_promo_level.update_layout(xaxis_title=None)
        st.plotly_chart(style_chart(fig_promo_level), use_container_width=True)
    
    # --- Department Promotion Rate ---
    st.markdown("##### Which Departments Offer the Most Growth?")
    promo_rate_data = promotion_data.get("department_promotion_rate", [])
    df_promo_rate = pd.DataFrame(promo_rate_data)
    df_promo_rate = df_promo_rate.sort_values(by="promotion_rate_percent", ascending=False)
    fig_promo_rate = px.bar(
        df_promo_rate, 
        x="department_name", 
        y="promotion_rate_percent",
        color_discrete_sequence=['#a0c4ff'],
        labels={'department_name': 'Department', 'promotion_rate_percent': 'Promotion Rate (%)'}
    )
    fig_promo_rate.update_layout(xaxis_title=None)
    st.plotly_chart(style_chart(fig_promo_rate), use_container_width=True)
    
# ==============================================================================
# --- EMPLOYEE PAGE ---
# ==============================================================================
elif page == "Employee Insights":

    st.subheader("Individual Employee Analysis")
    if employee_skill_data and promotion_data and termination_data:
        emp_ids = list(employee_skill_data.keys())
        selected_emp_id = st.selectbox("Select an Employee ID", options=emp_ids, index=None)
        
        if selected_emp_id:
            emp_info = employee_skill_data[selected_emp_id]

            col1, col2 = st.columns(2)
            # --- Termination Risk ---
            with col1:
                if selected_emp_id in termination_data.get("reason_by_employee", {}):
                    term_info = termination_data["reason_by_employee"][selected_emp_id]
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

                if selected_emp_id in termination_data.get("reason_by_employee", {}):
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
                missing_skills = emp_info.get("current_missing_skills", [])
                if missing_skills:
                    st.warning("\n".join([f"- {s}" for s in missing_skills]))
                else:
                    st.success("No skills missing for current role.")
            

            # --- Skill VS. Peers ---
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("###### Gap vs. Peers")
                peer_gap = emp_info.get("peer_missing_skills", {})
                if isinstance(peer_gap, str):
                    st.info(peer_gap)
                elif isinstance(peer_gap, list) and len(peer_gap) > 0:
                    for skill in peer_gap:
                        st.warning(f"- **{skill['skill_name']}**: Held by {skill['peer_count']} peers ({skill['percentage_of_peer']}%)")
                else:
                    st.success("No common skills missing compared to peers.")

            with col2:
                st.markdown("###### Gap vs. Next Level")
                skill_to_acquire = emp_info.get("next_missing_skills", [])
                st.markdown(f"**Current:** {emp_info.get('current_position', 'N/A')}")
                st.markdown(f"**Next:** {emp_info.get('next_position', 'N/A')}")
                if skill_to_acquire:
                    st.warning("**Skills to Acquire:**\n\n" + "\n".join([f"- {s}" for s in skill_to_acquire]))
                else:
                    st.success("No additional skills identified for the next level.")

# ==============================================================================
# --- DEPARTMENT PAGE ---
# ==============================================================================
elif page == "Department Insights":
    st.subheader("Department Insight")

    col1, col2 = st.columns([1, 1])
    # --- Employee Headcount per Department ---
    with col1:
        st.markdown("##### Employee Headcount per Department")
        dept_headcount = [
            {'Department': dept_name, 'Employees': dept_data.get('total_employee', 0)}
            for dept_name, dept_data in department_skill_data.items()
        ]
        df_headcount = pd.DataFrame(dept_headcount).sort_values('Employees', ascending=False)
        fig_headcount = px.bar(df_headcount, x='Department', y='Employees',
                                labels={'Employees': 'Number of Employees'},
                                color_discrete_sequence=['#a0c4ff'])
        fig_headcount.update_layout(xaxis_title=None)  # Hide the x-axis label
        st.plotly_chart(style_chart(fig_headcount), use_container_width=True)
        
    # --- Department Performance Trend (All Departments)---
    with col2:
        st.markdown("##### Department Performance Trends")
        perf_records = []
        for dept_name, dept_data in department_skill_data.items():
            for perf in dept_data.get("performance_trends", []):
                perf_records.append({
                    "department": dept_name,
                    "year_month": perf["year_month"],
                    "average_score": perf["average_score"]
                })
        
        perf_df = pd.DataFrame(perf_records)
        perf_df['year_month'] = pd.to_datetime(perf_df['year_month'])
        perf_df = perf_df.sort_values('year_month')
        
        fig_perf_trend = px.line(
            perf_df, 
            x='year_month', 
            y='average_score', 
            color='department',
            labels={'average_score': 'Average Performance Score'},
            markers=True
        )
        fig_perf_trend.update_yaxes(rangemode="tozero")  # Ensure the y-axis starts from 0
        fig_perf_trend.update_layout(xaxis_title=None)  # Hide the x-axis label
        st.plotly_chart(style_chart(fig_perf_trend), use_container_width=True)


    # --- Dropdown for Each Department Analysis ---
    if department_skill_data and termination_data:
        dept_name_map = {item['department_name']: item['department_name'] for item in termination_data.get("department_proportion", [])}
        selected_dept_name = st.selectbox("Select a Department", options=list(dept_name_map.keys()), index=None)

        if selected_dept_name:            
            st.markdown(f"##### {selected_dept_name} Termination Insights")
            term_dept_info = termination_data.get("reason_by_department", {}).get(selected_dept_name)
            if term_dept_info:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    with st.container(border=True):
                        st.metric("Current Employees", department_skill_data.get(selected_dept_name, {}).get("total_employee", 0))
                with c2:
                    with st.container(border=True):
                        st.metric("Historical Departures", term_dept_info.get("total_employee_left", 0))
                with c3:
                    with st.container(border=True):
                        st.metric("Predicted to Leave", term_dept_info.get("total_employee_to_leave", 0))
                with c4:
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


            st.markdown("##### Performance Trends")
            skill_dept_info = department_skill_data.get(selected_dept_name)
            perf_records = []
            for perf in skill_dept_info.get("performance_trends", []):
                perf_records.append({
                    "year_month": perf["year_month"],
                    "average_score": perf["average_score"]
                })
            perf_df = pd.DataFrame(perf_records)
            perf_df['year_month'] = pd.to_datetime(perf_df['year_month'])
            perf_df = perf_df.sort_values('year_month')
            fig_perf_trend = px.line(
                perf_df, 
                x='year_month', 
                y='average_score', 
                labels={'average_score': 'Average Performance Score'},
                markers=True
            )
            fig_perf_trend.update_yaxes(range=[0, 5])  # Set y-axis range from 0 to 5
            fig_perf_trend.update_layout(xaxis_title=None)  # Hide the x-axis label
            st.plotly_chart(style_chart(fig_perf_trend), use_container_width=True)
            st.markdown("---")


            st.markdown("##### Skill Gap Insights")
            if skill_dept_info:
                c1, c2 = st.columns(2)
                with c1:
                    with st.container(border=True):
                        st.metric("Missing Required Skills", len(skill_dept_info.get("department_missing_skills", [])))
                with c2:
                    with st.container(border=True):
                        st.metric("Skills with Low Scores", len(skill_dept_info.get("low_score_skills", [])))
                
                st.markdown("###### Score Distribution for Common Skills")
                common_skills = skill_dept_info.get("common_existing_skills", [])
                if common_skills:
                    fig = go.Figure()
                    for skill in common_skills:
                        stats = skill.get("statistics", {})
                        if all(k in stats for k in ['min', 'q1', 'median', 'q3', 'max']):
                            fig.add_trace(go.Box(y=[stats[k] for k in ['min', 'q1', 'median', 'q3', 'max']], name=skill['skill_name'], boxpoints=False))
                    fig.update_layout(
                        yaxis_title="Skill Score",
                        yaxis=dict(range=[0, 5])  # Set y-axis range from 0 to 5
                    )
                    st.plotly_chart(style_chart(fig), use_container_width=True)
            st.markdown("---")


# ==============================================================================
# --- SKILL SEARCH FOR ROTATION PAGE ---
# ==============================================================================
elif page == "Skills for Rotation":
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
                available_depts = df_rotation[df_rotation['employee_id'] == selected_employee_id]['department_name'].unique()
                selected_department_name = st.selectbox("Select Target Department", options=sorted(available_depts), index=None)

        st.markdown("---")

        if selected_employee_id and selected_department_name:
            result = df_rotation[
                (df_rotation['employee_id'] == selected_employee_id) &
                (df_rotation['department_name'] == selected_department_name)
            ]
            
            if not result.empty:
                skill_to_acquire = result.iloc[0]['skills_to_acquire']
                st.markdown("##### Skills to Acquire")
                if skill_to_acquire:
                    st.warning("\n".join([f"- {skill}" for skill in skill_to_acquire]))
                else:
                    st.success("This employee already possesses all the required skills for this department.")
            else:
                st.info("No rotation path data found for this specific selection.")