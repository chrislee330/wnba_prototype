from nba_api.stats.endpoints import LeagueDashTeamStats
import pandas as pd
from nba_api.stats.endpoints import playergamelog, commonteamroster, commonplayerinfo
from nba_api.stats.static import players, teams
import time
from itertools import combinations
from collections import defaultdict
import numpy as np

def team_lookup(id):
    return commonteamroster.CommonTeamRoster(
            team_id=id,
            season='2025',
            league_id_nullable='10'
        )
def player_id_to_name(id):
    time.sleep(1)
    return players.find_wnba_player_by_id(id)['full_name']
def get_shared_mins_df(ids):
    team_players = []
    for id in ids:
            player = players.find_wnba_player_by_id(id)
            gamelog = playergamelog.PlayerGameLog(
                player_id=id,
                season='2025',
                season_type_all_star='Regular Season',
                league_id_nullable='10'
            ).get_data_frames()[0]
        
            if not gamelog.empty:
                 gamelog.insert(1, 'Full_Name', player['id']) #change to 'full_name'
                 team_players.append(gamelog)
                 #code in def rate
            time.sleep(1)
    #print (team_players)
    all_logs = pd.concat(team_players, ignore_index=True)
    #print(all_logs)
    games = all_logs['GAME_DATE'].unique() #listof Game Dates
    shared_minutes = defaultdict(lambda: defaultdict(float))

    # shared minutes matrix (find most minutes combination)
    for game in games:
        game_data = all_logs[all_logs['GAME_DATE'] == game]
        for player1, player2 in combinations(game_data['Full_Name'], 2):
            min1 = game_data[game_data['Full_Name'] == player1]['MIN'].values[0]
            min2 = game_data[game_data['Full_Name'] == player2]['MIN'].values[0]
            shared = min(min1, min2)
            shared_minutes[player1][player2] += shared
            shared_minutes[player2][player1] += shared

    shared_mins_df = pd.DataFrame(shared_minutes).fillna(0)

    return shared_mins_df
    # listof top 4 other players with the target player

def get_team_ids_from_player_id(id):
    player_stats = commonplayerinfo.CommonPlayerInfo(
         player_id=id,
         league_id_nullable='10'
    ).get_data_frames()[0]
    team_id = player_stats['TEAM_ID']
    roster_team_df = team_lookup(team_id).get_data_frames()[0]
    #print(roster_team_1_df) #gives height
    team_player_ids = roster_team_df['PLAYER_ID'].tolist()
    if ignore in team_player_ids:
        team_player_ids.remove(ignore)
    return team_player_ids
def get_team_id_from_player_id(id):
    player_stats = commonplayerinfo.CommonPlayerInfo(
         player_id=id,
         league_id_nullable='10'
    ).get_data_frames()[0]
    return player_stats['TEAM_ID'].iloc[0]
def on_court_teammates(id):
    team_player_ids = get_team_ids_from_player_id(id)
    shared_minutes_df = get_shared_mins_df(team_player_ids)
    co_players = shared_minutes_df[id].sort_values(ascending=False).head(4).index.tolist()
    return co_players

def get_player_name(player_id):
    time.sleep(1)
    player = players.find_wnba_player_by_id(player_id)
    return player['full_name'] if player is not None else "Empty"
def calculate_team_possessions(home_id, opp_id):
    common_params = {
            'season': '2024', #change? 2025
            'season_type_all_star': 'Regular Season',
            'league_id_nullable': '10',  # '10' = WNBA
            'per_mode_detailed': 'PerGame',
            'measure_type_detailed_defense': 'Base',
            'last_n_games': 10,
            'pace_adjust': 'N',
            'plus_minus': 'N',
            'rank': 'N',
            'month': 0,
            'period': 0 #all game
        }
    #features = ['TEAM_NAME', 'TEAM_ID', 'FGA', 'FTA', 'OREB', 'TOV']
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

