import pandas as pd
import numpy as np
import streamlit as st
import os

# Define paths
PARQUET_PATH = "data/raw/weather_2025.parquet"
CSV_PATH = "data/raw/demanddata_2025.csv"

@st.cache_data
def load_weather_template():
    """
    PRIORITY: Loads 'weather_2025.parquet' (Fast).
    FALLBACK: Loads 'demanddata_2025.csv' (Slow).
    """
    # 1. FAST PATH: Check for Parquet
    if os.path.exists(PARQUET_PATH):
        try:
            return pd.read_parquet(PARQUET_PATH)
        except Exception:
            pass # If corrupt, ignore and use fallback

    # 2. SLOW PATH: CSV Fallback
    # (Only runs if you forgot to commit the parquet file)
    if not os.path.exists(CSV_PATH):
        st.error(f"CRITICAL ERROR: Data missing. Please add {CSV_PATH}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(CSV_PATH)
        
        # Process Data
        df['Datetime'] = pd.to_datetime(df['SETTLEMENT_DATE'], format='%Y-%m-%d') + \
                         pd.to_timedelta((df['SETTLEMENT_PERIOD'] - 1) * 30, unit='m')
        df = df.set_index('Datetime')
        
        # Calculate Factors
        df['Wind_LF'] = (df['EMBEDDED_WIND_GENERATION'] / df['EMBEDDED_WIND_CAPACITY']).fillna(0).clip(0,1)
        df['Solar_LF'] = (df['EMBEDDED_SOLAR_GENERATION'] / df['EMBEDDED_SOLAR_CAPACITY']).fillna(0).clip(0,1)
        df['Demand_MW'] = df['ND']
        
        return df[['Demand_MW', 'Wind_LF', 'Solar_LF']].astype(np.float32)
        
    except Exception as e:
        st.error(f"Error loading CSV fallback: {e}")
        return pd.DataFrame()

# ... (Rest of the file: get_fes_peak_demand, create_2030_profile remain unchanged)