import os
import sys
import json
import pandas as pd
import numpy as np
from google.cloud import aiplatform
from google.cloud.aiplatform import Model
from google.cloud.aiplatform.prediction import LocalModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config
from skill_promotion_management.skill_gap_analysis import (
    normalize_skill, analyze_current_position_gap, 
    analyze_peer_gap, analyze_next_level_gap
)
from skill_promotion_management.promotion_analysis import promotion_analysis

class SkillGapPredictor:
    """Real-time skill gap analysis predictor"""
    
    def __init__(self):
        # Load reference data
        self._load_reference_data()
    
    def _load_reference_data(self):
        """Load and prepare reference data for predictions"""
        # Load all reference datasets
        self.skill_df = pd.read_csv(config.SKILL_DATA)
        self.normalized_skill_df = normalize_skill(self.skill_df)
        
        # Create mappings
        self.id_to_canonical_map = self.normalized_skill_df.set_index('id')['canonical_id'].to_dict()
        self.canonical_id_to_name_map = self.normalized_skill_df.drop_duplicates(
            subset=['canonical_id']
        ).set_index('canonical_id')['canonical_name'].to_dict()
        
        # Load other datasets
        self.emp_df = pd.read_csv(config.EMPLOYEE_DATA)
        self.emp_skill_df = pd.read_csv(config.EMPLOYEE_SKILL_DATA)
        self.pos_skill_df = pd.read_csv(config.POSITION_SKILL_DATA) 
        self.position_df = pd.read_csv(config.POSITION_DATA)
        self.emp_pos_df = pd.read_csv(config.EMPLOYEE_MOVEMENT_DATA)
        
        # Process employee skills
        self.emp_skill_df = self.emp_skill_df.sort_values(
            by=['employee_id', 'skill_id', 'created_at'], 
            ascending=[True, True, True]
        ).drop_duplicates(subset=['employee_id', 'skill_id'], keep='last')
        
        self.emp_skill_df['canonical_skill_id'] = self.emp_skill_df['skill_id'].map(self.id_to_canonical_map)
        self.emp_skill_df['canonical_skill_name'] = self.emp_skill_df['canonical_skill_id'].map(self.canonical_id_to_name_map)
        
        # Process position skills
        self.pos_skill_df['canonical_skill_id'] = self.pos_skill_df['skill_id'].map(self.id_to_canonical_map)
        self.pos_skill_df['canonical_skill_name'] = self.pos_skill_df['canonical_skill_id'].map(self.canonical_id_to_name_map)
        
        # Employee positions
        self.emp_pos_df = self.emp_pos_df.sort_values(
            by=['employee_id', 'effective_date'], 
            ascending=[True, True]
        ).drop_duplicates(subset=['employee_id'], keep='last')[['employee_id', 'position_id']]
    
    def predict(self, instances):
        """
        Make skill gap predictions for employees
        
        Args:
            instances: List of dictionaries with employee_id
            
        Returns:
            List of skill gap analysis results
        """
        if not isinstance(instances, list):
            instances = [instances]
        
        predictions = []
        
        for instance in instances:
            employee_id = instance['employee_id']
            
            try:
                # Get employee's current position
                current_position_id = self.emp_pos_df[
                    self.emp_pos_df['employee_id'] == employee_id
                ]['position_id'].values[0]
                
                # Analyze current position gap
                employee_skills, current_missing = analyze_current_position_gap(
                    employee_id=employee_id,
                    employee_position_id=current_position_id,
                    employee_skill_df=self.emp_skill_df,
                    position_skill_df=self.pos_skill_df,
                )
                
                # Analyze peer gap
                peer_missing = analyze_peer_gap(
                    employee_id=employee_id,
                    current_position_id=current_position_id,
                    employee_position_df=self.emp_pos_df,
                    employee_skill_df=self.emp_skill_df,
                )
                
                # Analyze next level gap
                current_pos, next_pos, next_missing = analyze_next_level_gap(
                    employee_id=employee_id,
                    current_position_id=current_position_id,
                    position_df=self.position_df,
                    position_skill_df=self.pos_skill_df,
                    employee_skill_df=self.emp_skill_df,
                )
                
                prediction = {
                    'employee_id': employee_id,
                    'current_position': current_pos,
                    'next_position': next_pos,
                    'employee_skills': employee_skills,
                    'current_missing_skills': current_missing,
                    'peer_missing_skills': peer_missing,
                    'next_missing_skills': next_missing,
                    'skill_gap_score': self._calculate_skill_gap_score(
                        current_missing, peer_missing, next_missing
                    ),
                    'readiness_score': self._calculate_readiness_score(
                        employee_skills, next_missing
                    )
                }
                
                predictions.append(prediction)
                
            except Exception as e:
                predictions.append({
                    'employee_id': employee_id,
                    'error': str(e),
                    'status': 'failed'
                })
        
        return predictions
    
    def _calculate_skill_gap_score(self, current_missing, peer_missing, next_missing):
        """Calculate overall skill gap score (0-100, lower is better)"""
        current_gap = len(current_missing) * 10
        peer_gap = len(peer_missing) * 5
        next_gap = len(next_missing) * 3
        
        total_gap = current_gap + peer_gap + next_gap
        return min(100, total_gap)
    
    def _calculate_readiness_score(self, employee_skills, next_missing):
        """Calculate promotion readiness score (0-100, higher is better)"""
        if not employee_skills:
            return 0
        
        avg_skill_score = np.mean([skill['skill_score'] for skill in employee_skills])
        skill_count_bonus = min(len(employee_skills) * 2, 20)
        gap_penalty = len(next_missing) * 5
        
        readiness = (avg_skill_score * 15) + skill_count_bonus - gap_penalty
        return max(0, min(100, readiness))

