from nba_api.stats.endpoints import LeagueDashTeamStats, commonteamroster, commonplayerinfo
from nba_api.stats.static import players
import time

# NBA API interaction functions

def get_position(player_id):
    try:
        df = commonplayerinfo.CommonPlayerInfo(
            player_id=player_id,
            league_id_nullable='10'  # WNBA
        ).get_data_frames()[0]
        time.sleep(1)
        return df['POSITION'].iloc[0]
    except:
        return None

def parse_height(height_str):
    if not height_str or '-' not in height_str:
        return 72  # default 6'0" if unknown
    feet, inches = map(int, height_str.split('-'))
    return feet * 12 + inches
        
def get_player_height_and_position(pid):
    try:
        df = commonplayerinfo.CommonPlayerInfo(player_id=pid, league_id_nullable='10').get_data_frames()[0]
        height = parse_height(df['HEIGHT'].iloc[0])
        position = df['POSITION'].iloc[0]
        time.sleep(1)
        return height, position
    except:
        return 72, 'G'  # Default values
        
def team_lookup(team_id):
    return commonteamroster.CommonTeamRoster(
        team_id=team_id,
        season='2025',
        league_id_nullable='10'
    )

def player_id_to_name(id):
    time.sleep(1)
    return players.find_wnba_player_by_id(id)['full_name']

def get_player_name(player_id):
    time.sleep(1)
    player = players.find_wnba_player_by_id(player_id)
    return player['full_name'] if player is not None else "Empty"

def get_team_ids_from_player_id(id, ignore_id=None):
    player_stats = commonplayerinfo.CommonPlayerInfo(
         player_id=id,
         league_id_nullable='10'
    ).get_data_frames()[0]
    team_id = player_stats['TEAM_ID'].iloc[0]
    roster_team_df = team_lookup(team_id).get_data_frames()[0]
    team_player_ids = roster_team_df['PLAYER_ID'].tolist()
    if ignore_id and ignore_id in team_player_ids:
        team_player_ids.remove(ignore_id)
    return team_player_ids

def get_team_id_from_player_id(id):
    player_stats = commonplayerinfo.CommonPlayerInfo(
         player_id=id,
         league_id_nullable='10'
    ).get_data_frames()[0]
    return player_stats['TEAM_ID'].iloc[0]

# API data fetching
def calculate_team_possessions(home_id, opp_id):
    common_params = {
        'season': '2024', 
        'season_type_all_star': 'Regular Season',
        'league_id_nullable': '10',  # '10' = WNBA
        'per_mode_detailed': 'PerGame',
        'measure_type_detailed_defense': 'Base',
        'last_n_games': 10,
        'pace_adjust': 'N',
        'plus_minus': 'N',
        'rank': 'N',
        'month': 0,
        'period': 0 
    }
    hts = LeagueDashTeamStats( 
        **common_params,
        opponent_team_id=opp_id
    ).get_data_frames()[0]
    filt_hts = hts[hts['TEAM_ID'] == home_id]
    ots = LeagueDashTeamStats( 
        **common_params,
        opponent_team_id=home_id
    ).get_data_frames()[0]
    filt_ots = ots[ots['TEAM_ID'] == opp_id]

    team_possession = 0.5 * (
    (filt_hts['FGA'].iloc[0] + 0.44 * filt_hts['FTA'].iloc[0] - filt_hts['OREB'].iloc[0] + filt_hts['TOV'].iloc[0]) +
    (filt_ots['FGA'].iloc[0] + 0.44 * filt_ots['FTA'].iloc[0] - filt_ots['OREB'].iloc[0] + filt_ots['TOV'].iloc[0]))
    return team_possession