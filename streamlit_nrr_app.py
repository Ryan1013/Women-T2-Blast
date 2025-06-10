import streamlit as st
import pandas as pd

from nrrvt20w import get_updated_tables

if st.button("Update Table"):
    # Validation: Overs can only end in .0 to .5
    overs_error = False
    for match in future_matches:
        for key in ['overs_for', 'overs_against']:
            overs = match[key]
            overs_decimal = overs - int(overs)
            if overs_decimal > 0.5 or (round(overs_decimal * 10) % 1 != 0):
                overs_error = True
                break
        if overs_error:
            break

    if overs_error:
        st.error("❌ Overs can only end in .0 to .5 (e.g., 18.0 to 18.5 are valid, but not 18.6)")
    else:
        df = load_base_data()

team_list = [
    'Middlesex Women', 'Yorkshire Women', 'Northamptonshire Steelbacks Women',
    'Derbyshire Falcons Women', 'Glamorgan Women', 'Sussex Sharks Women',
    'Worcestershire Rapids Women', 'Leicestershire Foxes Women',
    'Kent Women', 'Gloucestershire Women'
]

st.title("Vitality Blast 2025 Standings Calculator")
st.markdown("Input results for **future games** below to get the updated standings.")

num_matches = st.number_input("Number of future matches to add", min_value=1, value=1, step=1)

valid_overs = [round(x * 0.1, 1) for x in range(0, 6)]  # .0 to .5 values only
overs_choices = [x + y for x in range(0, 21) for y in valid_overs]

future_matches = []

for i in range(num_matches):
    st.markdown(f"### Match {i+1}")
    team1 = st.selectbox(f"Team 1 (For) - Match {i+1}", team_list, key=f"team1_{i}")
    team2 = st.selectbox(f"Team 2 (Against) - Match {i+1}", [t for t in team_list if t != team1], key=f"team2_{i}")
    runs_for = st.number_input(f"Runs For - Match {i+1}", min_value=0, key=f"runs_for_{i}")
    overs_for = st.selectbox(f"Overs For - Match {i+1}", overs_choices, key=f"overs_for_{i}")
    runs_against = st.number_input(f"Runs Against - Match {i+1}", min_value=0, key=f"runs_against_{i}")
    overs_against = st.selectbox(f"Overs Against - Match {i+1}", overs_choices, key=f"overs_against_{i}")

    future_matches.append({
        'team1': team1, 'team2': team2,
        'runs_for': runs_for, 'overs_for': overs_for,
        'runs_against': runs_against, 'overs_against': overs_against
    })

if st.button("Update Table"):
    df = load_base_data()
    north_table, south_table = get_updated_tables(df, future_matches)

    st.subheader("📍 North Group")
    st.dataframe(north_table, use_container_width=True)

    st.subheader("📍 South Group")
    st.dataframe(south_table, use_container_width=True)

    st.markdown("ℹ️ **Disclaimer**: Always enter **Overs For/Against** as 20 if the concerned team has been bowled out earlier than their full quota of overs.")