class PromotionPredictor:
    """Real-time promotion readiness predictor"""
    
    def __init__(self):
        self._load_reference_data()
    
    def _load_reference_data(self):
        """Load reference data for promotion analysis"""
        self.emp_df = pd.read_csv(config.EMPLOYEE_DATA)
        self.movement_df = pd.read_csv(config.EMPLOYEE_MOVEMENT_DATA)
        self.evaluation_df = pd.read_csv(config.EVALUATION_RECORD_DATA)
        self.position_df = pd.read_csv(config.POSITION_DATA)
        
        # Process dates
        self.movement_df['effective_date'] = pd.to_datetime(
            self.movement_df['effective_date'], errors='coerce'
        )
        self.evaluation_df['evaluation_date'] = pd.to_datetime(
            self.evaluation_df['evaluation_date'], errors='coerce'
        )
        
        self.emp_pos_df = self.movement_df.sort_values(
            by=['employee_id', 'effective_date'], ascending=[True, True]
        ).drop_duplicates(subset=['employee_id'], keep='last')[['employee_id', 'position_id']]
    
    def predict(self, instances):
        """Predict promotion readiness for employees"""
        if not isinstance(instances, list):
            instances = [instances]
        
        predictions = []
        
        for instance in instances:
            employee_id = instance['employee_id']
            
            try:
                # Get employee evaluation history
                emp_evaluations = self.evaluation_df[
                    self.evaluation_df['employee_id'] == employee_id
                ].sort_values('evaluation_date')
                
                if emp_evaluations.empty:
                    category = 'Unknown'
                    score = 0
                else:
                    # Simple promotion readiness logic
                    recent_score = emp_evaluations.iloc[-1]['overall_score']
                    evaluation_trend = self._calculate_trend(emp_evaluations['overall_score'].tolist())
                    
                    if recent_score >= 4.5 and evaluation_trend >= 0:
                        category = 'On Track'
                        score = 85 + (recent_score - 4.5) * 30
                    elif recent_score >= 4.0 and evaluation_trend >= 0:
                        category = 'Overlooked Talent'
                        score = 70 + (recent_score - 4.0) * 30
                    elif recent_score >= 3.5 and evaluation_trend < 0:
                        category = 'Disengaged Employee'  
                        score = 40 + (recent_score - 3.5) * 20
                    else:
                        category = 'New and Promising'
                        score = 50 + evaluation_trend * 20
                
                prediction = {
                    'employee_id': employee_id,
                    'promotion_category': category,
                    'promotion_score': min(100, max(0, score)),
                    'recent_evaluation_score': float(emp_evaluations.iloc[-1]['overall_score']) if not emp_evaluations.empty else 0,
                    'evaluation_trend': evaluation_trend
                }
                
                predictions.append(prediction)
                
            except Exception as e:
                predictions.append({
                    'employee_id': employee_id,
                    'error': str(e),
                    'status': 'failed'
                })
        
        return predictions
    
    def _calculate_trend(self, scores):
        """Calculate score trend over time"""
        if len(scores) < 2:
            return 0
        return (scores[-1] - scores[0]) / len(scores)

class VertexAISkillModel:
    """Wrapper for deploying skill models to Vertex AI"""
    
    def __init__(self, project_id, region="asia-southeast1"):
        aiplatform.init(project=project_id, location=region)
        self.project_id = project_id
        self.region = region
    
    def create_skill_gap_model(self, model_display_name="skill-gap-predictor"):
        """Create skill gap analysis model"""
        local_model = LocalModel.build_cpr_model(
            "vertex_ai/skill_predictor.py",
            "SkillGapPredictor",
            requirements=["pandas", "numpy", "sentence-transformers"]
        )
        
        return local_model.upload(
            display_name=model_display_name,
            description="Real-time skill gap analysis"
        )
    
    def create_promotion_model(self, model_display_name="promotion-predictor"):
        """Create promotion readiness model"""
        local_model = LocalModel.build_cpr_model(
            "vertex_ai/skill_predictor.py", 
            "PromotionPredictor",
            requirements=["pandas", "numpy"]
        )
        
        return local_model.upload(
            display_name=model_display_name,
            description="Real-time promotion readiness analysis"
        )

# Example usage
if __name__ == "__main__":
    # Test skill gap predictor
    skill_predictor = SkillGapPredictor()
    skill_result = skill_predictor.predict([{'employee_id': 'EMP001'}])
    print("Skill Gap:", json.dumps(skill_result, indent=2))
    
    # Test promotion predictor
    promotion_predictor = PromotionPredictor()
    promotion_result = promotion_predictor.predict([{'employee_id': 'EMP001'}])
    print("Promotion:", json.dumps(promotion_result, indent=2))