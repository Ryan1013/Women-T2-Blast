
import streamlit as st
import pandas as pd

@st.cache_data
def load_base_data():
    return pd.read_csv("9JuneuptoWT20.csv")

def cricket_overs_to_balls(overs):
    overs_int = int(overs)
    balls_part = int(round((overs - overs_int) * 10))
    return overs_int * 6 + balls_part

def balls_to_cricket_overs(balls):
    overs = balls // 6
    rem_balls = balls % 6
    return float(f"{int(overs)}.{int(rem_balls)}")

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

    base = pd.read_csv("north_table.csv")
    base_south = pd.read_csv("south_table.csv")
    combined = pd.concat([base, base_south], ignore_index=True)

    new_rows = []
    new_results = []

    for match in future_matches:
        t1, t2 = match['team1'], match['team2']
        rf, of, ra, oa = match['runs_for'], match['overs_for'], match['runs_against'], match['overs_against']
        new_rows.append({'Team': t1, 'Runs For': rf, 'Overs For': of, 'Runs Against': ra, 'Overs Against': oa, 'M': 1})
        new_rows.append({'Team': t2, 'Runs For': ra, 'Overs For': oa, 'Runs Against': rf, 'Overs Against': of, 'M': 1})
        if rf > ra:
            new_results += [{'Team': t1, 'W': 1, 'L': 0, 'T': 0, 'N/R': 0, 'PT': 4}, {'Team': t2, 'W': 0, 'L': 1, 'T': 0, 'N/R': 0, 'PT': 0}]
        elif rf < ra:
            new_results += [{'Team': t1, 'W': 0, 'L': 1, 'T': 0, 'N/R': 0, 'PT': 0}, {'Team': t2, 'W': 1, 'L': 0, 'T': 0, 'N/R': 0, 'PT': 4}]
        else:
            new_results += [{'Team': t1, 'W': 0, 'L': 0, 'T': 1, 'N/R': 0, 'PT': 2}, {'Team': t2, 'W': 0, 'L': 0, 'T': 1, 'N/R': 0, 'PT': 2}]

    match_df = pd.DataFrame(new_rows)
    result_df = pd.DataFrame(new_results)

    updated = pd.concat([combined, match_df]).groupby('Team').agg({
        'M': 'sum', 'W': 'sum', 'L': 'sum', 'T': 'sum', 'N/R': 'sum', 'BP': 'sum', 'PT': 'sum',
        'Runs For': 'sum', 'Overs For': 'sum', 'Runs Against': 'sum', 'Overs Against': 'sum'
    }).reset_index()

    updated = pd.merge(updated, result_df.groupby('Team').sum().reset_index(), on='Team', how='outer').fillna(0)
    updated = updated.groupby('Team').sum(numeric_only=True).reset_index()

    updated['PT'] += updated['W'] * 4 + updated['T'] * 2 + updated['N/R'] * 2 + updated['BP']
    updated['NRR Balls For'] = updated['Overs For'].apply(cricket_overs_to_balls)
    updated['NRR Balls Against'] = updated['Overs Against'].apply(cricket_overs_to_balls)
    updated['Run Rate For'] = updated['Runs For'] / (updated['NRR Balls For'] / 6)
    updated['Run Rate Against'] = updated['Runs Against'] / (updated['NRR Balls Against'] / 6)
    updated['NRR'] = (updated['Run Rate For'] - updated['Run Rate Against']).round(3)

    final = updated[['Team', 'M', 'W', 'L', 'T', 'N/R', 'BP', 'PT', 'NRR', 'Runs For', 'Overs For', 'Runs Against', 'Overs Against']]
    final = final.sort_values(by=['PT', 'NRR'], ascending=[False, False]).reset_index(drop=True)
    final.index += 1

    north_final = final[final['Team'].isin(north_group)].reset_index(drop=True)
    south_final = final[~final['Team'].isin(north_group)].reset_index(drop=True)
    north_final.index += 1
    south_final.index += 1

    st.subheader("📍 North Group")
    st.dataframe(north_final, use_container_width=True)

    st.subheader("📍 South Group")
    st.dataframe(south_final, use_container_width=True)

    st.markdown("ℹ️ **Disclaimer**: Always enter **Overs For/Against** as 20 if the concerned team has been bowled out earlier than their full quota of overs.")
