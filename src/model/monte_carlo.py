import numpy as np
import pandas as pd

# Simulation engine

def run_monte_carlo_sim(player_sim_data, n_simulations):
    print('Data fetched!')
    np.random.seed(42)  # For reproducibility

    sim_results = {
        'PTS': [],
        'REB': [],
        'AST': []
    }

    for trial in range(n_simulations):
        if trial % 5000 == 0 and trial > 0:  # Fixed: was checking if trial == n_simulations
            print(f'Trial number {trial}')
        for stat in ['PTS', 'REB', 'AST']:
            mean = float(player_sim_data['adj_rolling_stats'][stat])
            std = float(player_sim_data['rolling_std'][stat])

            # Sample from normal distribution
            value = np.random.normal(loc=mean, scale=std)
            value = max(0, round(value, 1))  # Clamp to 0, round to 1 decimal
            sim_results[stat].append(value)

    return pd.DataFrame(sim_results)