def calculate_usage_rate(id, home_id, opp_id):
    '''
    def calculate_base_usage(curr_id):
        team_possession = calculate_team_possessions(home_id, opp_id)
        gamelog = playergamelog.PlayerGameLog(
            player_id=curr_id,
            season='2025',
            season_type_all_star='Regular Season',
            league_id_nullable='10'
        ).get_data_frames()[0]
        if not gamelog.empty:
            rolling_fga = gamelog['FGA'].mean()
        time.sleep(1)
        return rolling_fga / team_possession
    '''
    def calculate_base_usage(curr_id):
        team_possession = calculate_team_possessions(home_id, opp_id)
        gamelog = playergamelog.PlayerGameLog(
            player_id=curr_id,
            season='2025',
            season_type_all_star='Regular Season',
            league_id_nullable='10'
        ).get_data_frames()[0]
        if not gamelog.empty:
            recent_games = gamelog.head(10)
            rolling_fga = recent_games['FGA'].mean()
            rolling_fta = recent_games['FTA'].mean()
            rolling_tov = recent_games['TOV'].mean()
            base_usage = (rolling_fga + 0.44 * rolling_fta + rolling_tov) / team_possession
            time.sleep(1)
            return base_usage
        return 0

    
    def calculate_usage_multiplier():
        co_player = on_court_teammates(id)
        teammate_usages_total = 0
        for c_id in co_player:
            teammate_usages_total += calculate_base_usage(c_id)
        avg_teammate_usage = teammate_usages_total / 4

        if avg_teammate_usage >= 0.28:
            return 0.88  # Very high-usage teammates 
        elif avg_teammate_usage >= 0.24:
            return 0.93  # High-usage teammates
        elif avg_teammate_usage >= 0.20:
            return 0.98  # Slightly reduced usage
        elif avg_teammate_usage >= 0.16:
            return 1.02  # Slightly boosted usage
        elif avg_teammate_usage >= 0.12:
            return 1.07  # Weak on-court group
        else:
            return 1.12  # Bench-heavy group

    base_usage = calculate_base_usage(id)
    usage_multiplier = calculate_usage_multiplier()
    usage_rate = base_usage * usage_multiplier
    #print(f"usage_rate={usage_rate}")
    return usage_rate

