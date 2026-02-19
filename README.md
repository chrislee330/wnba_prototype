# WNBA Monte Carlo Player Simulator

> **Prototype** Core simulation pipeline is functional. Known bugs and limitations are documented below. This project evolved from a semi-functional prototype. 

---

## What It Does

Given two teams and a list of target players, the simulator:

1. Fetches live WNBA player and team data via the `nba_api`
2. Computes context-aware stat projections accounting for:
   - **Usage rate** adjusted for on-court teammate tendencies
   - **Effective FG%** adjusted against the primary defender's defensive efficiency
   - **Rebound factors** based on player/teammate/opponent height and position
   - **Assist factors** based on teammate shooting efficiency vs. league average
   - **Pace and possessions** estimated from the Dean Oliver possession formula over the last 10 games
3. Runs 20,000 Monte Carlo trials per player sampling from a normal distribution around adjusted means
4. Saves per-player CSVs and a combined simulation file
---

## Project Structure

```
wnba_monte_carlo_sim/
├── main.py                         # Entry point — runs full simulation
├── analyze.py                      # Summary stats on simulation results
├── model.py                        # Original prototype (kept for reference)
├── requirements.txt
└── src/
    ├── data/
    │   ├── api_client.py           # All nba_api interactions
    │   └── data_processor.py       # Shared minutes matrix, teammate lookup
    ├── model/
    │   ├── matchup_analyzer.py     # Defender assignment, stat adjustment
    │   ├── monte_carlo.py          # Simulation engine
    │   └── usage_calculator.py     # Usage rate with teammate adjustment
    └── utils/
        ├── constants.py            # Teams, players, config in one place
        └── helpers.py              # Output management, full pipeline runner
```

---

## How to Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure the matchup
In `src/utils/constants.py`:
```python
TEAM1 = "Lynx"
TEAM2 = "Mercury"

TARGETPLAYERS = {
    'TEAM1': ['Napheesa Collier', 'Bridget Carleton', 'Alanna Smith'],
    'TEAM2': ['Alyssa Thomas', 'Kahleah Copper', 'Satou Sabally']
}
```

### 3. Run the simulation
```bash
python main.py
```

### 4. Analyze results
```bash
python analyze.py
# Enter date when prompted: YYYY-MM-DD
```

---

## Known Remaining Bugs

| # | Location | Issue |
|---|---|---|
| 1 | `monte_carlo.py` | Still uses `np.random.normal` for count data. Normal distribution can produce negatives and doesn't reflect the discrete nature of PTS/REB/AST. Poisson or negative binomial would be more appropriate. |
| 2 | `api_client.py` | Currently, the program fetches from the API multiple times, resulting in a chance of timing out. This is solved by using `time.sleep(1)`, however in the future, fetching all the data at once should be better. |
| 3 | `matchup_analyzer.py` | `calculate_ast_factor()` computes eFG of teammates but calls `calculate_eFG()` which resolves the *defender* of each teammate — not their own eFG. Conflates offensive and defensive efficiency. |

---

## Remaining Limitations

**Distributional assumptions**
Normal distribution is a poor fit for sports count data. Points, rebounds, and assists are non-negative integers with right-skewed distributions better modeled by Poisson or negative binomial.

**No time-series discipline**
Features are computed from recent game averages with no enforcement that only past data is used. There is no train/validation split or leakage prevention, so there is no rigorous way to know whether the projections are actually predictive vs. a simple rolling average.


**No injury or lineup handling**
No check for player availability or injury status. A player in `TARGETPLAYERS` who is inactive will still be simulated with stale stats and no warning.

**API-dependent runtime**
Every run fetches fresh data with no local caching. A full 6-player run takes 15–30 minutes due to rate limiting. No retry logic or exponential backoff exists if the API returns errors mid-run.

**NBA API endpoints have changed**
From the time I made this, the NBA api endpoints were working. This project will be served as an initial prototype.

---

## Dependencies

- `nba_api` — WNBA player/team data
- `pandas`, `numpy` — data manipulation and simulation
- Python 3.10+