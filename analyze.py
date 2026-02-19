import pandas as pd
import os
from datetime import datetime

from src.utils.constants import TEAM1, TEAM2

#date_str = datetime.today().strftime('%Y-%m-%d')
date_str = input("Enter date for analysis: YYYY-MM-DD \n")
# Reuse your folder name
folder_name = f"{TEAM1.lower()}_vs_{TEAM2.lower()}_{date_str}"
output_folder = os.path.join('sim_results', folder_name)
combined_path = os.path.join(output_folder, f"{TEAM1.lower()}_vs_{TEAM2.lower()}_combined_simulations.csv")

# Load CSV
df_combined = pd.read_csv(combined_path)

# View summary stats
summary_df = df_combined.groupby('PLAYER')[['PTS', 'REB', 'AST']].agg(['mean', 'std', 'min', 'max', 'median'])
print(summary_df.round(2))