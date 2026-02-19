import time
from nba_api.stats.endpoints import playergamelog

def calculate_usage_rate(player_id, home_id, opp_id):
    from src.data.api_client import calculate_team_possessions
    from src.data.data_processor import on_court_teammates
    
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
        return 0.2  # default usage rate

    def calculate_usage_multiplier():
        co_players = on_court_teammates(player_id)
        if not co_players:
            return 1.0
            
        teammate_usages_total = 0
        valid_teammates = 0
        for c_id in co_players:
            usage = calculate_base_usage(c_id)
            if usage > 0:
                teammate_usages_total += usage
                valid_teammates += 1
        
        if valid_teammates == 0:
            return 1.0
            
        avg_teammate_usage = teammate_usages_total / valid_teammates

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

    base_usage = calculate_base_usage(player_id)
    usage_multiplier = calculate_usage_multiplier()
    usage_rate = base_usage * usage_multiplier
    return usage_rate