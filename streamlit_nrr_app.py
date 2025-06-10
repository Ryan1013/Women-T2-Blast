import streamlit as st
import pandas as pd

# ----------------------------------------
# Cached Data Loader
# ----------------------------------------
@st.cache_data
def load_base_data():
    return pd.read_csv("9JuneuptoWT20.csv")

# ----------------------------------------
# Helper Functions
# ----------------------------------------
def cricket_overs_to_balls(overs):
    overs_int = int(overs)
    balls_part = int(round((overs - overs_int + 1e-6) * 10))
    return overs_int * 6 + balls_part

def balls_to_cricket_overs(balls):
    overs = balls // 6
    rem_balls = balls % 6
    return float(f"{int(overs)}.{int(rem_balls)}")

def corrected_actual_overs(row):
    adjusted_ball = row['Actual Ball']
    if row['Legal Ball'] != 'Yes':
        adjusted_ball = max(0, adjusted_ball - 1)
    if adjusted_ball == 6:
        return float(f"{int(row['Over'])}.0")
    else:
        return float(f"{int(row['Over']) - 1}.{int(adjusted_ball)}")

def is_valid_overs(o):
    int_part = int(o)
    dec_part = round((o - int_part) * 10)
    return 0 <= dec_part <= 5

# ----------------------------------------
# Setup
# ----------------------------------------
st.title("Vitality Blast 2025 Standings Calculator")
st.markdown("Input results for **future games** below to get the updated standings.")

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

# ----------------------------------------
# Input Future Matches
# ----------------------------------------
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

