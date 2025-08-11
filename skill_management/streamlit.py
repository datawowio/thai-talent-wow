import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(
    page_title="Skill Gap Analysis Dashboard",
    page_icon="🎯",
    layout="wide"
)

# --- Helper Function to Style Charts ---
def style_chart(fig):
    """Applies consistent styling to a Plotly figure."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#EAEAEA'),
        xaxis=dict(gridcolor='#4E4E4E'),
        yaxis=dict(gridcolor='#4E4E4E')
    )
    return fig

# --- Data Loading ---
@st.cache_data
def load_json_data(filepath):
    """Loads JSON data from the specified file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error(f"Error: The file '{filepath}' was not found. Please make sure it's in the same directory.")
        return None
    except json.JSONDecodeError:
        st.error(f"Error: The file '{filepath}' is not a valid JSON file.")
        return None

# Load both data files
employee_data = load_json_data('/Users/warisaraporn.l/Documents/TalentWow/output/employee_skill_gap_result.json')
department_data = load_json_data('/Users/warisaraporn.l/Documents/TalentWow/output/department_skill_gap_result.json')

# --- Main Dashboard UI ---
st.title("🎯 Skill Gap Analysis Dashboard")
st.markdown("An interactive tool to explore skill gaps by employee and department.")

if not employee_data or not department_data:
    st.error("One or more data files could not be loaded. Please check the files and try again.")
else:
    # Create main tabs for the two different views
    tab1, tab2 = st.tabs(["📊 Skill Gap by Department", "👤 Skill Gap by Employee"])

    # --- Department Analysis Tab ---
    with tab1:
        st.header("Department-Level Skill Analysis")
        
        # Create a select box for choosing a department
        dept_ids = list(department_data.keys())
        # Assuming department IDs are strings, create a more readable label
        dept_options = {f"Department {dept_id}": dept_id for dept_id in dept_ids}
        
        selected_dept_label = st.selectbox(
            "Select a Department to Analyze",
            options=list(dept_options.keys())
        )
        
        selected_dept_id = dept_options[selected_dept_label]
        dept_info = department_data[selected_dept_id]

        if "message" in dept_info:
            st.info(dept_info["message"])
        else:
            # Display summary metrics
            st.metric("Total Employees in Department", dept_info.get("total_employees", 0))

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Missing Required Skills")
                missing_skills = dept_info.get("missing_required_skills", [])
                if missing_skills:
                    st.warning("The following skills are required but are not common among employees:")
                    for skill in missing_skills:
                        st.markdown(f"- {skill}")
                else:
                    st.success("No significant gaps in required skills for this department.")
            
            with col2:
                st.subheader("Skills with Low Scores")
                low_score_skills = dept_info.get("skills_with_low_score", [])
                if low_score_skills:
                    st.error("Employees have the following skills, but the average score is low (< 2.5):")
                    for skill in low_score_skills:
                        st.markdown(f"- {skill}")
                else:
                    st.success("No skills with critically low average scores found.")

            st.markdown("---")
            
            # Box Plot for Common Skill Scores
            st.subheader("Score Distribution of Common Skills")
            common_skills = dept_info.get("common_existing_skills", {})
            if common_skills:
                fig = go.Figure()
                for skill, details in common_skills.items():
                    stats = details.get("stats", {})
                    fig.add_trace(go.Box(
                        y=[stats.get(k) for k in ['min', 'q1', 'median', 'q3', 'max']],
                        name=skill,
                        boxpoints=False # We only have the stats, not the raw points
                    ))
                
                fig.update_layout(
                    title="Skill Score Distribution (min, Q1, median, Q3, max)",
                    yaxis_title="Skill Score"
                )
                st.plotly_chart(style_chart(fig), use_container_width=True)
            else:
                st.info("No common skills found to generate a box plot.")


    # --- Employee Analysis Tab ---
    with tab2:
        st.header("Individual Employee Skill Analysis")
        
        # Create a select box for choosing an employee
        emp_ids = list(employee_data.keys())
        selected_emp_id = st.selectbox(
            "Select an Employee ID",
            options=emp_ids
        )
        
        emp_info = employee_data[selected_emp_id]

        # Display Skill Gap by Position
        st.subheader("Skill Gap vs. Current Position")
        pos_gap = emp_info.get("skill_gap_by_position", {})
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Skills Possessed (with score)**")
            emp_skills = pos_gap.get("employee_skills", [])
            if emp_skills:
                df_emp_skills = pd.DataFrame(emp_skills)
                st.dataframe(df_emp_skills, use_container_width=True)
            else:
                st.info("No skills recorded for this employee.")
        
        with col2:
            st.markdown("**Skills Missing for Current Role**")
            missing_skills = pos_gap.get("missing_skills", [])
            if missing_skills:
                for skill in missing_skills:
                    st.warning(f"- {skill}")
            else:
                st.success("No skills missing for the current role.")

        st.markdown("---")

        # Display Peer and Next Level Gaps
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Gap vs. Peers")
            peer_gap = emp_info.get("peer_skill_gap", {})
            if isinstance(peer_gap.get("missing_skills_vs_peers"), str):
                 st.info(peer_gap["missing_skills_vs_peers"])
            elif peer_gap.get("missing_skills_vs_peers"):
                for skill, details in peer_gap["missing_skills_vs_peers"].items():
                     st.markdown(f"- **{skill}**: Held by {details['peer_count']} peers ({details['percentage']})")
            else:
                st.success("No common skills missing compared to peers.")

        with col2:
            st.subheader("Gap vs. Next Level")
            next_level_gap = emp_info.get("next_level_gap", {})
            st.markdown(f"**Current Position:** {next_level_gap.get('current_position', 'N/A')}")
            st.markdown(f"**Next Position:** {next_level_gap.get('next_position', 'N/A')}")
            skills_to_acquire = next_level_gap.get("skills_to_acquire", [])
            if skills_to_acquire:
                st.markdown("**Skills to Acquire for Promotion:**")
                for skill in skills_to_acquire:
                    st.warning(f"- {skill}")
            else:
                st.success("No additional skills required for the next level.")
