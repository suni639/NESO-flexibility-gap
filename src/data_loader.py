import pandas as pd
import numpy as np
import streamlit as st
import os

# Define paths relative to the root directory
PARQUET_PATH = "data/raw/weather_2025.parquet"
CSV_PATH = "data/raw/demanddata_2025.csv"

@st.cache_data
def load_weather_template():
    """
    Smart Loader:
    1. Checks for optimized 'weather_2025.parquet'.
    2. If found -> Loads instantly.
    3. If missing -> Loads CSV, converts to Parquet, saves it, and returns data.
    """
    # 1. Try Loading Parquet (Fast Path)
    if os.path.exists(PARQUET_PATH):
        try:
            df = pd.read_parquet(PARQUET_PATH)
            return df
        except Exception:
            pass # If corrupt, ignore and use fallback

    # 2. Fallback to CSV & Optimize (Slow Path - Runs Once)
    if not os.path.exists(CSV_PATH):
        st.error(f"CRITICAL ERROR: Could not find '{CSV_PATH}'. Check 'data/raw/' folder.")
        return pd.DataFrame()

    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return pd.DataFrame()

    # --- Data Processing ---
    # Parse Dates (The slow part)
    # coerce errors to handle any bad rows safely
    df['Datetime'] = pd.to_datetime(df['SETTLEMENT_DATE'], format='%Y-%m-%d', errors='coerce') + \
                     pd.to_timedelta((df['SETTLEMENT_PERIOD'] - 1) * 30, unit='m')
    
    # Drop invalid rows and set index
    df = df.dropna(subset=['Datetime']).set_index('Datetime')

    # Calculate Load Factors
    if 'EMBEDDED_WIND_GENERATION' in df.columns:
        df['Wind_LF'] = df['EMBEDDED_WIND_GENERATION'] / df['EMBEDDED_WIND_CAPACITY']
        df['Wind_LF'] = df['Wind_LF'].fillna(0).clip(0, 1)
    else:
        df['Wind_LF'] = 0

    if 'EMBEDDED_SOLAR_GENERATION' in df.columns:
        df['Solar_LF'] = df['EMBEDDED_SOLAR_GENERATION'] / df['EMBEDDED_SOLAR_CAPACITY']
        df['Solar_LF'] = df['Solar_LF'].fillna(0).clip(0, 1)
    else:
        df['Solar_LF'] = 0

    df['Demand_MW'] = df['ND']

    # Keep only necessary columns and optimize types (float32 saves RAM)
    clean_df = df[['Demand_MW', 'Wind_LF', 'Solar_LF']].astype(np.float32)

    # 3. Save as Parquet for next time (Auto-Optimization)
    try:
        clean_df.to_parquet(PARQUET_PATH)
        print(f"✅ Optimization complete: Saved {PARQUET_PATH}")
    except Exception as e:
        print(f"⚠️ Could not save optimization file (likely read-only filesystem): {e}")

    return clean_df

@st.cache_data
def get_fes_peak_demand(filepath="data/raw/fes2025_ed1_v006.csv", scenario="Holistic Transition", year="2030"):
    """
    Retrieves the projected Peak Demand (MW) for a specific year and scenario.
    """
    if not os.path.exists(filepath):
        st.error(f"Error: FES Data not found at {filepath}")
        return 50000 # Safe fallback

    try:
        df = pd.read_csv(filepath)
        mask = (df['Pathway'] == scenario) & \
               (df['Data item'].str.contains('Peak Customer Demand: Total Consumption', case=False)) & \
               (df['Peak/ Annual/ Minimum'] == 'Peak')
               
        row = df[mask]
        
        if row.empty:
            st.warning(f"No data found for {scenario} Peak Demand in {year}. Using default.")
            return 50000 
        
        val = row[str(year)].values[0]
        unit = row['Unit'].values[0]
        
        if unit == 'GW':
            return val * 1000
        elif unit == 'MW':
            return val
        else:
            return val * 1000
    except Exception as e:
        st.error(f"Error reading FES data: {e}")
        return 50000

def create_2030_profile(weather_df, cp30_targets, peak_demand_2030_mw):
    """
    Scales the 2025 weather template to 2030 dimensions using CP30 Targets.
    """
    # SAFETY CHECK: Handles None/Empty inputs to prevent crashes
    if weather_df is None or weather_df.empty:
        return pd.DataFrame()

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