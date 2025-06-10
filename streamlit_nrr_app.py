
import streamlit as st
import pandas as pd

# -----------------------------
# Helper Functions
# -----------------------------
def cricket_overs_to_balls(overs):
    overs_int = int(overs)
    balls_part = int(round((overs - overs_int) * 10))
    return overs_int * 6 + balls_part

# -----------------------------
# Load Preprocessed Base Tables
# -----------------------------
@st.cache_data
def load_base_data():
    north = pd.read_csv("north_table.csv")
    south = pd.read_csv("south_table.csv")
    return pd.concat([north, south], ignore_index=True)

# -----------------------------
# Streamlit Interface
# -----------------------------
base_data = load_base_data()
team_list = base_data['Team'].tolist()

north_group = [
    'Yorkshire Women', 'Northamptonshire Steelbacks Women',
    'Derbyshire Falcons Women', 'Leicestershire Foxes Women',
    'Worcestershire Rapids Women'
]

st.title("Vitality Blast 2025 Standings Calculator")
st.markdown("Input results for **future games** below to get the updated standings.")

num_matches = st.number_input("Number of future matches to add", min_value=1, value=1, step=1)

future_matches = []
overs_input_valid = True

for i in range(num_matches):
    st.markdown(f"### Match {i+1}")
    team1 = st.selectbox(f"Team 1 (For) - Match {i+1}", team_list, key=f"team1_{i}")
    team2 = st.selectbox(f"Team 2 (Against) - Match {i+1}", [t for t in team_list if t != team1], key=f"team2_{i}")
    runs_for = st.number_input(f"Runs For - Match {i+1}", min_value=0, key=f"runs_for_{i}")
    overs_for = st.number_input(f"Overs For (e.g., 19.5) - Match {i+1}", min_value=0.0, step=0.1, value=0.0, format="%.1f", key=f"overs_for_{i}")
    runs_against = st.number_input(f"Runs Against - Match {i+1}", min_value=0, key=f"runs_against_{i}")
    overs_against = st.number_input(f"Overs Against (e.g., 20.0) - Match {i+1}", min_value=0.0, step=0.1, value=0.0, format="%.1f", key=f"overs_against_{i}")

    def is_valid_overs(o): return (o * 10) % 1 == 0 and 0.0 <= (o % 1) <= 0.5
    if not is_valid_overs(overs_for):
        st.warning(f"⚠️ Match {i+1}: Overs For must end in .0 to .5 only.")
        overs_input_valid = False
    if not is_valid_overs(overs_against):
        st.warning(f"⚠️ Match {i+1}: Overs Against must end in .0 to .5 only.")
        overs_input_valid = False

    future_matches.append({
        'team1': team1, 'team2': team2,
        'runs_for': runs_for, 'overs_for': overs_for,
        'runs_against': runs_against, 'overs_against': overs_against
    })

if st.button("Update Table"):
    if not overs_input_valid:
        st.error("❌ Please correct the invalid Overs inputs before proceeding.")
        st.stop()

    updated = base_data.copy()

    for match in future_matches:
        t1, t2 = match['team1'], match['team2']
        rf, of, ra, oa = match['runs_for'], match['overs_for'], match['runs_against'], match['overs_against']

        for team, add_rf, add_of, add_ra, add_oa, win, tie in [
            (t1, rf, of, ra, oa, rf > ra, rf == ra),
            (t2, ra, oa, rf, of, ra > rf, rf == ra)
        ]:
            idx = updated[updated['Team'] == team].index[0]
            updated.at[idx, 'Runs For'] += add_rf
            updated.at[idx, 'Overs For'] += add_of
            updated.at[idx, 'Runs Against'] += add_ra
            updated.at[idx, 'Overs Against'] += add_oa
            updated.at[idx, 'M'] += 1
            if win:
                updated.at[idx, 'W'] += 1
                updated.at[idx, 'PT'] += 4
            elif tie:
                updated.at[idx, 'T'] += 1
                updated.at[idx, 'PT'] += 2
            else:
                updated.at[idx, 'L'] += 1

    updated['NRR Balls For'] = updated['Overs For'].apply(cricket_overs_to_balls)
    updated['NRR Balls Against'] = updated['Overs Against'].apply(cricket_overs_to_balls)
    updated['Run Rate For'] = updated['Runs For'] / (updated['NRR Balls For'] / 6)
    updated['Run Rate Against'] = updated['Runs Against'] / (updated['NRR Balls Against'] / 6)
    updated['NRR'] = (updated['Run Rate For'] - updated['Run Rate Against']).round(3)

    final = updated[['Team', 'M', 'W', 'L', 'T', 'N/R', 'BP', 'PT', 'NRR',
                     'Runs For', 'Overs For', 'Runs Against', 'Overs Against']]
    final = final.sort_values(by=['PT', 'NRR'], ascending=[False, False]).reset_index(drop=True)
    final.index += 1

    north_table = final[final['Team'].isin(north_group)].reset_index(drop=True)
    south_table = final[~final['Team'].isin(north_group)].reset_index(drop=True)
    north_table.index += 1
    south_table.index += 1

    st.subheader("📍 North Group")
    st.dataframe(north_table, use_container_width=True)

    st.subheader("📍 South Group")
    st.dataframe(south_table, use_container_width=True)

    st.markdown("ℹ️ **Disclaimer**: Always enter **Overs For/Against** as 20 if the concerned team has been bowled out earlier than their full quota of overs.")
