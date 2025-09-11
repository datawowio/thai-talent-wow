import os
import sys
import shap
import json
import pickle
import optuna
import numpy as np
import pandas as pd
from datetime import datetime
from catboost import CatBoostRegressor, Pool
from sklearn.feature_selection import SelectFromModel
from sklearn.metrics import f1_score, recall_score, precision_score
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config

SEED = 98
np.random.seed(SEED)

def fit_model(model, X_train, y_train, X_test, y_test, score_metric, recall_threshold=0):
    categorical_features = [col for col in X_train.columns if X_train[col].dtype in ['object', 'category']] # identify categorical features
    model.fit(X_train, y_train, cat_features=categorical_features)
    y_test = y_test != 0
    threshold, metrics = find_optimal_threshold(model, X_test, y_test, score_metric, recall_threshold) # find the optimal threshold
    
    return model, threshold, metrics


def objective(trial, X_train, y_train, X_val, y_val):
    categorical_features = [col for col in X_train.columns if X_train[col].dtype in ['object', 'category']] # identify categorical features

    # define hyperparameters to tune
    param = {
        'iterations': trial.suggest_int('iterations', 100, 1000),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.5),
        'depth': trial.suggest_int('depth', 2, 8),
        'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 1e-8, 10.0, log=True),
        'bootstrap_type': trial.suggest_categorical('bootstrap_type', ['Bayesian', 'Bernoulli']),
        'random_seed': SEED
    }
    if param['bootstrap_type'] == 'Bayesian':
        param['bagging_temperature'] = trial.suggest_float('bagging_temperature', 0, 10.0)
    else:
        param['subsample'] = trial.suggest_float('subsample', 0.1, 1.0)

    # create the CatBoost model with the suggested hyperparameters
    model = CatBoostRegressor(**param)
    train_pool = Pool(X_train, y_train, cat_features=categorical_features) # create pools for proper handling of categorical features
    val_pool = Pool(X_val, y_val, cat_features=categorical_features)

    # fit the model and evaluate on the validation set
    model.fit(train_pool, eval_set=val_pool, verbose=False, early_stopping_rounds=50)
    _, metrics = find_optimal_threshold(model, X_val, y_val)

    return metrics['macro_f1']



def finetune_hyperparameter(X_train, X_test, y_train, y_test, score_metric, recall_threshold):
    # split the data into training and validation sets 
    # with the first 80% for training and the last 20% for validation
    X_train_tune = X_train.iloc[:int(0.8 * len(X_train))]
    y_train_tune = y_train.iloc[:int(0.8 * len(y_train))]
    X_val_tune = X_train.iloc[int(0.8 * len(X_train)):]
    y_val_tune = y_train.iloc[int(0.8 * len(y_train)):]

    # hyperparameter optimization
    study = optuna.create_study(direction='maximize')
    study.optimize(lambda trial: objective(trial, X_train_tune, y_train_tune, X_val_tune, y_val_tune), n_trials=100)
    
    # get best parameters
    best_params = study.best_params

    # fit the final model with best parameters on full training data
    best_model = CatBoostRegressor(**best_params, random_state=0, verbose=False)
    best_model, threshold, metrics = fit_model(best_model, X_train, y_train, X_test, y_test, score_metric, recall_threshold)
    
    return best_model, threshold, metrics


def finetune_model(train_df, test_df, score_metric='macro_f1', recall_threshold=0):
    # split train-test
    X_train, X_test, y_train, y_test = prepare_data(train_df, test_df)

    # train default model with all features
    model = CatBoostRegressor(random_state=SEED, verbose=False)
    model, _, _ = fit_model(model, X_train, y_train, X_test, y_test, score_metric, recall_threshold)
    
    # get feature importance to create feature set and re-train the model
    selector = SelectFromModel(model, prefit=True, threshold='mean')
    feature_mask = selector.get_support()
    selected_features = X_train.columns[feature_mask].tolist()
    feature_set = [
        list(set(selected_features)), # default feature importance
    ]
    # initialize variables to track the best model and metrics
    best_score_metric = -np.inf
    best_metrics = None
    best_model = None
    optimal_threshold = 0
    # iterate through the feature sets and finetune the model to find the best model
    for features in feature_set:
        X_train, X_test, y_train, y_test = prepare_data(train_df, test_df, features)
        model, threshold, metrics = finetune_hyperparameter(X_train, X_test, y_train, y_test, score_metric, recall_threshold) # re-finetune the model with selected features
        if metrics is not None and metrics[score_metric] > best_score_metric and metrics['recall'] >= recall_threshold:
            best_score_metric = metrics[score_metric] 
            best_metrics = metrics
            best_model = model
            optimal_threshold = threshold

    return best_model, optimal_threshold, best_metrics


def prepare_data(train_df, test_df, features=None):
    ### set the target column
    target_column = 'termination_value'
    drop_columns = ['emp_id', 'execution_date', target_column]

    ### set train, test features and drop columns with more than 80% missing values
    X_train = train_df.drop(columns=drop_columns)
    X_train = X_train[features] if features is not None else X_train
    y_train = train_df[target_column].reset_index(drop=True)
    missing_df = (X_train.isna().sum() / X_train.shape[0]).to_frame('percentage').sort_values('percentage', ascending=False)
    dropped_missing_columns = missing_df.query('percentage > 0.8').index.tolist()
    X_train = X_train.drop(columns=dropped_missing_columns)

    X_test = test_df.drop(columns=drop_columns)
    X_test = X_test[features] if features is not None else X_test
    y_test = test_df[target_column].reset_index(drop=True)
    X_test = X_test.drop(columns=dropped_missing_columns)

    return X_train, X_test, y_train, y_test


