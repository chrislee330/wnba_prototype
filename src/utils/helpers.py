from datetime import datetime
from nba_api.stats.static import players
import pandas as pd
import numpy as np
import os

# Fixed imports
from src.model.matchup_analyzer import get_primary_defender_matchup
from src.model.monte_carlo import run_monte_carlo_sim
from src.utils.constants import TARGETPLAYERS, TARGETPLAYERS_FLAT, TEAM1, TEAM2, get_team_rosters, get_player_team_assignment

# File management and output

def create_output_folder():
    # Create timestamped folder name
    today_str = datetime.today().strftime('%Y-%m-%d')
    folder_name = f"{TEAM1.lower()}_vs_{TEAM2.lower()}_{today_str}"
    output_folder = os.path.join('sim_results', folder_name)
    os.makedirs(output_folder, exist_ok=True)
    return output_folder

def save_simulation_results():
    """Run simulations for all target players and save results"""
    # Get team rosters
    TEAM1PLAYERIDS, TEAM2PLAYERIDS, TEAM1ID, TEAM2ID = get_team_rosters()
    
    # Create output folder
    output_folder = create_output_folder()
    
    for player_name in TARGETPLAYERS_FLAT:
        output_file = os.path.join(output_folder, f"{player_name.replace(' ', '_').lower()}_sim.csv")

        # Skip if already exists
        if os.path.exists(output_file):
            print(f"Skipping {player_name}, already simulated.")
            continue

        try:
            player_data = players.find_wnba_players_by_full_name(player_name)
            if not player_data:
                print(f"Player not found: {player_name}")
                continue
                
            player_id = player_data[0]['id']
            print(f"\nRunning simulation for {player_name} (ID: {player_id})")

            # Determine which team the player belongs to
            player_team = get_player_team_assignment(player_name)
            
            if player_team == 'TEAM1':
                # Player is on Team 1, so Team 1 is home, Team 2 is opponent
                home_team_ids = TEAM1PLAYERIDS
                opp_team_ids = TEAM2PLAYERIDS
            elif player_team == 'TEAM2':
                # Player is on Team 2, so Team 2 is home, Team 1 is opponent
                home_team_ids = TEAM2PLAYERIDS
                opp_team_ids = TEAM1PLAYERIDS
            else:
                print(f"Could not determine team for {player_name}, skipping...")
                continue

            player_sim_data = get_primary_defender_matchup(home_team_ids, opp_team_ids, player_id)

            # Clamp std dev
            max_pts_std = player_sim_data['est_fga'] * 1.5
            player_sim_data['rolling_std']['PTS'] = min(player_sim_data['rolling_std']['PTS'], max_pts_std)

            # Simulate
            df_sim = run_monte_carlo_sim(player_sim_data, n_simulations=20000)
            df_sim['PLAYER'] = player_name
            df_sim['TEAM'] = TEAM1 if player_team == 'TEAM1' else TEAM2

            # Save immediately
            df_sim.to_csv(output_file, index=False)
            print(f"Saved: {output_file}")

        except Exception as e:
            print(f"Error simulating {player_name}: {e}")
    
    return output_folder

def combine_player_csvs(output_folder):
    """Combine all player CSVs into one file"""
    combined_df = pd.DataFrame()
    
    for fname in os.listdir(output_folder):
        if fname.endswith('_sim.csv') and 'combined' not in fname:
            df = pd.read_csv(os.path.join(output_folder, fname))
            combined_df = pd.concat([combined_df, df], ignore_index=True)

    if not combined_df.empty:
        final_output = os.path.join(output_folder, f"{TEAM1.lower()}_vs_{TEAM2.lower()}_combined_simulations.csv")
        combined_df.to_csv(final_output, index=False)
        print(f"All player simulations combined to: {final_output}")
        return final_output
    else:
        print("No simulation files found to combine")
        return None