def get_primary_defender_matchup(home_team_player_ids, opp_team_player_ids, player_id):
    
    def get_position(p_id):
        try:
            df = commonplayerinfo.CommonPlayerInfo(
                player_id=p_id,
                league_id_nullable='10'  # WNBA
            ).get_data_frames()[0]
            time.sleep(1)
            return df['POSITION'].iloc[0]
        except:
            return None
    
    def get_impact_scores(player_dict):
        impact_list = []
        season='2025'
        n_games=10
        for p_id, info in player_dict.items():
            try:
                gamelog = playergamelog.PlayerGameLog(
                    player_id=p_id,
                    season=season,
                    season_type_all_star='Regular Season',
                    league_id_nullable='10'
                ).get_data_frames()[0]
                recent_games = gamelog.head(n_games)
                mean_pts = recent_games['PTS'].mean()
                mean_ast = recent_games['AST'].mean()
                mean_reb = recent_games['REB'].mean()
                impact_score = mean_pts + 0.7 * mean_ast + 0.7 * mean_reb
                impact_list.append({
                    'id': p_id,
                    'name': info['name'],
                    'position': info['position'],
                    'impact': impact_score
                })

                time.sleep(1)  # avoid rate limit
            except Exception as e:
                print(f"Failed to get impact for {info['name']}: {e}")
                continue
        # Sort by impact score descending
        return sorted(impact_list, key=lambda x: x['impact'], reverse=True)

    def normalize_position(pos):
        if not pos: return 'F'
        if 'G' in pos:
            return 'G'
        elif 'C' in pos:
            return 'C'
        else:
            return 'F'
        
    def pace(): #approx # of possessions the home team will get in segment
        total_impact = 0
        player_impact = 0
        for p in home_sorted:
            total_impact += p['impact']
            if p['name'] == player_id_to_name(player_id):
                player_impact = p['impact']
        
        player_weight = player_impact / total_impact
        segment_total_minutes = 8 #will play 8 mins out of 10

        # PACE: based on opponent/team tendencies
        pace_per_minute = calculate_team_possessions(home_team_id, opp_team_id) / 40
        # PLAYER MINUTES: based on weight and 5 people on court
        segment_minutes = player_weight * segment_total_minutes * 5

        # POSSESSIONS: how many total chances happen in the segment (team overall)
        segment_possessions = pace_per_minute * segment_total_minutes

        #print('seg mins =',segment_minutes, 'seg pos =', segment_possessions, 'pace per min =', pace_per_minute)
        return [segment_minutes, segment_possessions] 
    
    def calculate_segment_mins(id):
        gamelog_df = playergamelog.PlayerGameLog(
                    player_id=id,
                    season='2025',
                    season_type_all_star='Regular Season',
                    league_id_nullable='10'
                ).get_data_frames()[0][['MIN']]
        #print(gamelog_df)
        rolling_average_mins = gamelog_df[['MIN']].mean()
        segment_mins = rolling_average_mins * (10 / 40) #10 min quarters
        return float(segment_mins.iloc[0])

    def calculate_FGA_estimate(player_id): #per segment
        usage_rate = calculate_usage_rate(player_id, home_team_id, opp_team_id)
        segment_possessions = pace()[1]
        FGA_estimate =  segment_possessions * usage_rate
        return FGA_estimate
    
    home_positions = {}
    opp_positions = {}
    for id in home_team_player_ids:
        home_positions[id] = {'name': get_player_name(id),
                              'position': get_position(id)}
    for id in opp_team_player_ids:
        opp_positions[id] = {'name': get_player_name(id),
                              'position': get_position(id)}
    matchup_dict = {}
    used_defenders = set()
    home_sorted = get_impact_scores(home_positions)
    opp_sorted = get_impact_scores(opp_positions) 
    home_team_id = get_team_id_from_player_id(home_sorted[0]['id'])
    opp_team_id = get_team_id_from_player_id(opp_sorted[0]['id'])
    # Normalize positions
    for player in home_sorted:
        player['norm_pos'] = normalize_position(player['position'])
    for player in opp_sorted:
        player['norm_pos'] = normalize_position(player['position'])

    for home_player in home_sorted:
        matched = False

        # Match by exact position
        for opp in opp_sorted:
            if (home_player['position'] == opp['position']) and (opp['name'] not in used_defenders):
                matchup_dict[home_player['name']] = opp['name']
                used_defenders.add(opp['name'])
                matched = True
                break

        # Fallback,  match by normalized position group (G/F/C)
        if not matched:
            for opp in opp_sorted:
                if (home_player['norm_pos'] == opp['norm_pos']) and (opp['name'] not in used_defenders):
                    matchup_dict[home_player['name']] = opp['name']
                    used_defenders.add(opp['name'])
                    matched = True
                    break

        # Final fallback, assign any unassigned defender
        if not matched:
            for opp in opp_sorted:
                if opp['name'] not in used_defenders:
                    matchup_dict[home_player['name']] = opp['name']
                    used_defenders.add(opp['name'])
                    matched = True
                    break

        # If absolutely no defender available
        if not matched:
            matchup_dict[home_player['name']] = None
    common_params = {
            'season': '2025', #change? 2025
            'season_type_all_star': 'Regular Season',
            'league_id_nullable': '10',  # '10' = WNBA
            'per_mode_detailed': 'PerGame',
            'measure_type_detailed_defense': 'Advanced',
            'last_n_games': 10,
            'pace_adjust': 'N',
            'plus_minus': 'N',
            'rank': 'N',
            'month': 0,
            'period': 0 #all game
        }
    league_df = LeagueDashTeamStats(
            **common_params
        ).get_data_frames()[0]
    rolling_league_eFG = league_df['EFG_PCT'].mean()
    
    def calculate_eFG(player_id):
        season = '2025'
        n_games = 10
        defender_id = players.find_wnba_players_by_full_name(matchup_dict[get_player_name(player_id)])[0]['id']
        home_opp_efg = [] #home in index 0, defender in index 1
        for id in [player_id, defender_id]:
            gamelog = playergamelog.PlayerGameLog(
                        player_id=id,
                        season=season,
                        season_type_all_star='Regular Season',
                        league_id_nullable='10'
                    ).get_data_frames()[0]
            recent_games = gamelog.head(n_games)

            fgm = recent_games['FGM'].mean()
            fg3m = recent_games['FG3M'].mean()
            fga = recent_games['FGA'].mean()

            if fga == 0:
                efg = 0
            else:
                efg = (fgm + 0.5 * fg3m) / fga
            home_opp_efg.append(efg)
            time.sleep(1)
        adj_efg = home_opp_efg[0] * (rolling_league_eFG / home_opp_efg[1])
        return adj_efg
    
    def calculate_teammate_factors(player_id):
        def calculate_ast_factor(id):
            co_player_ids = on_court_teammates(player_id)
            total_teammate_eFG = 0
            for p_id in co_player_ids:
                total_teammate_eFG += calculate_eFG(p_id) 
            teammate_eFG = total_teammate_eFG / len(co_player_ids)
            AST_factor = teammate_eFG / rolling_league_eFG
            return AST_factor 
        
        #REB, (Height):

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

        def get_reb_factor(player_id, opp_on_court_ids):
            player_height, player_pos = get_player_height_and_position(player_id)
            
            teammates = on_court_teammates(player_id)
            teammate_heights = []
            teammate_positions = []

            for pid in teammates:
                h, pos = get_player_height_and_position(pid)
                teammate_heights.append(h)
                teammate_positions.append(pos)

            avg_teammate_height = sum(teammate_heights) / len(teammate_heights)
            player_vs_teammates = player_height - avg_teammate_height

            # Check if team lacks bigs
            has_big = any(p in ['F', 'C'] for p in teammate_positions)
            only_one_big = sum(p in ['F', 'C'] for p in teammate_positions) == 1

            # Opponent height assessment
            opp_heights = []
            for pid in opp_on_court_ids:
                h, _ = get_player_height_and_position(pid)
                opp_heights.append(h)

            avg_opp_height = sum(opp_heights) / len(opp_heights) if opp_heights else 72
            height_diff_vs_opp = player_height - avg_opp_height

            base_factor = 1.0

            # Teammate-based scaling
            if player_pos in ['G'] and not has_big:
                base_factor += 0.2
            elif player_pos in ['F'] and only_one_big:
                base_factor += 0.1

            # Height-based adjustments
            height_adj = player_vs_teammates / 24  # +0.1 if 2 ft taller than teammates
            opp_adj = height_diff_vs_opp / 36      # +0.1 if 3 ft taller than opponents

            reb_factor = base_factor + height_adj + opp_adj
            return round(max(0.85, min(reb_factor, 1.2)), 3)  # Clamp
        def calculate_adj_stats(curr_id):
            defender_id = players.find_wnba_players_by_full_name(matchup_dict[get_player_name(curr_id)])[0]['id']
            opp_on_court_ids = on_court_teammates(defender_id)
            reb_factor = get_reb_factor(player_id, opp_on_court_ids)
            gamelog = playergamelog.PlayerGameLog(
                player_id=curr_id,
                season='2025',
                season_type_all_star='Regular Season',
                league_id_nullable='10'
            ).get_data_frames()[0]
            recent_games = gamelog.head(10)
            if not gamelog.empty:
                if recent_games['FTA'].sum() != 0:
                    ft_pct = recent_games['FTM'].sum() / recent_games['FTA'].sum()
                else:
                    ft_pct = 0.8  # fallback avg
                fta_per_min = recent_games['FTA'].sum() / recent_games['MIN'].sum()

                rolling_ast = recent_games['AST'].mean()
                rolling_reb = recent_games['REB'].mean()

                reb_std = recent_games['REB'].std()
                ast_std = recent_games['AST'].std()
                pts_std = recent_games['PTS'].std()

            teammate_AST_factor = calculate_ast_factor(curr_id)
            opp_AST_factor = calculate_ast_factor(defender_id)
            segment_minutes = calculate_segment_mins(curr_id)
            usage_rate = calculate_usage_rate(curr_id, home_team_id, opp_team_id)
            adj_ast = rolling_ast * teammate_AST_factor * opp_AST_factor
            adj_reb = rolling_reb * reb_factor
            adj_efg = calculate_eFG(player_id)
            est_fga = calculate_FGA_estimate(player_id) * 4
            est_fta = float(fta_per_min * segment_minutes * 4) # per game (4)
            adj_pts = float(est_fga * adj_efg * 2 + est_fta * ft_pct)

            return {
                'player_id': curr_id,
                'opponent_id': defender_id,
                'segment_minutes': segment_minutes,
                'usage_rate': usage_rate,
                'adj_efg': adj_efg,
                'ft_pct': ft_pct,
                'est_fga': est_fga,
                'est_fta': est_fta,
                'adj_rolling_stats': {
                    'PTS': adj_pts,
                    'REB': adj_reb,
                    'AST': adj_ast
                    
            },
                    'rolling_std': {
                        'PTS': pts_std,
                        'REB': reb_std,
                        'AST': ast_std
                    }}
        


        return calculate_adj_stats(player_id)
    

    return calculate_teammate_factors(player_id)
    #return matchup_dict

