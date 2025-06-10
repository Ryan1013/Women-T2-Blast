import streamlit as st
import pandas as pd

# -----------------------------
# Preprocessing Step
# -----------------------------
@st.cache_data
def load_and_preprocess():
    data = pd.read_csv("9JuneuptoWT20.csv")
    data.columns = data.columns.str.strip()

    def cricket_overs_to_balls(overs):
        overs_int = int(overs)
        balls_part = int(round((overs - overs_int) * 10))
        return overs_int * 6 + balls_part

    def balls_to_cricket_overs(balls):
        overs = balls // 6
        rem_balls = balls % 6
        return float(f"{int(overs)}.{int(rem_balls)}")

    def corrected_actual_overs(row):
        adjusted_ball = row['Ball']
        if row['Legal Ball'] != 'Yes':
            adjusted_ball = max(0, adjusted_ball - 1)
        if adjusted_ball == 6:
            return float(f"{int(row['Over'])}.0")
        else:
            return float(f"{int(row['Over']) - 1}.{int(adjusted_ball)}")

    data[['Team1', 'Team2']] = data['Match'].str.split(' v ', expand=True)
    data.sort_values(by=['Match', 'Date', 'Innings'], inplace=True)
    data['Next_Innings'] = data.groupby(['Match', 'Date'])['Innings'].shift(-1)
    mask = data['Innings'].ne(data['Next_Innings']) & (data.index < len(data))
    rows = data[mask].copy().reset_index(drop=True).drop(columns=['Next_Innings'])

    rows['Actual Overs'] = rows.apply(corrected_actual_overs, axis=1)
    rows['NRR Overs'] = rows.apply(lambda r: 20.0 if r['Team Wickets'] == 10 else r['Actual Overs'], axis=1)
    rows['NRR Balls'] = rows['NRR Overs'].apply(cricket_overs_to_balls)

    for_summary = rows.groupby('Batting Team').agg({
        'Team Runs': 'sum', 'NRR Balls': 'sum'
    }).reset_index().rename(columns={
        'Batting Team': 'Team', 'Team Runs': 'Runs For', 'NRR Balls': 'NRR Balls For'
    })
    for_summary['Overs For'] = for_summary['NRR Balls For'].apply(balls_to_cricket_overs)
    for_summary.drop(columns='NRR Balls For', inplace=True)

    against_summary = rows.groupby('Bowling Team').agg({
        'Team Runs': 'sum', 'NRR Balls': 'sum'
    }).reset_index().rename(columns={
        'Bowling Team': 'Team', 'Team Runs': 'Runs Against', 'NRR Balls': 'NRR Balls Against'
    })
    against_summary['Overs Against'] = against_summary['NRR Balls Against'].apply(balls_to_cricket_overs)
    against_summary.drop(columns='NRR Balls Against', inplace=True)

    team_summary = pd.merge(for_summary, against_summary, on='Team', how='outer')

    team_summary['NRR Balls For'] = team_summary['Overs For'].apply(cricket_overs_to_balls)
    team_summary['NRR Balls Against'] = team_summary['Overs Against'].apply(cricket_overs_to_balls)
    team_summary['Run Rate For'] = team_summary['Runs For'] / (team_summary['NRR Balls For'] / 6)
    team_summary['Run Rate Against'] = team_summary['Runs Against'] / (team_summary['NRR Balls Against'] / 6)
    team_summary['NRR'] = (team_summary['Run Rate For'] - team_summary['Run Rate Against']).round(3)

    match_results = []
    innings_grouped = rows.groupby(['Match', 'Date'])

    for (match, date), group in innings_grouped:
        if len(group) == 2:
            t1 = group.iloc[0]['Batting Team']
            t2 = group.iloc[1]['Batting Team']
            r1 = group.iloc[0]['Team Runs']
            r2 = group.iloc[1]['Team Runs']
            if r1 > r2:
                match_results += [{'Team': t1, 'W': 1, 'L': 0, 'T': 0, 'N/R': 0},
                                  {'Team': t2, 'W': 0, 'L': 1, 'T': 0, 'N/R': 0}]
            elif r1 < r2:
                match_results += [{'Team': t1, 'W': 0, 'L': 1, 'T': 0, 'N/R': 0},
                                  {'Team': t2, 'W': 1, 'L': 0, 'T': 0, 'N/R': 0}]
            else:
                match_results += [{'Team': t1, 'W': 0, 'L': 0, 'T': 1, 'N/R': 0},
                                  {'Team': t2, 'W': 0, 'L': 0, 'T': 1, 'N/R': 0}]
        else:
            t1 = group.iloc[0]['Batting Team']
            t2 = group.iloc[0]['Bowling Team']
            match_results += [{'Team': t1, 'W': 0, 'L': 0, 'T': 0, 'N/R': 1},
                              {'Team': t2, 'W': 0, 'L': 0, 'T': 0, 'N/R': 1}]

    results_df = pd.DataFrame(match_results)
    summary_stats = results_df.groupby('Team').sum().reset_index()
    summary_stats['M'] = summary_stats[['W', 'L', 'T', 'N/R']].sum(axis=1)
    summary_stats['BP'] = summary_stats['Team'].map({
        'Middlesex Women': 1, 'Yorkshire Women': 2, 'Derbyshire Falcons Women': 1
    }).fillna(0).astype(int)
    summary_stats['PT'] = summary_stats['W'] * 4 + summary_stats['T'] * 2 + summary_stats['N/R'] * 2 + summary_stats['BP']

    base_table = pd.merge(summary_stats, team_summary, on='Team', how='outer')
    base_table = base_table[['Team', 'M', 'W', 'L', 'T', 'N/R', 'BP', 'PT',
                             'NRR', 'Runs For', 'Overs For', 'Runs Against', 'Overs Against']]
    return base_table

# -----------------------------
# Streamlit UI
# -----------------------------
base_data = load_and_preprocess()

north_group = [
    'Yorkshire Women', 'Northamptonshire Steelbacks Women',
    'Derbyshire Falcons Women', 'Leicestershire Foxes Women',
    'Worcestershire Rapids Women'
]

team_list = base_data['Team'].tolist()

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

    def cricket_overs_to_balls(overs):
        overs_int = int(overs)
        balls_part = int(round((overs - overs_int) * 10))
        return overs_int * 6 + balls_part

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
