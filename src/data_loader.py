import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st

@st.cache_data
def load_weather_template(filepath="data/raw/weather_2025.parquet"):
    """
    Tries to load the fast Parquet file. 
    If missing, falls back to the slower CSV method automatically.
    """
    try:
        # Try loading the fast file
        df = pd.read_parquet(filepath)
        return df
    except (FileNotFoundError, ImportError):
        # If file missing or pyarrow not installed, use CSV
        return _load_csv_fallback()

def _load_csv_fallback(filepath="data/raw/demanddata_2025.csv"):
    """
    The original CSV loading logic. Used if Parquet isn't available.
    """
    # Load data
    df = pd.read_csv(filepath)
    
    # 1. Date Parsing
    df['Datetime'] = pd.to_datetime(df['SETTLEMENT_DATE'], format='%Y-%m-%d') + \
                     pd.to_timedelta((df['SETTLEMENT_PERIOD'] - 1) * 30, unit='m')
    
    df = df.set_index('Datetime')
    
    # 2. Calculate Load Factors
    df['Wind_LF'] = df['EMBEDDED_WIND_GENERATION'] / df['EMBEDDED_WIND_CAPACITY']
    df['Wind_LF'] = df['Wind_LF'].fillna(0).clip(0, 1)
    
    df['Solar_LF'] = df['EMBEDDED_SOLAR_GENERATION'] / df['EMBEDDED_SOLAR_CAPACITY']
    df['Solar_LF'] = df['Solar_LF'].fillna(0).clip(0, 1)
    
    # 3. Clean Demand
    df['Demand_MW'] = df['ND']
    
    # Return only the essential columns
    return df[['Demand_MW', 'Wind_LF', 'Solar_LF']]

@st.cache_data
def get_fes_peak_demand(filepath="data/raw/fes2025_ed1_v006.csv", scenario="Holistic Transition", year="2030"):
    """
    Retrieves the projected Peak Demand (MW) for a specific year and scenario.
    """
    df = pd.read_csv(filepath)
    
    mask = (df['Pathway'] == scenario) & \
           (df['Data item'].str.contains('Peak Customer Demand: Total Consumption', case=False)) & \
           (df['Peak/ Annual/ Minimum'] == 'Peak')
           
    row = df[mask]
    
    if row.empty:
        raise ValueError(f"No data found for {scenario} Peak Demand in {year}")
    
    # Extract value
    val = row[str(year)].values[0]
    unit = row['Unit'].values[0]
    
    if unit == 'GW':
        return val * 1000
    elif unit == 'MW':
        return val
    else:
        return val * 1000

def create_2030_profile(weather_df, cp30_targets, peak_demand_2030_mw):
    """
    Scales the 2025 weather template to 2030 dimensions using CP30 Targets.
    """
    df = weather_df.copy()
    
    # 1. Scale Demand
    peak_2025 = df['Demand_MW'].max()
    scaling_factor = peak_demand_2030_mw / peak_2025
    df['Demand_2030_MW'] = df['Demand_MW'] * scaling_factor
    
    # 2. Build Generation Profiles
    total_wind_cap_mw = (cp30_targets['Offshore Wind']['High'] + cp30_targets['Onshore Wind']['High']) * 1000
    df['Wind_Gen_2030_MW'] = df['Wind_LF'] * total_wind_cap_mw
    
    total_solar_cap_mw = cp30_targets['Solar']['High'] * 1000
    df['Solar_Gen_2030_MW'] = df['Solar_LF'] * total_solar_cap_mw
    
    nuclear_cap_mw = cp30_targets['Nuclear']['High'] * 1000
    df['Nuclear_Gen_2030_MW'] = nuclear_cap_mw
    
    # 3. Calculate The Gap
    df['Net_Demand_MW'] = df['Demand_2030_MW'] - (
        df['Wind_Gen_2030_MW'] + 
        df['Solar_Gen_2030_MW'] + 
        df['Nuclear_Gen_2030_MW']
    )
    
    return df