def run_monte_carlo_sim(player_sim_data, n_simulations):
    print('Data fetched!')
    np.random.seed(42)  # For reproducibility

    sim_results = {
        'PTS': [],
        'REB': [],
        'AST': []
    }

    for trial in range(n_simulations):
        if trial == n_simulations:
            print(f'Trial number {n_simulations}')
        for stat in ['PTS', 'REB', 'AST']:
            mean = float(player_sim_data['adj_rolling_stats'][stat])
            std = float(player_sim_data['rolling_std'][stat])

            # Sample from normal distribution
            value = np.random.normal(loc=mean, scale=std)
            value = max(0, round(value, 1))  # Clamp to 0, round to 1 decimal
            sim_results[stat].append(value)

    return pd.DataFrame(sim_results)

team_2 = "Fever"
team_1 = "Lynx"

team_1_id = teams.find_wnba_teams_by_nickname(team_1)[0]['id']
team_2_id = teams.find_wnba_teams_by_nickname(team_2)[0]['id']

roster_team_1_df = team_lookup(team_1_id).get_data_frames()[0]
roster_team_2_df = team_lookup(team_2_id).get_data_frames()[0]
#print(roster_team_1_df) #gives height
team_1_player_ids = roster_team_1_df['PLAYER_ID'].tolist()
team_2_player_ids = roster_team_2_df['PLAYER_ID'].tolist()