def train_model(feature_engineered_df):
    available_execution_dates = sorted(feature_engineered_df['execution_date'].unique().tolist())
    train_execution_dates = available_execution_dates[:-7] # use all except the last 7 months for training
    test_execution_dates = available_execution_dates[-4:-3] # use the 4-month before the last month for testing

    # filter the dataset for training and testing based on execution dates
    train_df = feature_engineered_df.query('execution_date.isin(@train_execution_dates)')
    test_df = feature_engineered_df.query('execution_date.isin(@test_execution_dates)')

    # finetune to get the best model and get the model configuration
    model, threshold, metrics = finetune_model(train_df, test_df, score_metric='macro_f1')
    model_config = {
        'features': model.feature_names_,
        'optimal_threshold': threshold,
        'training_period': [execution_date.strftime('%Y-%m-%d') for execution_date in train_execution_dates],
        'testing_period': [execution_date.strftime('%Y-%m-%d') for execution_date in test_execution_dates],
        'metrics': metrics
    }
    return model, model_config


def get_evaluation_metrics(y_true, y_pred):
    return {
        'f1': f1_score(y_true=y_true, y_pred=y_pred),
        'recall': recall_score(y_true=y_true, y_pred=y_pred),
        'precision': precision_score(y_true=y_true, y_pred=y_pred),
        'macro_f1': f1_score(y_true=y_true, y_pred=y_pred, average='macro')
    }


def find_optimal_threshold(model, X_test, y_test, score_metric='macro_f1', recall_threshold=0):
    # initialize variables to track the best score and metrics
    best_score_metric = -np.inf
    best_metrics = None
    optimal_threshold = 0
    y_true = y_test != 0
    # predict probabilities
    y_prob = model.predict(X_test)
    # iterate through a range of thresholds to find the optimal one
    for threshold in np.arange(0.001, 0.5, 0.001):
        y_pred = y_prob > threshold
        metrics = get_evaluation_metrics(y_true, y_pred)
        if metrics[score_metric] > best_score_metric and metrics['recall'] >= recall_threshold:
            best_score_metric = metrics[score_metric]
            best_metrics = metrics
            optimal_threshold = threshold
    return optimal_threshold, best_metrics


def save_model(model, model_config):
        # Save the trained model and its configuration
        model_dir = config.MODEL_OUTPUT_DIR
        os.makedirs(model_dir, exist_ok=True)
        with open(os.path.join(model_dir, 'model.pkl'), 'wb') as file:
            pickle.dump(model, file)
        with open(os.path.join(model_dir, 'model_config.json'), 'w') as file:
            json.dump(model_config, file, indent=4)


def load_model():
    model_dir = config.MODEL_OUTPUT_DIR
    # load the model from the pickle file
    with open(os.path.join(model_dir, 'model.pkl'), 'rb') as file:
        model = pickle.load(file)
    # load the model configuration from a JSON file
    with open(os.path.join(model_dir, 'model_config.json')) as file:
        model_config = json.load(file)
    # convert string dates to datetime objects
    model_config['training_period'] = [datetime.strptime(period, '%Y-%m-%d').date() for period in model_config['training_period']]
    model_config['testing_period'] = [datetime.strptime(period, '%Y-%m-%d').date() for period in model_config['testing_period']]
    return model, model_config


def predict_result(feature_engineered_df):
    # load the feature data and model
    model, model_config = load_model()
    predicted_execution_date = feature_engineered_df['execution_date'].max()
    feature_engineered_df = (feature_engineered_df.query('execution_date == @predicted_execution_date'))
    
    # predict the termination probability using the model
    y_prob = model.predict(feature_engineered_df[model_config['features']])
    y_prob = np.clip(y_prob, 0, 1) # ensure probabilities are between 0 and 1

    # get the feature importance
    feature_importance_df = pd.DataFrame({
        'feature': model.feature_names_,
        'importance': model.feature_importances_
    })
    feature_importance_df.sort_values(by='importance', ascending=False, inplace=True)

    # get the model interpretation using SHAP values
    explainer = shap.TreeExplainer(model)
    model_interpretation = {}
    for i in range(len(feature_engineered_df)):
        emp_id = feature_engineered_df.iloc[i]['emp_id']
        shap_value = explainer(feature_engineered_df.iloc[i: i+1][model_config['features']])[0]
        model_interpretation[emp_id] = shap_value

    result_df = feature_engineered_df[['emp_id']]
    result_df['termination_probability'] = y_prob
    result_df['predicted_termination'] = y_prob > model_config['optimal_threshold'] # classify as terminated if probability exceeds the threshold

    return result_df, feature_importance_df, model_interpretation


def save_model_result(prediction_df, feature_importance_df, model_interpretation):
    # Save the prediction results, feature importance, and model interpretation
    model_result_dir = config.MODEL_OUTPUT_DIR
    prediction_df.to_parquet(os.path.join(model_result_dir, 'model_result.parquet'), index=False)
    # feature_importance_df.to_parquet(os.path.join(model_result_dir, 'feature_importance.parquet'), index=False)
    with open(os.path.join(model_result_dir, 'model_interpretation.pkl'), 'wb') as file:
        pickle.dump(model_interpretation, file)