import pandas as pd
import time
from collections import defaultdict
from itertools import combinations
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players

# Processes game logs into shared minutes matrix
def get_shared_mins_df(team_ids):
    team_players = []
    for id in team_ids:
        try:
            player = players.find_wnba_player_by_id(id)
            gamelog = playergamelog.PlayerGameLog(
                player_id=id,
                season='2025',
                season_type_all_star='Regular Season',
                league_id_nullable='10'
            ).get_data_frames()[0]
        
            if not gamelog.empty:
                 gamelog.insert(1, 'Full_Name', player['full_name'])  # Fixed: use full_name
                 team_players.append(gamelog)
            time.sleep(1)
        except Exception as e:
            print(f"Error processing player {id}: {e}")
            continue
            
    if not team_players:
        return pd.DataFrame()
        
    all_logs = pd.concat(team_players, ignore_index=True)
    games = all_logs['GAME_DATE'].unique()
    shared_minutes = defaultdict(lambda: defaultdict(float))

    # shared minutes matrix
    for game in games:
        game_data = all_logs[all_logs['GAME_DATE'] == game]
        for player1, player2 in combinations(game_data['Full_Name'], 2):
            min1_data = game_data[game_data['Full_Name'] == player1]['MIN'].values
            min2_data = game_data[game_data['Full_Name'] == player2]['MIN'].values
            if len(min1_data) > 0 and len(min2_data) > 0:
                min1 = min1_data[0]
                min2 = min2_data[0]
                if isinstance(min1, str):
                    min1 = float(min1.split(':')[0]) + float(min1.split(':')[1])/60
                if isinstance(min2, str):
                    min2 = float(min2.split(':')[0]) + float(min2.split(':')[1])/60
                shared = min(min1, min2)
                shared_minutes[player1][player2] += shared
                shared_minutes[player2][player1] += shared

    shared_mins_df = pd.DataFrame(shared_minutes).fillna(0)
    return shared_mins_df

# Uses get_shared_mins_df to find top teammates
def on_court_teammates(player_id):
    from src.data.api_client import get_team_ids_from_player_id, get_player_name
    
    team_player_ids = get_team_ids_from_player_id(player_id, ignore_id=player_id)
    if not team_player_ids:
        return []
        
    shared_minutes_df = get_shared_mins_df(team_player_ids + [player_id])
    
    player_name = get_player_name(player_id)
    if player_name not in shared_minutes_df.columns:
        return []
        
    co_players = shared_minutes_df[player_name].sort_values(ascending=False).head(4).index.tolist()
    
    # Convert names back to IDs
    teammate_ids = []
    for name in co_players:
        try:
            player_data = players.find_wnba_players_by_full_name(name)
            if player_data:
                teammate_ids.append(player_data[0]['id'])
        except:
            continue
    
    return teammate_ids

def normalize_position(pos):
    if not pos: 
        return 'F'
    if 'G' in pos:
        return 'G'
    elif 'C' in pos:
        return 'C'
    else:
        return 'F'