# Logic to clean FES & Historic data and prepare it for the model
import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st

@st.cache_data
def load_weather_template(filepath="data/raw/demanddata_2025.csv"):
    """
    Loads 2025 historic data to create Unitized Load Factors (0-1) for Wind, Solar, and Demand Shape.
    Returns a clean DataFrame with a DatetimeIndex.
    Cached to prevent re-loading CSV on every slider change.
    """
    # Load data
    df = pd.read_csv(filepath)
    
    # 1. Date Parsing
    # NESO data uses 'SETTLEMENT_DATE' (YYYY-MM-DD) and 'SETTLEMENT_PERIOD' (1-48)
    # We specify the format explicitly to prevent parsing errors and improve speed.
    df['Datetime'] = pd.to_datetime(df['SETTLEMENT_DATE'], format='%Y-%m-%d') + \
                     pd.to_timedelta((df['SETTLEMENT_PERIOD'] - 1) * 30, unit='m')
    
    df = df.set_index('Datetime')
    
    # 2. Calculate Load Factors (Avoid division by zero)
    # Wind LF = Generated / Capacity
    # Note: We use 'EMBEDDED' columns as a proxy for the weather pattern
    df['Wind_LF'] = df['EMBEDDED_WIND_GENERATION'] / df['EMBEDDED_WIND_CAPACITY']
    df['Wind_LF'] = df['Wind_LF'].fillna(0).clip(0, 1)
    
    # Solar LF
    df['Solar_LF'] = df['EMBEDDED_SOLAR_GENERATION'] / df['EMBEDDED_SOLAR_CAPACITY']
    df['Solar_LF'] = df['Solar_LF'].fillna(0).clip(0, 1)
    
    # 3. Clean Demand (National Demand)
    # ND is 'National Demand' (Consumer load), excluding pumping/exports.
    # This is the correct baseline for 'Passive Demand'.
    df['Demand_MW'] = df['ND']
    
    # Return only the essential columns
    return df[['Demand_MW', 'Wind_LF', 'Solar_LF']]

@st.cache_data
def get_fes_peak_demand(filepath="data/raw/fes2025_ed1_v006.csv", scenario="Holistic Transition", year="2030"):
    """
    Retrieves the projected Peak Demand (MW) for a specific year and scenario.
    Cached to prevent re-reading the FES CSV on every interaction.
    """
    df = pd.read_csv(filepath)
    
    # Filter for the correct Peak Demand metric
    # 'GBFES Peak Customer Demand: Total Consumption plus Losses ' is the aggregate peak
    mask = (df['Pathway'] == scenario) & \
           (df['Data item'].str.contains('Peak Customer Demand: Total Consumption', case=False)) & \
           (df['Peak/ Annual/ Minimum'] == 'Peak')
           
    row = df[mask]
    
    if row.empty:
        raise ValueError(f"No data found for {scenario} Peak Demand in {year}")
    
    # Extract value (Columns are years)
    val = row[str(year)].values[0]
    unit = row['Unit'].values[0]
    
    # FES usually reports Peak in GW, but let's be safe
    if unit == 'GW':
        return val * 1000  # Convert to MW
    elif unit == 'MW':
        return val
    else:
        # Fallback if unit is missing, usually GW in FES ED1
        return val * 1000

def create_2030_profile(weather_df, cp30_targets, peak_demand_2030_mw):
    """
    Scales the 2025 weather template to 2030 dimensions using CP30 Targets.
    This function is fast (vectorized math) and does not need internal caching 
    if the inputs are managed by the main app cache.
    """
    df = weather_df.copy()
    
    # 1. Scale Demand
    # We maintain the *shape* of 2025, but stretch the *amplitude* to hit 2030 Peak.
    peak_2025 = df['Demand_MW'].max()
    scaling_factor = peak_demand_2030_mw / peak_2025
    df['Demand_2030_MW'] = df['Demand_MW'] * scaling_factor
    
    # 2. Build Generation Profiles from CP30 Targets (GW -> MW)
    # Wind: We apply the 2025 Wind Load Factor to the 2030 Total Capacity
    # (Offshore + Onshore High Ambition)
    total_wind_cap_mw = (cp30_targets['Offshore Wind']['High'] + cp30_targets['Onshore Wind']['High']) * 1000
    df['Wind_Gen_2030_MW'] = df['Wind_LF'] * total_wind_cap_mw
    
    # Solar
    total_solar_cap_mw = cp30_targets['Solar']['High'] * 1000
    df['Solar_Gen_2030_MW'] = df['Solar_LF'] * total_solar_cap_mw
    
    # Nuclear (Baseload)
    # Assumed flat for the base profile (outages can be modeled separately)
    nuclear_cap_mw = cp30_targets['Nuclear']['High'] * 1000
    df['Nuclear_Gen_2030_MW'] = nuclear_cap_mw
    
    # 3. Calculate The Gap (Net Demand)
    # Net Demand > 0 means we need Flexibility (Batteries/Gas)
    # Net Demand < 0 means we have Excess (Charge Batteries/Curtail)
    df['Net_Demand_MW'] = df['Demand_2030_MW'] - (
        df['Wind_Gen_2030_MW'] + 
        df['Solar_Gen_2030_MW'] + 
        df['Nuclear_Gen_2030_MW']
    )
    
    return df

# --- Verification Block (Run this file directly to test) ---
if __name__ == "__main__":
    try:
        from cp30_targets import CP30_TARGETS
        
        print("1. Loading Weather Template...")
        weather = load_weather_template()
        print(f"   Loaded {len(weather)} half-hourly periods.")
        
        print("2. Getting FES 2030 Peak...")
        peak_2030 = get_fes_peak_demand()
        print(f"   2030 Peak Demand Target: {peak_2030:,.0f} MW")
        
        print("3. Creating 2030 Scenario...")
        scenario_df = create_2030_profile(weather, CP30_TARGETS, peak_2030)
        
        print("\n--- 2030 Scenario Snapshot ---")
        print(scenario_df[['Demand_2030_MW', 'Net_Demand_MW']].describe().round(0))
        
        # Quick Dunkelflaute Check
        max_gap = scenario_df['Net_Demand_MW'].max()
        print(f"\nSevere Event Detected: Maximum Flexibility Gap = {max_gap:,.0f} MW")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Ensure files are in 'data/raw/' and cp30_targets.py is in 'src/'")