from datetime import datetime
import os

# Create timestamped folder name
today_str = datetime.today().strftime('%Y-%m-%d')
folder_name = f"{team_1.lower()}_vs_{team_2.lower()}_{today_str}"
output_folder = os.path.join('sim_results', folder_name)
os.makedirs(output_folder, exist_ok=True)

ignore = 1642286
#target_players = ['Aliyah Boston', 'Natasha Howard', 'Kelsey Mitchell', 'Aari McDonald', 'Lexie Hull']
target_players = ['Bridget Carleton', 'Alanna Smith', 'Napheesa Collier', 'Kayla McBride', 'Courtney Williams']

# Prepare a list to collect all results
all_sim_results = []

for player_name in target_players:
    output_file = os.path.join(output_folder, f"{player_name.replace(' ', '_').lower()}_sim.csv")

    # Skip if already exists
    if os.path.exists(output_file):
        print(f"Skipping {player_name}, already simulated.")
        continue

    try:
        player_id = players.find_wnba_players_by_full_name(player_name)[0]['id']
        print(f"\nRunning simulation for {player_name} (ID: {player_id})")

        player_sim_data = get_primary_defender_matchup(team_1_player_ids, team_2_player_ids, player_id)

        # Clamp std dev
        max_pts_std = player_sim_data['est_fga'] * 1.5
        player_sim_data['rolling_std']['PTS'] = min(player_sim_data['rolling_std']['PTS'], max_pts_std)

        # Simulate
        df_sim = run_monte_carlo_sim(player_sim_data, n_simulations=20000)
        df_sim['PLAYER'] = player_name

        # Save immediately
        df_sim.to_csv(output_file, index=False)
        print(f"Saved: {output_file}")

    except Exception as e:
        print(f"Error simulating {player_name}, maybe mispelled?: {e}")


