import pandas as pd
import time
from nba_api.stats.endpoints import playergamelog, commonplayerinfo
from nba_api.stats.static import players

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
            time.sleep(1)
        except Exception as e:
            print(f"Failed to get impact for {info['name']}: {e}")
            continue
    return sorted(impact_list, key=lambda x: x['impact'], reverse=True)

def calculate_segment_mins(id):
    try:
        gamelog_df = playergamelog.PlayerGameLog(
            player_id=id,
            season='2025',
            season_type_all_star='Regular Season',
            league_id_nullable='10'
        ).get_data_frames()[0][['MIN']]
        rolling_average_mins = gamelog_df[['MIN']].mean()
        segment_mins = rolling_average_mins * (10 / 40) 
        return float(segment_mins.iloc[0])
    except:
        return 8.0  # default minutes

def create_matchup_assignments(home_team_player_ids, opp_team_player_ids):
    """Create basic matchup assignments based on positions and impact"""
    from src.data.api_client import get_player_name
    
    # Get player info for both teams
    home_positions = {}
    opp_positions = {}
    
    for id in home_team_player_ids:
        home_positions[id] = {
            'name': get_player_name(id),
            'position': get_position(id)
        }
    
    for id in opp_team_player_ids:
        opp_positions[id] = {
            'name': get_player_name(id),
            'position': get_position(id)
        }
    
    # Get impact scores
    home_sorted = get_impact_scores(home_positions)
    opp_sorted = get_impact_scores(opp_positions)
    
    # Create matchup dictionary (simplified logic)
    matchup_dict = {}
    used_defenders = set()
    
    # Match by position priority and impact
    position_priority = {'G': 1, 'F': 2, 'C': 3}
    
    for home_player in home_sorted:
        best_defender = None
        best_score = float('inf')
        
        home_pos = home_player['position'] or 'F'
        home_pos_norm = home_pos[0] if home_pos else 'F'
        
        for opp_player in opp_sorted:
            if opp_player['name'] in used_defenders:
                continue
                
            opp_pos = opp_player['position'] or 'F'
            opp_pos_norm = opp_pos[0] if opp_pos else 'F'
            
            # Position matching score (lower is better)
            pos_score = abs(position_priority.get(home_pos_norm, 2) - 
                           position_priority.get(opp_pos_norm, 2))
            
            # Impact difference (prefer similar impact levels)
            impact_diff = abs(home_player['impact'] - opp_player['impact'])
            
            total_score = pos_score * 10 + impact_diff
            
            if total_score < best_score:
                best_score = total_score
                best_defender = opp_player['name']
        
        if best_defender:
            matchup_dict[home_player['name']] = best_defender
            used_defenders.add(best_defender)
    
    return matchup_dict

