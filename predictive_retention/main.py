
import config
from  feature_engineering import feature_engineering
from model import train_model, save_model, predict_result, save_model_result

def main():
    file_paths = [
        config.EMPLOYEE_DATA,
        config.MANAGER_LOG_DATA,
        config.EMPLOYEE_SKILL_DATA,
        config.EMPLOYEE_POSITION_DATA,
        # config.SKILL_DATA,
        config.POSITION_DATA,
        # config.DEPARTMENT_DATA,
        config.POSITION_SKILL_DATA,
        config.SALARY_DATA,
        config.EMPLOYEE_MOVEMENT_DATA,
        config.ENGAGEMENT_DATA,
        config.LEAVE_DATA,
        config.EVALUATION_RECORD_DATA,
        config.CLOCK_IN_OUT_DATA
    ]

    # 1. Feature Engineering
    print("Starting feature engineering...")
    feature_engineered_df = feature_engineering(file_paths)

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

if __name__ == "__main__":
    main()
