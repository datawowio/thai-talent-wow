import os
import sys
import json
import pandas as pd
import logging
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from predictive_retention.feature_engineering import feature_engineering
from predictive_retention.model import train_model, save_model, predict_result, save_model_result
from predictive_retention.termination_analysis import generate_termination_analysis
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    start_time = datetime.now()
    logger.info("=== TH.AI Retention ML Pipeline Started ===")
    logger.info(f"Pipeline start time: {start_time}")

    try:
        # 1. Feature Engineering
        logger.info("Step 1/6: Starting feature engineering...")
        feature_engineered_df = feature_engineering()
        logger.info(f"Feature engineering completed. Dataset shape: {feature_engineered_df.shape}")
        # feature_engineered_df = pd.read_csv(config.FEATURE_ENGINEERED_PATH)
        # feature_engineered_df['execution_date'] = pd.to_datetime(feature_engineered_df['execution_date'])

        # 2. Train Model
        logger.info("Step 2/6: Starting model training...")
        model, model_config = train_model(feature_engineered_df)
        logger.info("Model training completed successfully")

        # 3. Save Model
        logger.info("Step 3/6: Saving trained model...")
        save_model(model, model_config)
        logger.info("Model saved successfully")

        # 4. Predict Result
        logger.info("Step 4/6: Generating predictions...")
        prediction_df, feature_importance_df, model_interpretation = predict_result(feature_engineered_df)
        logger.info(f"Predictions completed. Generated {len(prediction_df)} predictions")

        # 5. Save Model Result
        logger.info("Step 5/6: Saving model results...")
        save_model_result(prediction_df, feature_importance_df, model_interpretation)
        logger.info("Model results saved successfully")

        # 6. Generate and Save Visualization JSON
        logger.info("Step 6/6: Generating termination analysis...")
        visualization_json = generate_termination_analysis(model_config, model_interpretation, prediction_df)
        with open(config.TERMINATION_ANALYSIS_OUTPUT, 'w') as f:
            json.dump(visualization_json, f, indent=4)
        logger.info(f"Termination analysis saved to {config.TERMINATION_ANALYSIS_OUTPUT}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info("=== TH.AI Retention ML Pipeline Completed Successfully ===")
        logger.info(f"Total pipeline execution time: {duration:.2f} seconds")

    except Exception as e:
        logger.error(f"Pipeline failed with error: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()