def get_primary_defender_matchup(home_team_player_ids, opp_team_player_ids, player_id):
    from src.data.api_client import (get_player_name, get_player_height_and_position, 
                                   get_team_id_from_player_id, calculate_team_possessions,
                                   player_id_to_name)
    from src.data.data_processor import on_court_teammates
    from src.model.usage_calculator import calculate_usage_rate
    
    # Create matchup assignments
    matchup_dict = create_matchup_assignments(home_team_player_ids, opp_team_player_ids)
    
    # Get basic info
    player_name = get_player_name(player_id)
    home_team_id = get_team_id_from_player_id(player_id)
    
    # Find opponent team ID
    opp_team_id = None
    for opp_id in opp_team_player_ids:
        try:
            opp_team_id = get_team_id_from_player_id(opp_id)
            break
        except:
            continue
    
    if not opp_team_id:
        raise ValueError("Could not determine opponent team ID")
    
    # Get defender ID
    defender_name = matchup_dict.get(player_name)
    if not defender_name:
        raise ValueError(f"No matchup found for {player_name}")
    
    defender_data = players.find_wnba_players_by_full_name(defender_name)
    if not defender_data:
        raise ValueError(f"Could not find defender: {defender_name}")
    
    defender_id = defender_data[0]['id']
    
    # Calculate league average eFG% (simplified)
    LEAGUE_EFG = 0.52  # approximate WNBA average
    
    def calculate_eFG(pid):
        try:
            gamelog = playergamelog.PlayerGameLog(
                player_id=pid,
                season='2025',
                season_type_all_star='Regular Season',
                league_id_nullable='10'
            ).get_data_frames()[0]
            recent_games = gamelog.head(10)
            
            fgm = recent_games['FGM'].mean()
            fg3m = recent_games['FG3M'].mean()
            fga = recent_games['FGA'].mean()
            
            if fga == 0:
                return LEAGUE_EFG
            
            efg = (fgm + 0.5 * fg3m) / fga
            time.sleep(1)
            return efg
        except:
            return LEAGUE_EFG
    
    def calculate_ast_factor(pid):
        try:
            co_player_ids = on_court_teammates(pid)
            if not co_player_ids:
                return 1.0
                
            total_teammate_eFG = 0
            valid_teammates = 0
            for p_id in co_player_ids:
                efg = calculate_eFG(p_id)
                if efg > 0:
                    total_teammate_eFG += efg
                    valid_teammates += 1
            
            if valid_teammates == 0:
                return 1.0
                
            teammate_eFG = total_teammate_eFG / valid_teammates
            return teammate_eFG / LEAGUE_EFG
        except:
            return 1.0
    
    def get_reb_factor(pid, opp_on_court_ids):
        try:
            player_height, player_pos = get_player_height_and_position(pid)
            
            teammates = on_court_teammates(pid)
            if not teammates:
                return 1.0
                
            teammate_heights = []
            teammate_positions = []

            for teammate_id in teammates:
                h, pos = get_player_height_and_position(teammate_id)
                teammate_heights.append(h)
                teammate_positions.append(pos)

            avg_teammate_height = sum(teammate_heights) / len(teammate_heights)
            player_vs_teammates = player_height - avg_teammate_height

            has_big = any(p and ('F' in p or 'C' in p) for p in teammate_positions)
            only_one_big = sum(1 for p in teammate_positions if p and ('F' in p or 'C' in p)) == 1

            opp_heights = []
            for pid in opp_on_court_ids:
                h, _ = get_player_height_and_position(pid)
                opp_heights.append(h)

            avg_opp_height = sum(opp_heights) / len(opp_heights) if opp_heights else 72
            height_diff_vs_opp = player_height - avg_opp_height

            base_factor = 1.0

            if player_pos and 'G' in player_pos and not has_big:
                base_factor += 0.2
            elif player_pos and 'F' in player_pos and only_one_big:
                base_factor += 0.1

            height_adj = player_vs_teammates / 24
            opp_adj = height_diff_vs_opp / 36

            reb_factor = base_factor + height_adj + opp_adj
            return max(0.85, min(reb_factor, 1.2))
        except:
            return 1.0
    
    # Calculate adjusted stats
    try:
        # Get player stats
        gamelog = playergamelog.PlayerGameLog(
            player_id=player_id,
            season='2025',
            season_type_all_star='Regular Season',
            league_id_nullable='10'
        ).get_data_frames()[0]
        recent_games = gamelog.head(10)
        
        if recent_games.empty:
            raise ValueError(f"No recent games found for player {player_id}")
        
        # Calculate base stats
        if recent_games['FTA'].sum() != 0:
            ft_pct = recent_games['FTM'].sum() / recent_games['FTA'].sum()
        else:
            ft_pct = 0.8
            
        fta_per_min = recent_games['FTA'].sum() / recent_games['MIN'].sum() if recent_games['MIN'].sum() > 0 else 0
        
        rolling_ast = recent_games['AST'].mean()
        rolling_reb = recent_games['REB'].mean()
        
        reb_std = recent_games['REB'].std()
        ast_std = recent_games['AST'].std()
        pts_std = recent_games['PTS'].std()
        
        # Calculate factors
        player_efg = calculate_eFG(player_id)
        defender_efg = calculate_eFG(defender_id)
        adj_efg = player_efg * (LEAGUE_EFG / max(defender_efg, 0.3))  # Prevent division by very small numbers
        
        teammate_AST_factor = calculate_ast_factor(player_id)
        opp_AST_factor = calculate_ast_factor(defender_id)
        
        opp_on_court_ids = on_court_teammates(defender_id)
        reb_factor = get_reb_factor(player_id, opp_on_court_ids)
        
        segment_minutes = calculate_segment_mins(player_id)
        usage_rate = calculate_usage_rate(player_id, home_team_id, opp_team_id)
        
        # Calculate team possessions and estimates
        team_possessions_per_game = calculate_team_possessions(home_team_id, opp_team_id)
        segment_possessions = team_possessions_per_game * (segment_minutes / 40)
        
        est_fga = segment_possessions * usage_rate * 4  # per game
        est_fta = fta_per_min * segment_minutes * 4
        
        # Adjusted stats
        adj_ast = rolling_ast * teammate_AST_factor * opp_AST_factor
        adj_reb = rolling_reb * reb_factor
        adj_pts = est_fga * adj_efg * 2 + est_fta * ft_pct
        
        return {
            'player_id': player_id,
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
                'PTS': pts_std if pd.notna(pts_std) else 3.0,
                'REB': reb_std if pd.notna(reb_std) else 1.5,
                'AST': ast_std if pd.notna(ast_std) else 1.0
            }
        }
        
    except Exception as e:
        print(f"Error calculating stats for player {player_id}: {e}")
        # Return default values
        return {
            'player_id': player_id,
            'opponent_id': defender_id,
            'segment_minutes': 8.0,
            'usage_rate': 0.2,
            'adj_efg': 0.5,
            'ft_pct': 0.8,
            'est_fga': 8.0,
            'est_fta': 2.0,
            'adj_rolling_stats': {
                'PTS': 12.0,
                'REB': 4.0,
                'AST': 3.0
            },
            'rolling_std': {
                'PTS': 3.0,
                'REB': 1.5,
                'AST': 1.0
            }
        }