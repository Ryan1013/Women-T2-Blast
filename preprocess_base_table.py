import pandas as pd

# Load the CSV
data = pd.read_csv("9JuneuptoWT20.csv")
data.columns = data.columns.str.strip()

# Define helper functions
def cricket_overs_to_balls(overs):
    overs_int = int(overs)
    balls_part = int(round((overs - overs_int) * 10))
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

# Preprocess match innings
data[['Team1', 'Team2']] = data['Match'].str.split(' v ', expand=True)
data.sort_values(by=['Match', 'Date', 'Innings'], inplace=True)
data['Next_Innings'] = data.groupby(['Match', 'Date'])['Innings'].shift(-1)
mask = data['Innings'].ne(data['Next_Innings']) & (data.index < len(data))
rows_before_change = data[mask].copy().reset_index(drop=True).drop(columns=['Next_Innings'])

rows_before_change['Actual Overs'] = rows_before_change.apply(corrected_actual_overs, axis=1)
rows_before_change['NRR Overs'] = rows_before_change.apply(
    lambda row: 20.0 if row['Team Wickets'] == 10 else row['Actual Overs'], axis=1
)
rows_before_change['NRR Balls'] = rows_before_change['NRR Overs'].apply(cricket_overs_to_balls)

# Compute team summaries
for_summary = rows_before_change.groupby('Batting Team').agg({
    'Team Runs': 'sum',
    'NRR Balls': 'sum'
}).reset_index().rename(columns={
    'Batting Team': 'Team',
    'Team Runs': 'Runs For',
    'NRR Balls': 'NRR Balls For'
})
for_summary['Overs For'] = for_summary['NRR Balls For'].apply(balls_to_cricket_overs)
for_summary.drop(columns='NRR Balls For', inplace=True)

against_summary = rows_before_change.groupby('Bowling Team').agg({
    'Team Runs': 'sum',
    'NRR Balls': 'sum'
}).reset_index().rename(columns={
    'Bowling Team': 'Team',
    'Team Runs': 'Runs Against',
    'NRR Balls': 'NRR Balls Against'
})
against_summary['Overs Against'] = against_summary['NRR Balls Against'].apply(balls_to_cricket_overs)
against_summary.drop(columns='NRR Balls Against', inplace=True)

team_summary = pd.merge(for_summary, against_summary, on='Team', how='outer')
team_summary['NRR Balls For'] = team_summary['Overs For'].apply(cricket_overs_to_balls)
team_summary['NRR Balls Against'] = team_summary['Overs Against'].apply(cricket_overs_to_balls)
team_summary['Run Rate For'] = team_summary['Runs For'] / (team_summary['NRR Balls For'] / 6)
team_summary['Run Rate Against'] = team_summary['Runs Against'] / (team_summary['NRR Balls Against'] / 6)
team_summary['NRR'] = (team_summary['Run Rate For'] - team_summary['Run Rate Against']).round(3)
final_nrr_table = team_summary[['Team', 'Runs For', 'Overs For', 'Runs Against', 'Overs Against', 'NRR']]

# Match results
match_results = []
innings_grouped = rows_before_change.groupby(['Match', 'Date'])

for (match, date), group in innings_grouped:
    if len(group) == 2:
        team1 = group.iloc[0]['Batting Team']
        team2 = group.iloc[1]['Batting Team']
        runs1 = group.iloc[0]['Team Runs']
        runs2 = group.iloc[1]['Team Runs']

        if runs1 > runs2:
            match_results.extend([
                {'Team': team1, 'W': 1, 'L': 0, 'T': 0, 'N/R': 0},
                {'Team': team2, 'W': 0, 'L': 1, 'T': 0, 'N/R': 0},
            ])
        elif runs1 == runs2:
            match_results.extend([
                {'Team': team1, 'W': 0, 'L': 0, 'T': 1, 'N/R': 0},
                {'Team': team2, 'W': 0, 'L': 0, 'T': 1, 'N/R': 0},
            ])
        else:
            match_results.extend([
                {'Team': team1, 'W': 0, 'L': 1, 'T': 0, 'N/R': 0},
                {'Team': team2, 'W': 1, 'L': 0, 'T': 0, 'N/R': 0},
            ])
    else:
        team1 = group.iloc[0]['Batting Team']
        team2 = group.iloc[0]['Bowling Team']
        match_results.extend([
            {'Team': team1, 'W': 0, 'L': 0, 'T': 0, 'N/R': 1},
            {'Team': team2, 'W': 0, 'L': 0, 'T': 0, 'N/R': 1},
        ])

results_df = pd.DataFrame(match_results)
summary_stats = results_df.groupby('Team').sum().reset_index()
summary_stats['M'] = summary_stats[['W', 'L', 'T', 'N/R']].sum(axis=1)
summary_stats['PT'] = summary_stats['W'] * 4 + summary_stats['T'] * 2 + summary_stats['N/R'] * 2

final_merged = pd.merge(summary_stats, final_nrr_table, on='Team', how='outer')

# Add bonus points
bonus_points = {
    'Middlesex Women': 1,
    'Yorkshire Women': 2,
    'Derbyshire Falcons Women': 1
}
final_merged['BP'] = final_merged['Team'].map(bonus_points).fillna(0).astype(int)
final_merged['PT'] += final_merged['BP']

final_display = final_merged[
    ['Team', 'M', 'W', 'L', 'T', 'N/R', 'BP', 'PT', 'NRR',
     'Runs For', 'Overs For', 'Runs Against', 'Overs Against']
].sort_values(by=['PT', 'NRR'], ascending=[False, False]).reset_index(drop=True)

north_group = ['Yorkshire Women', 'Northamptonshire Steelbacks Women', 'Derbyshire Falcons Women', 
               'Leicestershire Foxes Women', 'Worcestershire Rapids Women']
north_table = final_display[final_display['Team'].isin(north_group)].reset_index(drop=True)
south_table = final_display[~final_display['Team'].isin(north_group)].reset_index(drop=True)

# Save to CSV for Streamlit
north_table.to_csv("north_table.csv", index=False)
south_table.to_csv("south_table.csv", index=False)