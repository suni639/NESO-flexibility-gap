# convert_data.py
import pandas as pd
import numpy as np

def convert_weather_data():
    print("Converting Weather Data...")
    # 1. Read Raw CSV
    df = pd.read_csv("data/raw/demanddata_2025.csv")

    # 2. Do the Heavy Math ONCE
    # Date Parsing
    df['Datetime'] = pd.to_datetime(df['SETTLEMENT_DATE'], format='%Y-%m-%d') + \
                     pd.to_timedelta((df['SETTLEMENT_PERIOD'] - 1) * 30, unit='m')
    df = df.set_index('Datetime')

    # Load Factors
    df['Wind_LF'] = df['EMBEDDED_WIND_GENERATION'] / df['EMBEDDED_WIND_CAPACITY']
    df['Wind_LF'] = df['Wind_LF'].fillna(0).clip(0, 1)

    df['Solar_LF'] = df['EMBEDDED_SOLAR_GENERATION'] / df['EMBEDDED_SOLAR_CAPACITY']
    df['Solar_LF'] = df['Solar_LF'].fillna(0).clip(0, 1)

    df['Demand_MW'] = df['ND']

    # 3. Optimize Types (float64 -> float32 saves 50% RAM)
    cols = ['Demand_MW', 'Wind_LF', 'Solar_LF']
    final_df = df[cols].astype(np.float32)

    # 4. Save as Parquet
    final_df.to_parquet("data/raw/weather_2025.parquet")
    print("✅ Created data/raw/weather_2025.parquet")

if __name__ == "__main__":
    convert_weather_data()