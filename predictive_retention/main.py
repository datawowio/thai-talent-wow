import os
import sys
import json
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from  feature_engineering import feature_engineering
from model import train_model, save_model, predict_result, save_model_result
from termination_visualization import generate_termination_visualizations
from config import config

def main():
    # 1. Feature Engineering
    print("Starting feature engineering...")
    feature_engineered_df = feature_engineering()
    # feature_engineered_df = pd.read_csv(config.FEATURE_ENGINEERED_PATH)
    # feature_engineered_df['execution_date'] = pd.to_datetime(feature_engineered_df['execution_date'])

    # 2. Train Model
    print("Starting model training...")
    model, model_config = train_model(feature_engineered_df)

    # 3. Save Model
    print("Saving model...")
    save_model(model, model_config)

    # 4. Predict Result
    print("Starting prediction...")
    prediction_df, feature_importance_df, model_interpretation = predict_result(feature_engineered_df)

    # 5. Save Model Result
    print("Saving prediction results...")
    save_model_result(prediction_df, feature_importance_df, model_interpretation)

    # 6. Generate and Save Visualization JSON
    print("Generating JSON result...")
    visualization_json = generate_termination_visualizations(model_config, model_interpretation, prediction_df)
    with open(config.TERMINATION_ANALYSIS_OUTPUT, 'w') as f:
        json.dump(visualization_json, f, indent=4)
    
if __name__ == "__main__":
    main()