# ----------------------------------------
# Process and Calculate
# ----------------------------------------
if st.button("Update Table"):
    if not overs_input_valid:
        st.error("❌ Please correct the invalid Overs inputs before proceeding.")
        st.stop()

    df = load_base_data()
    df.columns = df.columns.str.strip()
    df[['Team1', 'Team2']] = df['Match'].str.split(' v ', expand=True)
    df.sort_values(by=['Match', 'Date', 'Innings'], inplace=True)
    df['Next_Innings'] = df.groupby(['Match', 'Date'])['Innings'].shift(-1)
    mask = df['Innings'].ne(df['Next_Innings']) & (df.index < len(df))
    rows = df[mask].copy().reset_index(drop=True).drop(columns=['Next_Innings'])

    rows['Actual Ball'] = rows['Ball']
    rows['Actual Overs'] = rows.apply(corrected_actual_overs, axis=1)
    rows['NRR Overs'] = rows.apply(lambda r: 20.0 if r['Team Wickets'] == 10 else r['Actual Overs'], axis=1)
    rows['NRR Balls'] = rows['NRR Overs'].apply(cricket_overs_to_balls)

    for_summary = rows.groupby('Batting Team').agg({'Team Runs': 'sum', 'NRR Balls': 'sum'}).reset_index().rename(columns={
        'Batting Team': 'Team', 'Team Runs': 'Runs For', 'NRR Balls': 'NRR Balls For'
    })
    against_summary = rows.groupby('Bowling Team').agg({'Team Runs': 'sum', 'NRR Balls': 'sum'}).reset_index().rename(columns={
        'Bowling Team': 'Team', 'Team Runs': 'Runs Against', 'NRR Balls': 'NRR Balls Against'
    })

    summary = pd.merge(for_summary, against_summary, on='Team', how='outer')

    # Future Matches
    add_rows = []
    future_results = []
    for match in future_matches:
        t1, t2 = match['team1'], match['team2']
        rf, of, ra, oa = match['runs_for'], match['overs_for'], match['runs_against'], match['overs_against']
        b_for = cricket_overs_to_balls(of)
        b_against = cricket_overs_to_balls(oa)
        add_rows += [
            {'Team': t1, 'Runs For': rf, 'NRR Balls For': b_for, 'Runs Against': ra, 'NRR Balls Against': b_against},
            {'Team': t2, 'Runs For': ra, 'NRR Balls For': b_against, 'Runs Against': rf, 'NRR Balls Against': b_for}
        ]
        if rf > ra:
            future_results += [{'Team': t1, 'W': 1, 'L': 0, 'T': 0, 'N/R': 0}, {'Team': t2, 'W': 0, 'L': 1, 'T': 0, 'N/R': 0}]
        elif rf < ra:
            future_results += [{'Team': t1, 'W': 0, 'L': 1, 'T': 0, 'N/R': 0}, {'Team': t2, 'W': 1, 'L': 0, 'T': 0, 'N/R': 0}]
        else:
            future_results += [{'Team': t1, 'W': 0, 'L': 0, 'T': 1, 'N/R': 0}, {'Team': t2, 'W': 0, 'L': 0, 'T': 1, 'N/R': 0}]

    future_df = pd.DataFrame(add_rows)
    summary = pd.concat([summary, future_df]).groupby('Team').agg({
        'Runs For': 'sum', 'NRR Balls For': 'sum', 'Runs Against': 'sum', 'NRR Balls Against': 'sum'
    }).reset_index()

    summary['Overs For'] = summary['NRR Balls For'].apply(balls_to_cricket_overs)
    summary['Overs Against'] = summary['NRR Balls Against'].apply(balls_to_cricket_overs)
    summary['Run Rate For'] = summary['Runs For'] / (summary['NRR Balls For'] / 6)
    summary['Run Rate Against'] = summary['Runs Against'] / (summary['NRR Balls Against'] / 6)
    summary['NRR'] = (summary['Run Rate For'] - summary['Run Rate Against']).round(3)

    match_results = []
    for (match, date), group in rows.groupby(['Match', 'Date']):
        if len(group) == 2:
            t1, t2 = group.iloc[0]['Batting Team'], group.iloc[1]['Batting Team']
            r1, r2 = group.iloc[0]['Team Runs'], group.iloc[1]['Team Runs']
            if r1 > r2:
                match_results += [{'Team': t1, 'W': 1, 'L': 0, 'T': 0, 'N/R': 0}, {'Team': t2, 'W': 0, 'L': 1, 'T': 0, 'N/R': 0}]
            elif r1 == r2:
                match_results += [{'Team': t1, 'W': 0, 'L': 0, 'T': 1, 'N/R': 0}, {'Team': t2, 'W': 0, 'L': 0, 'T': 1, 'N/R': 0}]
            else:
                match_results += [{'Team': t1, 'W': 0, 'L': 1, 'T': 0, 'N/R': 0}, {'Team': t2, 'W': 1, 'L': 0, 'T': 0, 'N/R': 0}]
        else:
            t1 = group.iloc[0]['Batting Team']
            t2 = group.iloc[0]['Bowling Team']
            match_results += [{'Team': t1, 'W': 0, 'L': 0, 'T': 0, 'N/R': 1}, {'Team': t2, 'W': 0, 'L': 0, 'T': 0, 'N/R': 1}]

    match_df = pd.DataFrame(match_results + future_results)
    outcome = match_df.groupby('Team').sum().reset_index()
    outcome['M'] = outcome[['W', 'L', 'T', 'N/R']].sum(axis=1)
    outcome['BP'] = outcome['Team'].map({
        'Middlesex Women': 1, 'Yorkshire Women': 2, 'Derbyshire Falcons Women': 1
    }).fillna(0).astype(int)
    outcome['PT'] = outcome['W'] * 4 + outcome['T'] * 2 + outcome['N/R'] * 2 + outcome['BP']

    final = pd.merge(outcome, summary[['Team', 'NRR', 'Runs For', 'Overs For', 'Runs Against', 'Overs Against']], on='Team', how='outer')
    final = final[['Team', 'M', 'W', 'L', 'T', 'N/R', 'BP', 'PT', 'NRR', 'Runs For', 'Overs For', 'Runs Against', 'Overs Against']]
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
