from nba_api.stats.static import teams

TEAM1 = "Lynx"
TEAM2 = "Mercury"

IGNORE = None

# Updated to specify which team each player belongs to
TARGETPLAYERS = {
    'TEAM1': [  
        'Bridget Carleton', 
        'Alanna Smith', 
        'Napheesa Collier'
    ],
    'TEAM2': [  
        'Alyssa Thomas',
        'Kahleah Copper', 
        'Satou Sabally'
    ]
}

# For backward compatibility, create a flat list
TARGETPLAYERS_FLAT = TARGETPLAYERS['TEAM1'] + TARGETPLAYERS['TEAM2']

def get_team_rosters():
    from src.data.api_client import team_lookup
    
    TEAM1ID = teams.find_wnba_teams_by_nickname(TEAM1)[0]['id']
    TEAM2ID = teams.find_wnba_teams_by_nickname(TEAM2)[0]['id']

    ROSTERTEAM1DF = team_lookup(TEAM1ID).get_data_frames()[0]
    ROSTERTEAM2DF = team_lookup(TEAM2ID).get_data_frames()[0]
    
    TEAM1PLAYERIDS = ROSTERTEAM1DF['PLAYER_ID'].tolist()
    TEAM2PLAYERIDS = ROSTERTEAM2DF['PLAYER_ID'].tolist()
    
    return TEAM1PLAYERIDS, TEAM2PLAYERIDS, TEAM1ID, TEAM2ID

def get_player_team_assignment(player_name):
    """Determine which team a player belongs to"""
    if player_name in TARGETPLAYERS['TEAM1']:
        return 'TEAM1'
    elif player_name in TARGETPLAYERS['TEAM2']:
        return 'TEAM2'
    else:
        return None

SIMULATION_DEFAULTS = {
    'n_simulations': 20000,
    'season': '2025',
    'recent_games': 10
}

ROLLINGLEAGUE_EFG = 0.52  # Approximate WNBA league average

COMMON_PARAMS = {
    'season': '2025',
    'season_type_all_star': 'Regular Season',
    'league_id_nullable': '10',  # '10' = WNBA
    'per_mode_detailed': 'PerGame',
    'measure_type_detailed_defense': 'Advanced',
    'last_n_games': 10,
    'pace_adjust': 'N',
    'plus_minus': 'N',
    'rank': 'N',
    'month': 0,
    'period': 0
}