import streamlit as st
import pandas as pd
import math

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

# Initialize team list
team_list = [
    'Middlesex Women', 'Yorkshire Women', 'Northamptonshire Steelbacks Women',
    'Derbyshire Falcons Women', 'Glamorgan Women', 'Sussex Sharks Women',
    'Worcestershire Rapids Women', 'Leicestershire Foxes Women',
    'Kent Women', 'Gloucestershire Women'
]

st.title("Vitality Blast 2025 Standings Calculator")
st.markdown("Input results for a **future game** below to get the updated standings.")

team1 = st.selectbox("Team 1 (For)", team_list)
team2 = st.selectbox("Team 2 (Against)", [t for t in team_list if t != team1])
runs_for = st.number_input("Runs For", min_value=0)
overs_for = st.number_input("Overs For (e.g., 19.5)", min_value=0.0, step=0.1)
runs_against = st.number_input("Runs Against", min_value=0)
overs_against = st.number_input("Overs Against (e.g., 20.0)", min_value=0.0, step=0.1)

if st.button("Update Table"):
    df = load_base_data()
    df.columns = df.columns.str.strip()
    df[['Team1', 'Team2']] = df['Match'].str.split(' v ', expand=True)
    df.sort_values(by=['Match', 'Date', 'Innings'], inplace=True)
    df['Next_Innings'] = df.groupby(['Match', 'Date'])['Innings'].shift(-1)
    mask = df['Innings'].ne(df['Next_Innings']) & (df.index < len(df))
    rows = df[mask].copy().reset_index(drop=True).drop(columns=['Next_Innings'])

    rows['Actual Ball'] = rows['Ball']
    rows['Actual Overs'] = rows.apply(lambda row: float(f"{int(row['Over']) - 1}.{int(row['Actual Ball'])}") if row['Legal Ball'] != 'Yes' else float(f"{int(row['Over'])}.{int(row['Actual Ball'])}") if row['Actual Ball'] == 6 else float(f"{int(row['Over']) - 1}.{int(row['Actual Ball'])}"), axis=1)
    rows['NRR Overs'] = rows.apply(lambda r: 20.0 if r['Team Wickets'] == 10 else r['Actual Overs'], axis=1)
    rows['NRR Balls'] = rows['NRR Overs'].apply(cricket_overs_to_balls)

    # For and Against summaries
    for_summary = rows.groupby('Batting Team').agg({'Team Runs': 'sum', 'NRR Balls': 'sum'}).reset_index().rename(columns={'Batting Team': 'Team', 'Team Runs': 'Runs For', 'NRR Balls': 'NRR Balls For'})
    for_summary['Overs For'] = for_summary['NRR Balls For'].apply(balls_to_cricket_overs)
    for_summary.drop(columns='NRR Balls For', inplace=True)

    against_summary = rows.groupby('Bowling Team').agg({'Team Runs': 'sum', 'NRR Balls': 'sum'}).reset_index().rename(columns={'Bowling Team': 'Team', 'Team Runs': 'Runs Against', 'NRR Balls': 'NRR Balls Against'})
    against_summary['Overs Against'] = against_summary['NRR Balls Against'].apply(balls_to_cricket_overs)
    against_summary.drop(columns='NRR Balls Against', inplace=True)

    summary = pd.merge(for_summary, against_summary, on='Team', how='outer')

    # Add future match
    add_df = pd.DataFrame({
        'Team': [team1, team2],
        'Runs For': [runs_for, runs_against],
        'Overs For': [overs_for, overs_against],
        'Runs Against': [runs_against, runs_for],
        'Overs Against': [overs_against, overs_for]
    })

    summary = pd.concat([summary, add_df]).groupby('Team').agg({
        'Runs For': 'sum', 'Overs For': 'sum',
        'Runs Against': 'sum', 'Overs Against': 'sum'
    }).reset_index()

    summary['NRR Balls For'] = summary['Overs For'].apply(cricket_overs_to_balls)
    summary['NRR Balls Against'] = summary['Overs Against'].apply(cricket_overs_to_balls)
    summary['Run Rate For'] = summary['Runs For'] / (summary['NRR Balls For'] / 6)
    summary['Run Rate Against'] = summary['Runs Against'] / (summary['NRR Balls Against'] / 6)
    summary['NRR'] = (summary['Run Rate For'] - summary['Run Rate Against']).round(3)

    # Win/Loss Summary from actual data
    match_results = []
    innings_grouped = rows.groupby(['Match', 'Date'])
    for (match, date), group in innings_grouped:
        if len(group) == 2:
            t1 = group.iloc[0]['Batting Team']
            t2 = group.iloc[1]['Batting Team']
            r1 = group.iloc[0]['Team Runs']
            r2 = group.iloc[1]['Team Runs']
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
    match_df = pd.DataFrame(match_results)
    outcome = match_df.groupby('Team').sum().reset_index()

    # Add outcome for new match
    if runs_for > runs_against:
        new_result = pd.DataFrame({'Team': [team1, team2], 'W': [1, 0], 'L': [0, 1], 'T': [0, 0], 'N/R': [0, 0]})
    elif runs_for < runs_against:
        new_result = pd.DataFrame({'Team': [team1, team2], 'W': [0, 1], 'L': [1, 0], 'T': [0, 0], 'N/R': [0, 0]})
    else:
        new_result = pd.DataFrame({'Team': [team1, team2], 'W': [0, 0], 'L': [0, 0], 'T': [1, 1], 'N/R': [0, 0]})
    outcome = pd.concat([outcome, new_result]).groupby('Team').sum().reset_index()
    outcome['M'] = outcome[['W', 'L', 'T', 'N/R']].sum(axis=1)
    outcome['BP'] = outcome['Team'].map({'Middlesex Women': 1, 'Yorkshire Women': 2, 'Derbyshire Falcons Women': 1}).fillna(0).astype(int)
    outcome['PT'] = outcome['W'] * 4 + outcome['T'] * 2 + outcome['N/R'] * 2 + outcome['BP']

    final = pd.merge(outcome, summary[['Team', 'NRR', 'Runs For', 'Overs For', 'Runs Against', 'Overs Against']], on='Team', how='outer')
    final = final[['Team', 'M', 'W', 'L', 'T', 'N/R', 'BP', 'PT', 'NRR', 'Runs For', 'Overs For', 'Runs Against', 'Overs Against']]
    final = final.sort_values(by=['PT', 'NRR'], ascending=[False, False]).reset_index(drop=True)
    final.index += 1

    st.subheader("📊 Updated Standings Table")
    st.dataframe(final, use_container_width=True)
