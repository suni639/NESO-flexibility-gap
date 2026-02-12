import pandas as pd
import numpy as np
import os

def optimize():
    # Define paths
    raw_path = "data/raw/demanddata_2025.csv"
    parquet_path = "data/raw/weather_2025.parquet"

    print(f"Reading {raw_path}...")
    try:
        df = pd.read_csv(raw_path)
    except FileNotFoundError:
        print("❌ Error: CSV file not found. Please run this from the project root.")
        return

    print("Processing data (Parsing dates, calculating Load Factors)...")
    # 1. Date Parsing
    df['Datetime'] = pd.to_datetime(df['SETTLEMENT_DATE'], format='%Y-%m-%d') + \
                     pd.to_timedelta((df['SETTLEMENT_PERIOD'] - 1) * 30, unit='m')
    df = df.set_index('Datetime')

    # 2. Load Factors
    # Wind
    df['Wind_LF'] = df['EMBEDDED_WIND_GENERATION'] / df['EMBEDDED_WIND_CAPACITY']
    df['Wind_LF'] = df['Wind_LF'].fillna(0).clip(0, 1)

    # Solar
    df['Solar_LF'] = df['EMBEDDED_SOLAR_GENERATION'] / df['EMBEDDED_SOLAR_CAPACITY']
    df['Solar_LF'] = df['Solar_LF'].fillna(0).clip(0, 1)

    # 3. Demand
    df['Demand_MW'] = df['ND']

    # 4. Float32 Optimization (Saves 50% RAM)
    print("Optimizing memory usage...")
    clean_df = df[['Demand_MW', 'Wind_LF', 'Solar_LF']].astype(np.float32)

    # 5. Save
    print(f"Saving to {parquet_path}...")
    clean_df.to_parquet(parquet_path)
    print("✅ Success! Parquet file created.")
    print("🚀 NEXT STEP: Run 'git add data/raw/weather_2025.parquet' and commit!")

if __name__ == "__main__":
    optimize()