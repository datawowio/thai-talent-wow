# th.ai-talent-wow

This repository right now contains two main analytics modules:
1. **Predictive Retention Analysis** – to predict employee termination probability.
2. **Skill Gap Analysis** – to assess and visualize skill gaps across employees and departments.
3. **Promotion Analysis** - to add a career progression dimension for each employees.

## Requirements
- Python 3.12+
- Install dependencies before running:
```bash
pip install -r requirements.txt
```

## 1. Predictive Retention Analysis
### Training the Model
To train the predictive retention analysis model, run:
```bash
python predictive_retention/main.py
```

### Experimental Visualizations & Results
- You can explore result storage and plotting methods in:
  ```predictive_retention/experimental_visualization.ipynb```
- JSON output of the prediction results is stored at:
  ```output/termination_result.json```

---

## 2. Skill Gap Analysis
### Running the Analysis
To run the skill gap analysis:
```bash
python skill_management/main.py
```

### Results
- JSON output of the **Employee* skill gap analysis is stored at:
  ```output/employee_skill_gap_result.json```
- JSON output of the **Department* skill gap analysis is stored at:
  ```output/department_skill_gap_result.json```

---

## 3. Promotion Analysis
### Running the Analysis
To run the promotion analysis:
```bash
python promotion_analysis/main.py
```

### Results
- JSON output of the promotion analysis is stored at:
  ```output/promotion_analysis_results.json```

---

## 4. Example dashboard 
For view the example dashboard and how each variable can be visualize, run:
```bash
streamlit run all_streamlit.py
```