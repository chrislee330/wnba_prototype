import pandas as pd
import numpy as np
from datetime import datetime
import os

from src.utils.constants import TEAM1, TEAM2
class ModelEvaluator:
    """
    Evaluates Monte Carlo simulation model performance against actual game results
    """
    
    def __init__(self):
        self.metrics = {}
        
    def load_predictions(self, team_1, team_2, date_str=None):
        """Load simulation predictions from CSV"""
        if not date_str:
            date_str = datetime.today().strftime('%Y-%m-%d')
        
        folder_name = f"{team_1.lower()}_vs_{team_2.lower()}_{date_str}"
        print(folder_name)
        output_folder = os.path.join('sim_results', folder_name)
        combined_path = os.path.join(output_folder, f"{team_1.lower()}_vs_{team_2.lower()}_combined_simulations.csv")
        
        try:
            df = pd.read_csv(combined_path)
            # Calculate prediction statistics
            predictions = df.groupby('PLAYER')[['PTS', 'REB', 'AST']].agg({
                'PTS': ['mean', 'std', 'median'],
                'REB': ['mean', 'std', 'median'], 
                'AST': ['mean', 'std', 'median']
            }).round(2)
            
            # Flatten column names
            predictions.columns = [f"{stat}_{agg}" for stat, agg in predictions.columns]
            return predictions.reset_index()
            
        except FileNotFoundError:
            print(f"Prediction file not found: {combined_path}")
            return None
    
    def input_actual_results(self, predictions_df):
        """
        Manually input actual game results
        Returns a dataframe with actual stats
        """
        actual_results = []
        
        print("Enter actual game results for each player:")
        
        for player in predictions_df['PLAYER'].unique():
            print(f"\nPlayer: {player}")
            print(f"Predicted - PTS: {predictions_df[predictions_df['PLAYER']==player]['PTS_mean'].iloc[0]:.1f}, "
                  f"REB: {predictions_df[predictions_df['PLAYER']==player]['REB_mean'].iloc[0]:.1f}, "
                  f"AST: {predictions_df[predictions_df['PLAYER']==player]['AST_mean'].iloc[0]:.1f}")
            
            try:
                actual_pts = float(input(f"Actual Points for {player}: "))
                actual_reb = float(input(f"Actual Rebounds for {player}: "))
                actual_ast = float(input(f"Actual Assists for {player}: "))
                
                actual_results.append({
                    'PLAYER': player,
                    'ACTUAL_PTS': actual_pts,
                    'ACTUAL_REB': actual_reb,
                    'ACTUAL_AST': actual_ast
                })
            except ValueError:
                print(f"Invalid input for {player}, skipping")
                continue
        
        return pd.DataFrame(actual_results)
    
    def load_actual_from_csv(self, csv_path):
        """
        Load actual results from a CSV file
        """
        try:
            actual_df = pd.read_csv(csv_path)
            required_cols = ['PLAYER', 'ACTUAL_PTS', 'ACTUAL_REB', 'ACTUAL_AST']
            
            if not all(col in actual_df.columns for col in required_cols):
                raise ValueError(f"CSV must contain columns: {required_cols}")
                
            return actual_df
        except Exception as e:
            print(f"Error loading actual results: {e}")
            return None
    
    def calculate_accuracy_metrics(self, predictions_df, actual_df):
        # Merge predictions with actuals
        merged_df = predictions_df.merge(actual_df, on='PLAYER', how='inner')
        
        if merged_df.empty:
            print("No matching players found between predictions and actuals")
            return None
        
        stats = ['PTS', 'REB', 'AST']
        results = {'PLAYER': [], 'STAT': [], 'PREDICTED': [], 'ACTUAL': [], 
                  'ERROR': [], 'ABS_ERROR': [], 'PCT_ERROR': [], 'Z_SCORE': [], 'IN_CONFIDENCE_INTERVAL': []}
        
        for _, row in merged_df.iterrows():
            player = row['PLAYER']
            
            for stat in stats:
                predicted_mean = row[f'{stat}_mean']
                predicted_std = row[f'{stat}_std']
                actual_value = row[f'ACTUAL_{stat}']
                
                # Calculate metrics
                error = actual_value - predicted_mean
                abs_error = abs(error)
                pct_error = (abs_error / max(actual_value, 0.1)) * 100  # Avoid division by zero
                
                # Z-score
                z_score = error / max(predicted_std, 0.1) if predicted_std > 0 else 0
                
                # Check if actual falls within 1 standard deviation (68% confidence interval)
                in_ci = abs(z_score) <= 1.0
                
                results['PLAYER'].append(player)
                results['STAT'].append(stat)
                results['PREDICTED'].append(predicted_mean)
                results['ACTUAL'].append(actual_value)
                results['ERROR'].append(error)
                results['ABS_ERROR'].append(abs_error)
                results['PCT_ERROR'].append(pct_error)
                results['Z_SCORE'].append(z_score)
                results['IN_CONFIDENCE_INTERVAL'].append(in_ci)
        
        results_df = pd.DataFrame(results)
        
        # Calculate summary metrics
        summary_metrics = {
            'Mean Absolute Error (MAE)': results_df.groupby('STAT')['ABS_ERROR'].mean(),
            'Mean Percentage Error (MAPE)': results_df.groupby('STAT')['PCT_ERROR'].mean(),
            'Root Mean Square Error (RMSE)': results_df.groupby('STAT').apply(lambda x: np.sqrt((x['ERROR']**2).mean())),
            'Confidence Interval Accuracy': results_df.groupby('STAT')['IN_CONFIDENCE_INTERVAL'].mean() * 100,
            'Mean Z-Score': results_df.groupby('STAT')['Z_SCORE'].mean().abs()
        }
        
        return results_df, summary_metrics
    
    def generate_evaluation_report(self, results_df, summary_metrics, save_path=None):
        """
        Generate a comprehensive evaluation report
        """
        report = []
        report.append("=" * 60)
        report.append("MODEL EVALUATION REPORT")
        report.append("=" * 60)
        report.append(f"Evaluation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Players Evaluated: {results_df['PLAYER'].nunique()}")
        report.append("")
        
        # Individual player results
        report.append("INDIVIDUAL PLAYER RESULTS:")
        report.append("-" * 40)
        for player in results_df['PLAYER'].unique():
            player_data = results_df[results_df['PLAYER'] == player]
            report.append(f"\n{player}:")
            for _, row in player_data.iterrows():
                report.append(f"  {row['STAT']}: Predicted {row['PREDICTED']:.1f}, "
                             f"Actual {row['ACTUAL']:.1f}, Error {row['ERROR']:+.1f} "
                             f"({row['PCT_ERROR']:.1f}% error)")
        
        report.append("\n" + "=" * 60)
        report.append("OVERALL MODEL PERFORMANCE:")
        report.append("=" * 60)
        
        for metric_name, metric_values in summary_metrics.items():
            report.append(f"\n{metric_name}:")
            for stat in ['PTS', 'REB', 'AST']:
                if stat in metric_values:
                    value = metric_values[stat]
                    if 'Percentage' in metric_name or 'Accuracy' in metric_name:
                        report.append(f"  {stat}: {value:.1f}%")
                    else:
                        report.append(f"  {stat}: {value:.2f}")
        
        # Model grading
        report.append("\n" + "=" * 60)
        report.append("MODEL GRADE:")
        report.append("=" * 60)
        
        # Calculate overall grade based on MAPE and CI accuracy
        avg_mape = summary_metrics['Mean Percentage Error (MAPE)'].mean()
        avg_ci_accuracy = summary_metrics['Confidence Interval Accuracy'].mean()
        
        if avg_mape <= 15 and avg_ci_accuracy >= 70:
            grade = "A (Excellent)"
        elif avg_mape <= 25 and avg_ci_accuracy >= 60:
            grade = "B (Good)"
        elif avg_mape <= 35 and avg_ci_accuracy >= 50:
            grade = "C (Fair)"
        elif avg_mape <= 50 and avg_ci_accuracy >= 40:
            grade = "D (Poor)"
        else:
            grade = "F (Very Poor)"
        
        report.append(f"Overall Model Grade: {grade}")
        report.append(f"Average MAPE: {avg_mape:.1f}%")
        report.append(f"Average CI Accuracy: {avg_ci_accuracy:.1f}%")
        
        report_text = "\n".join(report)
        print(report_text)
        
        if save_path:
            with open(save_path, 'w') as f:
                f.write(report_text)
            print(f"\nReport saved to: {save_path}")
        
        return report_text
    
    def evaluate_model(self, team_1, team_2, date_str=None, 
                      actual_csv_path=None, save_report=True):
        """
        Complete model evaluation workflow
        """
        print("Starting Model Evaluation...")
        
        # Load predictions
        predictions_df = self.load_predictions(team_1, team_2, date_str)
        if predictions_df is None:
            return None
        
        # Load actual results
        if actual_csv_path:
            actual_df = self.load_actual_from_csv(actual_csv_path)
        else:
            actual_df = self.input_actual_results(predictions_df)
        
        if actual_df is None or actual_df.empty:
            print("No actual results provided")
            return None
        
        # Calculate metrics
        results_df, summary_metrics = self.calculate_accuracy_metrics(predictions_df, actual_df)
        
        if results_df is None:
            return None
        
        # Generate report
        if save_report:
            if not date_str:
                date_str = datetime.today().strftime('%Y-%m-%d')
            folder_name = f"{team_1.lower()}_vs_{team_2.lower()}_{date_str}"
            output_folder = os.path.join('sim_results', folder_name)
            report_path = os.path.join(output_folder, f"model_evaluation_report_{date_str}.txt")
        else:
            report_path = None
        
        report = self.generate_evaluation_report(results_df, summary_metrics, report_path)
        
        return {
            'results_df': results_df,
            'summary_metrics': summary_metrics,
            'report': report,
            'predictions_df': predictions_df,
            'actual_df': actual_df
        }