# Combine all player CSVs at the end
combined_df = pd.DataFrame()
for fname in os.listdir(output_folder):
    if fname.endswith('_sim.csv'):
        df = pd.read_csv(os.path.join(output_folder, fname))
        combined_df = pd.concat([combined_df, df], ignore_index=True)

# Save the full CSV
final_output = os.path.join(output_folder, f"{team_1.lower()}_vs_{team_2.lower()}_combined_simulations.csv")
combined_df.to_csv(final_output, index=False)
print(f"All player simulations combined to: {final_output}")


'''
predict_player = 'Aliyah Boston' #must be in team 1
predict_player_id = players.find_wnba_players_by_full_name(predict_player)[0]['id']
print(predict_player_id)

gamelog = playergamelog.PlayerGameLog(
                player_id=predict_player_id,
                season='2025',
                season_type_all_star='Regular Season',
                league_id_nullable='10'
            ).get_data_frames()[0]
#print(gamelog)
player_sim_data = get_primary_defender_matchup(team_1_player_ids, team_2_player_ids, predict_player_id)
max_pts_std = player_sim_data['est_fga'] * 1.5  # rough estimate: 1.5x shot volume
player_sim_data['rolling_std']['PTS'] = min(player_sim_data['rolling_std']['PTS'], max_pts_std)
print(player_sim_data)
df_sim = run_monte_carlo_sim(player_sim_data, n_simulations=20000)
print(df_sim.describe())
'''

def_stats = LeagueDashTeamStats( #lower def rating better
    season='2025',
    season_type_all_star='Regular Season',
    league_id_nullable='10',  # '10' = WNBA
    per_mode_detailed='PerGame',
    measure_type_detailed_defense='Opponent',  # Pull defensive metrics
    last_n_games=10,
    pace_adjust='N',
    plus_minus='N',
    rank='N',
    month=0,
    opponent_team_id=0,
    period=0 #all game
)

#print(def_stats.get_data_frames()[0].info())

features2 = ['TEAM_ID',
            'TEAM_NAME',
            'OPP_PTS',
            'OPP_FG_PCT',
            'OPP_FG3_PCT',
            'OPP_REB',
            'OPP_AST',
]


features = ['TEAM_ID',
            'TEAM_NAME',
            'DEF_RATING', #Overall
            'DREB', #Paint, Post Def
            'BLK', 
            'OPP_PTS_PAINT', 
            'STL', #Transition, Turnover
            'OPP_PTS_FB', 
            'OPP_PTS_OFF_TOV',
            'OPP_PTS_2ND_CHANCE' #2nd chance
            ]
#print(player_stats.get_data_frames()[0][features2])
#print(base_stats.get_data_frames()[0].info())
#print(team_stats.get_data_frames()[0][features])
# Filter for key columns
#print(player_stats.get_data_frames()[0][features2])
# Opponent Defensive Metrics


# Convert to DataFrame
#print(team_stats.get_data_frames()[0][features])
# Display selected defensive metrics
#print(df)

#XXXXX no need




