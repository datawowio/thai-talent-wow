import streamlit as st
import pandas as pd
import json
import plotly.express as px

# --- Page Configuration ---
st.set_page_config(
    page_title="Termination Prediction Dashboard",
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
def load_data(filepath):
    """Loads the JSON data from the specified file."""
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

# Load the data
data = load_data('/Users/warisaraporn.l/Documents/TalentWow/output/termination_result.json')

if data:
    # --- Main Dashboard Title ---
    st.title("Employee Termination Prediction Dashboard")
    st.markdown("An overview of predicted employee turnover and the key driving factors.")

    # --- Overall Summary Section ---
    st.header("Overall Summary")
    summary = data.get("overall_summary", {})
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Employees", summary.get("total_employees", 0))
    col2.metric("Total Left (Historical)", summary.get("total_employees_left", 0))
    col3.metric("Predicted to Leave", summary.get("employees_predicted_to_leave", 0), help="In the next 3 months")
    avg_prob = summary.get("average_retention_probability", 0)
    col4.metric("Avg. Termination Probability", f"{round(avg_prob, 2)}", help="Average probability of leaving across all employees.")
    
    st.markdown("---")

    # --- Proportions and Top Reasons Section ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Termination by Department")
        dept_data = data.get("termination_proportion_by_department", [])
        if dept_data:
            df_dept = pd.DataFrame(dept_data)
            fig_dept = px.bar(
                df_dept, 
                x="department_name", 
                y="termination_count", 
                title="Historical Terminations per Department",
                labels={'department_name': 'Department', 'termination_count': 'Number of Terminations'}
            )
            st.plotly_chart(style_chart(fig_dept), use_container_width=True)
        else:
            st.warning("No department termination data available.")

    with col2:
        st.subheader("Termination by Job Level")
        level_data = data.get("termination_proportion_by_job_level", [])
        if level_data:
            df_level = pd.DataFrame(level_data)
            fig_level = px.bar(
                df_level, 
                x="level_name", 
                y="termination_count", 
                title="Historical Terminations per Job Level",
                labels={'level_name': 'Job Level', 'termination_count': 'Number of Terminations'}
            )
            st.plotly_chart(style_chart(fig_level), use_container_width=True)
        else:
            st.warning("No job level termination data available.")

    st.markdown("---")

    # --- Top Reasons for Quitting (Overall) ---
    st.subheader("Top Overall Reasons for Quitting")
    top_reasons_data = data.get("top_reasons_for_quitting", [])
    if top_reasons_data:
        df_reasons = pd.DataFrame(top_reasons_data)
        df_reasons = df_reasons.sort_values(by="impact_value", ascending=True)
        fig_reasons = px.bar(
            df_reasons,
            x='impact_value',
            y='feature_name',
            orientation='h',
            title='Top Factors Increasing Termination Risk (Company-Wide)',
            labels={'feature_name': 'Factor', 'impact_value': 'Average Impact on Termination Risk'}
        )
        fig_reasons.update_traces(marker_color='#FF4B4B')
        st.plotly_chart(style_chart(fig_reasons), use_container_width=True)
    else:
        st.warning("No top reasons data available.")
        
    st.markdown("---")
    
    # --- Detailed Analysis by Group ---
    st.header("Detailed Analysis")
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["By Employee", "By Department", "By Job Level"])

    with tab1:
        st.subheader("Termination Risk by Individual Employee")
        emp_data = data.get("termination_reason_by_employee", {})
        if emp_data:
            for emp_id, details in emp_data.items():
                with st.expander(f"Employee ID: {emp_id} (Risk: {details.get('predicted_termination_probability', 0):.1%})"):
                    st.write(f"**Predicted Termination Probability:** {details.get('predicted_termination_probability', 0):.1%}")
                    
                    df_factors = pd.DataFrame(details.get("impact_factors", []))
                    df_factors['color'] = df_factors['impact_value'].apply(lambda x: '#FF4B4B' if x > 0 else '#00B084')
                    df_factors = df_factors.sort_values(by="impact_value", ascending=True)
                    
                    fig_emp = px.bar(
                        df_factors,
                        x='impact_value',
                        y='feature_name',
                        orientation='h',
                        title=f'Key Factors for Employee {emp_id}',
                        labels={'feature_name': 'Factor', 'impact_value': 'Impact on Risk'}
                    )
                    fig_emp.update_traces(marker_color=df_factors['color'])
                    st.plotly_chart(style_chart(fig_emp), use_container_width=True)
        else:
            st.info("No individual employee data to display.")

    with tab2:
        st.subheader("Termination Risk by Department")
        dept_detail_data = data.get("termination_reason_by_department", {})
        if dept_detail_data:
            for dept_name, details in dept_detail_data.items():
                with st.expander(f"Department: {dept_name}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Employees Who Left", details.get("num_emp_left", 0))
                    c2.metric("Predicted to Leave", details.get("num_emp_predicted_to_leave", 0))
                    c3.metric("Avg. Termination Risk", f"{details.get('avg_termination_probability', 0):.1%}")
                    
                    df_factors = pd.DataFrame(details.get("impact_factors", []))
                    df_factors['color'] = df_factors['impact_value'].apply(lambda x: '#FF4B4B' if x > 0 else '#00B084')
                    df_factors = df_factors.sort_values(by="impact_value", ascending=True)

                    fig_dept_detail = px.bar(
                        df_factors,
                        x='impact_value',
                        y='feature_name',
                        orientation='h',
                        title=f'Key Factors for {dept_name} Department',
                        labels={'feature_name': 'Factor', 'impact_value': 'Average Impact on Risk'}
                    )
                    fig_dept_detail.update_traces(marker_color=df_factors['color'])
                    st.plotly_chart(style_chart(fig_dept_detail), use_container_width=True)
        else:
            st.info("No detailed department data to display.")
            
    with tab3:
        st.subheader("Termination Risk by Job Level")
        level_detail_data = data.get("termination_reason_by_job_level", {})
        if level_detail_data:
            for level_name, details in level_detail_data.items():
                with st.expander(f"Job Level: {level_name}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Employees Who Left", details.get("num_emp_left", 0))
                    c2.metric("Predicted to Leave", details.get("num_emp_predicted_to_leave", 0))
                    c3.metric("Avg. Termination Risk", f"{details.get('avg_termination_probability', 0):.1%}")
                    
                    df_factors = pd.DataFrame(details.get("impact_factors", []))
                    df_factors['color'] = df_factors['impact_value'].apply(lambda x: '#FF4B4B' if x > 0 else '#00B084')
                    df_factors = df_factors.sort_values(by="impact_value", ascending=True)

                    fig_level_detail = px.bar(
                        df_factors,
                        x='impact_value',
                        y='feature_name',
                        orientation='h',
                        title=f'Key Factors for {level_name} Level',
                        labels={'feature_name': 'Factor', 'impact_value': 'Average Impact on Risk'}
                    )
                    fig_level_detail.update_traces(marker_color=df_factors['color'])
                    st.plotly_chart(style_chart(fig_level_detail), use_container_width=True)
        else:
            st.info("No detailed job level data to display.")

else:
    st.error("Could not load data. Please check the file and try again.")