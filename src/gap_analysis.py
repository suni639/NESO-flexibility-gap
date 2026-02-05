# The Dunkelflaute logic & math to calculate the gap and the flexibility requirement
import pandas as pd
import numpy as np

def identify_dunkelflaute_window(df, window_days=5):
    """
    Identifies the most stressful period (Dunkelflaute) in the year.
    Criteria: The rolling window with the highest cumulative Net Demand (Energy Deficit).
    
    Returns: 
        - dunkelflaute_df: The DataFrame slice for the worst window
        - worst_period_idx: The timestamp where the worst window ends
    """
    # 48 periods per day (30 min resolution)
    window_periods = window_days * 48
    
    # Calculate rolling sum of POSITIVE Net Demand (Deficit only)
    # We ignore negative periods (surplus) because you can't "eat" surplus wind 
    # to fix a deficit unless you have storage (which we simulate later).
    deficit_only = df['Net_Demand_MW'].clip(lower=0)
    rolling_deficit = deficit_only.rolling(window=window_periods).sum()
    
    # Find the end point of the worst window
    if rolling_deficit.max() == 0:
        # Fallback if no deficit exists (unlikely in 2030)
        return df.head(window_periods), df.index[window_periods]

    worst_period_idx = rolling_deficit.idxmax()
    end_loc = df.index.get_loc(worst_period_idx)
    start_loc = max(0, end_loc - window_periods)
    
    # Extract the window
    dunkelflaute_df = df.iloc[start_loc:end_loc].copy()
    
    return dunkelflaute_df, worst_period_idx

def run_simple_dispatch(df, battery_capacity_mw=25000, battery_duration_hours=4, efficiency=0.9):
    """
    Simulates a 'Greedy' Dispatch Stack:
    1. Excess Wind/Solar -> Charges Battery
    2. Net Demand Gap -> Discharges Battery
    3. Remaining Gap -> Loss of Load (or Gas requirement)
    
    Returns: 
        - The original DataFrame with new columns:
          'Battery_Storage_MWh', 'Battery_Output_MW', 'Unmet_Gap_MW'
    """
    simulation = df.copy()
    
    # Battery Tech Specs
    max_energy_mwh = battery_capacity_mw * battery_duration_hours
    current_storage_mwh = max_energy_mwh * 0.5  # Start year 50% full
    
    storage_profile = []
    battery_output = []
    
    # Loop through every half-hour (row) in the year
    for net_demand in simulation['Net_Demand_MW']:
        # Period length is 0.5 hours
        
        if net_demand < 0:
            # --- EXCESS: Charge Battery ---
            # We have surplus power (e.g. -10,000 MW)
            
            # Constraint 1: Inverter Limit (The Pipe)
            charge_power = min(abs(net_demand), battery_capacity_mw)
            
            # Constraint 2: Efficiency (The Tax)
            energy_to_store = charge_power * 0.5 * efficiency
            
            # Constraint 3: Capacity Limit (The Bucket)
            space_available = max_energy_mwh - current_storage_mwh
            actual_stored = min(energy_to_store, space_available)
            
            current_storage_mwh += actual_stored
            
            # Negative 'Output' means we are consuming power (Load)
            # We record the GRID view: -100 MW means grid gave 100 MW to battery
            battery_flow = -actual_stored / 0.5 / efficiency 
            
        else:
            # --- DEFICIT: Discharge Battery ---
            # We need power (e.g. +50,000 MW)
            
            # Constraint 1: Inverter Limit
            discharge_power = min(net_demand, battery_capacity_mw)
            
            # Constraint 2: Energy Available (The Bucket)
            energy_needed = discharge_power * 0.5
            actual_energy_out = min(energy_needed, current_storage_mwh)
            
            current_storage_mwh -= actual_energy_out
            
            # Positive 'Output' means we are injecting power
            battery_flow = actual_energy_out / 0.5
            
        storage_profile.append(current_storage_mwh)
        battery_output.append(battery_flow)
        
    simulation['Battery_Storage_MWh'] = storage_profile
    simulation['Battery_Output_MW'] = battery_output
    
    # Calculate what is left for Gas/Hydrogen to cover
    # Final Gap = Need - Battery
    simulation['Unmet_Gap_MW'] = simulation['Net_Demand_MW'] - simulation['Battery_Output_MW']
    
    return simulation