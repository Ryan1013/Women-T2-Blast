import streamlit as st
import pandas as pd

# -----------------------------
# Helper Functions
# -----------------------------
def cricket_overs_to_balls(overs):
    overs_int = int(overs)
    balls_part = int(round((overs - overs_int) * 10))
    return overs_int * 6 + balls_part

def balls_to_cricket_overs(balls):
    overs = balls // 6
    rem_balls = balls % 6
    return float(f"{int(overs)}.{int(rem_balls)}")

# -----------------------------
# Load Processed Base Table
# -----------------------------
@st.cache_data
def load_base_table():
    base = pd.read_csv("/mnt/data/9JuneuptoWT20.csv")
    # ... Add preprocessing logic here, or assume final_display, north_table, south_table already computed
    # For simplicity, return pre-split group tables
    return north_table.copy(), south_table.copy()

north_table, south_table = load_base_table()
all_teams = sorted(north_table["Team"].tolist() + south_table["Team"].tolist())

# -----------------------------
# Streamlit Interface
# -----------------------------
st.title("Vitality Blast 2025 Standings Calculator")

num_matches = st.number_input("Number of future matches to add", min_value=1, max_value=10, value=1, step=1)

future_results = []
for i in range(num_matches):
    st.subheader(f"Match {i+1}")
    col1, col2 = st.columns(2)
    with col1:
        team1 = st.selectbox(f"Team 1 (For) - Match {i+1}", all_teams, key=f"team1_{i}")
        runs1 = st.number_input(f"Runs For - Match {i+1}", min_value=0, key=f"runs1_{i}")
        overs1 = st.number_input(f"Overs For (e.g., 19.5) - Match {i+1}", min_value=0.0, max_value=20.0, step=0.1, key=f"overs1_{i}")
    with col2:
        team2 = st.selectbox(f"Team 2 (Against) - Match {i+1}", all_teams, key=f"team2_{i}")
        runs2 = st.number_input(f"Runs Against - Match {i+1}", min_value=0, key=f"runs2_{i}")
        overs2 = st.number_input(f"Overs Against (e.g., 20.0) - Match {i+1}", min_value=0.0, max_value=20.0, step=0.1, key=f"overs2_{i}")

    future_results.append({
        'team1': team1, 'runs1': runs1, 'overs1': overs1,
        'team2': team2, 'runs2': runs2, 'overs2': overs2
    })

if st.button("Update Table"):
    temp_table = pd.concat([north_table, south_table], ignore_index=True)

    for match in future_results:
        for_record = temp_table[temp_table["Team"] == match["team1"]].copy()
        against_record = temp_table[temp_table["Team"] == match["team2"]].copy()

        for_record["Runs For"] += match["runs1"]
        for_record["Overs For"] += match["overs1"]
        for_record["Runs Against"] += match["runs2"]
        for_record["Overs Against"] += match["overs2"]
        for_record["M"] += 1

        against_record["Runs For"] += match["runs2"]
        against_record["Overs For"] += match["overs2"]
        against_record["Runs Against"] += match["runs1"]
        against_record["Overs Against"] += match["overs1"]
        against_record["M"] += 1

        # Update win/loss/tie
        if match["runs1"] > match["runs2"]:
            for_record["W"] += 1
            for_record["PT"] += 4
            against_record["L"] += 1
        elif match["runs1"] < match["runs2"]:
            for_record["L"] += 1
            against_record["W"] += 1
            against_record["PT"] += 4
        else:
            for_record["T"] += 1
            for_record["PT"] += 2
            against_record["T"] += 1
            against_record["PT"] += 2

        # Update NRR
        for_record["NRR"] = round(
            (for_record["Runs For"] / (cricket_overs_to_balls(for_record["Overs For"]) / 6)) -
            (for_record["Runs Against"] / (cricket_overs_to_balls(for_record["Overs Against"]) / 6)), 3)
        against_record["NRR"] = round(
            (against_record["Runs For"] / (cricket_overs_to_balls(against_record["Overs For"]) / 6)) -
            (against_record["Runs Against"] / (cricket_overs_to_balls(against_record["Overs Against"]) / 6)), 3)

        temp_table.update(for_record)
        temp_table.update(against_record)

    north_group = ['Yorkshire Women', 'Northamptonshire Steelbacks Women', 'Derbyshire Falcons Women',
                   'Leicestershire Foxes Women', 'Worcestershire Rapids Women']
    north_updated = temp_table[temp_table["Team"].isin(north_group)].copy()
    south_updated = temp_table[~temp_table["Team"].isin(north_group)].copy()

    north_updated = north_updated.sort_values(by=["PT", "NRR"], ascending=[False, False]).reset_index(drop=True)
    south_updated = south_updated.sort_values(by=["PT", "NRR"], ascending=[False, False]).reset_index(drop=True)

    north_updated.index += 1
    south_updated.index += 1

    st.markdown("### 📍 North Group")
    st.dataframe(north_updated)

    st.markdown("### 📍 South Group")
    st.dataframe(south_updated)

st.markdown(
    "<small>📘 Disclaimer: Always enter Overs For/Against as 20 if the concerned team has been bowled out earlier than their full quota of overs.</small>",
    unsafe_allow_html=True)
