# th.ai-talent-wow

This repository contains a suite of analytics modules designed to provide deep insights into talent management, focusing on employee retention, skill development, and career progression.

Modules Overview
The project is composed of four main analysis modules:
1. **Predictive Retention Analysis** - Utilizes a predictive model to forecast employee termination probability and identifies the key factors influencing attrition.
2. **Skill Gap Analysis** - Assesses and visualizes skill gaps for individual employees and entire departments.
3. **Department Rotation Analysis** - Identifies the skills an employee would need to acquire to successfully transition to a different department.
4. **Promotion Readiness Analysis** - Categorizes employees based on their readiness for promotion, identifying overlooked talent and disengaged individuals.

---

## Requirements
- Python 3.12+
- Install dependencies before running:
```bash
pip install -r requirements.txt
```

---
## Usage
### 1. Predictive Retention Analysis
To train the predictive retention analysis model:
```bash
python predictive_retention/main.py
```

**Results**
- The saved model and its configuration is saved in:
  ```output/model```
- JSON output of the prediction results and analysis is stored at:
  ```output/termination_result.json```

---

### 2. Skill Gap, Promotion, and Rotation Analysis
To run the skill gap analysis:
```bash
python skill_promotion_management/main.py
```

**Results**
- JSON output of the **Employee** skill gap analysis is stored at:
  ```output/employee_skill_gap_result.json```
- JSON output of the **Department** skill gap analysis is stored at:
  ```output/department_skill_gap_result.json```
- JSON output of the **Rotation** analysis is stored at:
  ```output/rotation_skill_gap_result.json```
- JSON output of the **Promotion** analysis is stored at:
  ```output/promotion_analysis_results.json```

**Key Results**

A main key of each JSON file is listed in ```json_output_key.txt``` for quick reference and understanding of the output structure.

---

## Example dashboard 
To view the example dashboard of how each variable can be visualize and plot, run:
```bash
streamlit run all_streamlit.py
```

---

## File Structure
```
├── config/                     # Configuration files
├── mock_data/                  # Sample data for testing
├── output/                     # Output files and results
├── predictive_retention/       # Predictive retention analysis module
├── skill_promotion_management/ # Skill gap, promotion, and rotation analysis module
├── all_streamlit.py            # Streamlit dashboard
├── json_output_key.txt         # Listed main key of each JSON file
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```