# th.ai-talent-wow

This repository right now contains two main analytics modules:
1. **Predictive Retention Analysis** – to predict employee termination probability.
2. **Skill Gap Analysis** – to assess and visualize skill gaps across employees and departments.

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
  ```
  predictive_retention/experimental_visualization.ipynb
  ```
- JSON output of the prediction results is stored at:
  ```
  output/termination_result.json
  ```

### Interactive Overview (Streamlit)
To view an interactive dashboard of the analysis:
```bash
streamlit run predictive_retention/streamlit.py
```

---

## 2. Skill Gap Analysis
### Running the Analysis
To run the skill gap analysis:

```bash
python skill_management/main.py
```

### Interactive Overview (Streamlit)
To view the skill gap analysis dashboard:

```bash
streamlit run skill_management/streamlit.py
```