def analyze_simulation_results(team_1=None, team_2=None, date_str=None):
    """Analyze and summarize simulation results from CSV files"""
    
    # Use current teams and date if not specified
    if not team_1:
        team_1 = TEAM1  
    if not team_2:
        team_2 = TEAM2  
    if not date_str:
        date_str = datetime.today().strftime('%Y-%m-%d')
    
    # Build path to combined results
    folder_name = f"{team_1.lower()}_vs_{team_2.lower()}_{date_str}"
    output_folder = os.path.join('sim_results', folder_name)
    combined_path = os.path.join(output_folder, f"{team_1.lower()}_vs_{team_2.lower()}_combined_simulations.csv")
    
    try:
        # Load CSV
        df_combined = pd.read_csv(combined_path)
        print(f"Loaded simulation results from: {combined_path}")
        print(f"Total simulations: {len(df_combined)} rows")
        print(f"Players analyzed: {df_combined['PLAYER'].unique().tolist()}")
        
        # Show by team if TEAM column exists
        if 'TEAM' in df_combined.columns:
            print("Players by team:")
            for team in df_combined['TEAM'].unique():
                team_players = df_combined[df_combined['TEAM'] == team]['PLAYER'].unique().tolist()
                print(f"  {team}: {team_players}")
        
        print("\n" + "="*60)
        
        # View summary stats
        summary_df = df_combined.groupby('PLAYER')[['PTS', 'REB', 'AST']].agg(['mean', 'std', 'min', 'max', 'median'])
        print("SIMULATION SUMMARY STATISTICS")
        print("="*60)
        print(summary_df.round(2))
        
        # Additional percentile analysis
        print("\n" + "="*60)
        print("PERCENTILE ANALYSIS (25th, 75th, 90th)")
        print("="*60)
        percentile_df = df_combined.groupby('PLAYER')[['PTS', 'REB', 'AST']].quantile([0.25, 0.75, 0.9]).round(2)
        print(percentile_df)
        
        return df_combined, summary_df
        
    except FileNotFoundError:
        print(f"Error: Could not find simulation results at {combined_path}")
        return None, None
    except Exception as e:
        print(f"Error analyzing results: {e}")
        return None, None

def run_full_simulation():
    """Main function to run the complete simulation process"""
    print("Starting WNBA player simulation...")
    print(f"Simulating players from both {TEAM1} and {TEAM2}")
    
    # Run simulations for all players
    output_folder = save_simulation_results()
    
    # Combine all results
    combined_file = combine_player_csvs(output_folder)
    
    if combined_file:
        print(f"\nSimulation complete! Results saved in: {output_folder}")
        print(f"Combined results: {combined_file}")
        
    else:
        print("\nSimulation completed but no results to combine")
    
    return output_folder

def create_actual_results_template(team_1, team_2, date_str=None):
    """Create a CSV template for entering actual game results"""
    
    if not date_str:
        date_str = datetime.today().strftime('%Y-%m-%d')
    
    template_df = pd.DataFrame({
        'PLAYER': TARGETPLAYERS_FLAT,
        'TEAM': [TEAM1 if get_player_team_assignment(player) == 'TEAM1' else TEAM2 for player in TARGETPLAYERS_FLAT],
        'ACTUAL_PTS': [0.0] * len(TARGETPLAYERS_FLAT),
        'ACTUAL_REB': [0.0] * len(TARGETPLAYERS_FLAT),
        'ACTUAL_AST': [0.0] * len(TARGETPLAYERS_FLAT)
    })
    
    folder_name = f"{team_1.lower()}_vs_{team_2.lower()}_{date_str}"
    output_folder = os.path.join('sim_results', folder_name)
    template_path = os.path.join(output_folder, "actual_results_template.csv")
    
    os.makedirs(output_folder, exist_ok=True)
    template_df.to_csv(template_path, index=False)
    print(f"Actual results template created: {template_path}")
    
    return template_path