import pandas as pd
import numpy as np
import streamlit as st

@st.cache_data
def load_weather_template(filepath="data/raw/weather_2025.parquet"):
    """
    Loads pre-processed Parquet data.
    This is effectively instant because:
    1. No CSV parsing
    2. No Date parsing
    3. No float calculation
    """
    try:
        # Load Parquet (Fastest method)
        df = pd.read_parquet(filepath)
        return df
    except FileNotFoundError:
        # Fallback if you haven't run the conversion script yet
        # (Useful if someone clones the repo and forgets to run the script)
        return _load_csv_fallback()

def _load_csv_fallback():
    # ... (Your original CSV loading code goes here as a backup) ...
    # ideally, you just commit the .parquet file to git and remove this fallback
    pass 

@st.cache_data
def get_fes_peak_demand(filepath="data/raw/fes2025_ed1_v006.csv", scenario="Holistic Transition", year="2030"):
    # Keep this as CSV for now as it's a tiny lookup, not worth converting
    df = pd.read_csv(filepath)
    mask = (df['Pathway'] == scenario) & \
           (df['Data item'].str.contains('Peak Customer Demand: Total Consumption', case=False)) & \
           (df['Peak/ Annual/ Minimum'] == 'Peak')
    row = df[mask]
    val = row[str(year)].values[0]
    unit = row['Unit'].values[0]
    return val * 1000 if unit == 'GW' else val

def create_2030_profile(weather_df, cp30_targets, peak_demand_2030_mw):
    # This logic remains exactly the same
    df = weather_df.copy()
    peak_2025 = df['Demand_MW'].max()
    scaling_factor = peak_demand_2030_mw / peak_2025
    df['Demand_2030_MW'] = df['Demand_MW'] * scaling_factor
    
    total_wind_cap_mw = (cp30_targets['Offshore Wind']['High'] + cp30_targets['Onshore Wind']['High']) * 1000
    df['Wind_Gen_2030_MW'] = df['Wind_LF'] * total_wind_cap_mw
    
    total_solar_cap_mw = cp30_targets['Solar']['High'] * 1000
    df['Solar_Gen_2030_MW'] = df['Solar_LF'] * total_solar_cap_mw
    
    nuclear_cap_mw = cp30_targets['Nuclear']['High'] * 1000
    df['Nuclear_Gen_2030_MW'] = nuclear_cap_mw
    
    df['Net_Demand_MW'] = df['Demand_2030_MW'] - (
        df['Wind_Gen_2030_MW'] + 
        df['Solar_Gen_2030_MW'] + 
        df['Nuclear_Gen_2030_MW']
    )
    return df