import streamlit as st
import pandas as pd

# Load base table from the original CSV data
@st.cache_data
def load_base_data():
    return pd.read_csv("9JuneuptoWT20.csv")

# Helper functions
def cricket_overs_to_balls(overs):
    overs_int = int(overs)
    balls_part = int(round((overs - overs_int) * 10))
    return overs_int * 6 + balls_part

def balls_to_cricket_overs(balls):
    overs = balls // 6
    rem_balls = balls % 6
    return float(f"{int(overs)}.{int(rem_balls)}")

def is_valid_overs_format(over):
    overs_int = int(over)
    balls = round((over - overs_int) * 10)
    return balls in [0, 1, 2, 3, 4, 5]

# Team list
team_list = [
    'Middlesex Women', 'Yorkshire Women', 'Northamptonshire Steelbacks Women',
    'Derbyshire Falcons Women', 'Glamorgan Women', 'Sussex Sharks Women',
    'Worcestershire Rapids Women', 'Leicestershire Foxes Women',
    'Kent Women', 'Gloucestershire Women'
]

north_group = [
    'Yorkshire Women', 'Northamptonshire Steelbacks Women',
    'Derbyshire Falcons Women', 'Leicestershire Foxes Women',
    'Worcestershire Rapids Women'
]

# UI
st.title("Vitality Blast 2025 Standings Calculator")
st.markdown("Input results for **future games** below to get the updated standings.")

num_matches = st.number_input("Number of future matches to add", min_value=1, value=1, step=1)

future_matches = []

for i in range(num_matches):
    st.markdown(f"### Match {i+1}")
    team1 = st.selectbox(f"Team 1 (For) - Match {i+1}", team_list, key=f"team1_{i}")
    team2 = st.selectbox(f"Team 2 (Against) - Match {i+1}", [t for t in team_list if t != team1], key=f"team2_{i}")
    runs_for = st.number_input(f"Runs For - Match {i+1}", min_value=0, key=f"runs_for_{i}")
    overs_for = st.number_input(f"Overs For - Match {i+1} (Valid: x.0 to x.5 only)", min_value=0.0, step=0.1, key=f"overs_for_{i}")
    runs_against = st.number_input(f"Runs Against - Match {i+1}", min_value=0, key=f"runs_against_{i}")
    overs_against = st.number_input(f"Overs Against - Match {i+1} (Valid: x.0 to x.5 only)", min_value=0.0, step=0.1, key=f"overs_against_{i}")

    if is_valid_overs_format(overs_for) and is_valid_overs_format(overs_against):
        future_matches.append({
            'team1': team1, 'team2': team2,
            'runs_for': runs_for, 'overs_for': overs_for,
            'runs_against': runs_against, 'overs_against': overs_against
        })
    else:
        st.warning(f"Invalid overs format in Match {i+1}. Allowed: decimal up to .5 only (e.g., 19.0 to 19.5).")

if st.button("Update Table") and len(future_matches) == num_matches:
    # 🧠 Logic moved to a separate helper for clarity
    from pathlib import Path
    exec(Path("NRRVT20W.ipynb").read_text())
