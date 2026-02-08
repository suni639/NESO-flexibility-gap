import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.cp30_targets import CP30_TARGETS
from src.data_loader import load_weather_template, get_fes_peak_demand, create_2030_profile
from src.gap_analysis import identify_dunkelflaute_window, run_simple_dispatch

# --- Page Config ---
st.set_page_config(page_title="NESO Flexibility Gap 2030", layout="wide", page_icon="⚡")

# --- CSS for "Strategy Grade" Cards ---
st.markdown("""
<style>
    .metric-card {
        background-color: #F0F2F6;
        border: 1px solid #E0E0E0;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .metric-label {
        font-size: 14px;
        font-weight: 600;
        color: #555555;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 26px; /* Fixed font size for ALL cards (Text & Numbers) */
        font-weight: 700;
        color: #000000;
    }
    .metric-sub {
        font-size: 12px;
        color: #888888;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- Helper Function to Draw Custom Cards ---
def strategy_card(label, value, sub_text=""):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub_text}</div>
    </div>
    """, unsafe_allow_html=True)

# --- 1. Sidebar: Scenario Controls ---
st.sidebar.title("🛠️ Strategy Controls")
st.sidebar.markdown("Adjust 2030 assumptions to close the gap.")

# Scenario Sliders
battery_cap = st.sidebar.slider("Battery Capacity (GW)", min_value=0, max_value=100, value=25, step=5)
battery_dur = st.sidebar.slider("Battery Duration (Hours)", min_value=1, max_value=12, value=4, step=1)
offshore_wind_target = st.sidebar.select_slider(
    "Offshore Wind Target", 
    options=["Low (43GW)", "High (50GW)", "Extreme (60GW)"], 
    value="High (50GW)"
)

# Parse the slider text back to numbers
wind_gw = int(offshore_wind_target.split("(")[1].replace("GW)", ""))
# Hack: Update the target dynamically for the simulation
CP30_TARGETS['Offshore Wind']['High'] = wind_gw 

st.sidebar.divider()
st.sidebar.info(f"**Current Scenario:**\n\n🔋 {battery_cap}GW / {battery_cap*battery_dur}GWh Storage\n💨 {wind_gw}GW Offshore Wind")

# --- 2. Main Execution Engine ---
@st.cache_data
def load_and_run_simulation(bat_cap, bat_dur, wind_gw_val):
    # Load Data (Cached so it's fast)
    weather = load_weather_template()
    peak_2030 = get_fes_peak_demand()
    
    # Create Base Profile
    targets = CP30_TARGETS.copy()
    targets['Offshore Wind']['High'] = wind_gw_val
    
    scenario_df = create_2030_profile(weather, targets, peak_2030)
    
    # Run Battery Dispatch
    dispatched_df = run_simple_dispatch(
        scenario_df, 
        battery_capacity_mw=bat_cap*1000, 
        battery_duration_hours=bat_dur
    )
    
    return dispatched_df

# Run the logic
df = load_and_run_simulation(battery_cap, battery_dur, wind_gw)

# Find the worst window (returns dataframe slice and end timestamp)
dunkelflaute, worst_date_timestamp = identify_dunkelflaute_window(df, window_days=7)

# --- 3. Dashboard Header & Context ---
st.title("⚡ Clean Power 2030: The Green Energy Gap")

# --- Expanders for Context ---
with st.expander("🌍 Strategic Context: Clean Power 2030 & Key Findings", expanded=False):
    st.markdown("""
    ### 🌍 The Context: Clean Power 2030 vs. The Weather
    **The Mission:** The Government's **Clean Power 2030 (CP30)** roadmap aims to decarbonise the UK grid. While this works for "average" weather, it creates a critical vulnerability during extreme events.

    **The Threat:** A **"Dunkelflaute"** (Dark Wind Lull) is a recurring weather phenomenon where high pressure freezes wind speeds (<10% capacity) and blocks sunlight for **3–10 days**.
    * **The Risk:** These events coincide with cold snaps (peak heating demand) and affect neighbouring countries simultaneously, making imports unreliable.
    * **The Question:** As fossil fuels retire, what keeps the lights on when the wind stops for a week?

    ---

    ### 🎯 The Goal & Key Findings
    **The Goal:** To quantify the **"Clean Power Gap"**—the specific volume of firm, dispatchable capacity (GW) and energy (TWh) required to secure the UK grid during a severe weather stress event (*Dunkelflaute*), assuming full delivery of CP30 targets.

    **The Findings:**
    * **The "Gap" Defined:** During a severe winter calm (modelled on 2025 weather patterns scaled to 2030), the grid faces a capacity shortfall of **~51 GW**.
    * **The Failure Mode:** Short-duration (Li-ion) batteries exhausted their energy reserves within the **first 24 hours** of the 120-hour stress window.
    * **Strategic Implication:** Batteries solve *intraday* volatility but provide **zero security** for *inter-day* weather risks. The 51 GW gap effectively defines the requirement for **Long Duration Energy Storage (LDES)** and Low-Carbon Gas (CCS/Hydrogen).
    """)

with st.expander("🛡️ Mitigations & The 'Dispatch Stack'", expanded=False):
    st.markdown("""
    If batteries fail the 5-day test (as shown by the model), the project highlights the hierarchy of mitigations required to fill the 51 GW gap:

    | Tier | Mitigation Strategy | Potential Impact | Risk / Limitation |
    | :--- | :--- | :--- | :--- |
    | **1** | **Interconnectors** | ~10-15 GW | **High Risk.** We can import power, but only if our neighbours aren't suffering the same weather event. |
    | **2** | **Nuclear** | ~4-6 GW | **Inflexible.** Provides a stable floor (Baseload) but cannot easily "ramp up" to fill a sudden 50GW gap. |
    | **3** | **Demand Side Response (DSR)** | ~5-10 GW | **Consumer Action.** Paying heavy industry to shut down and consumers to lower usage. |
    | **4** | **The Strategic Reserve** | **~30 GW** | **The Gap Filler.** The remaining shortfall must be met by Gas with CCS (Carbon Capture), Hydrogen Turbines, or keeping unabated gas plants on standby as a "last resort" insurance policy. |
    """)

with st.expander("⚙️ Data & Methodology", expanded=False):
    st.markdown("""
    A **"Digital Twin"** approach was utilised to stress-test the 2030 grid:

    * **Weather Profile:** Used **2025 Historic Demand & Settlement Data (Elexon)** to capture the exact physics of a "Cold Dunkelflaute" (load factors <3%).
    * **Future Scaling:** Applied **NESO FES 2030** and **CP30 Action Plan** targets to scale the wind/solar amplitude (e.g., scaling wind output to hit 50 GW capacity).
    * **Simulation Engine:** A custom Python dispatch engine calculated the net deficit half-hour by half-hour, prioritising `Renewables` > `Batteries` > `Fossil Backup`.
    """)

# --- 4. KPI Metrics Row ---
col1, col2, col3, col4 = st.columns(4)

# Calculate Metrics
peak_gap_raw = df['Net_Demand_MW'].max() / 1000
peak_gap_fixed = df['Unmet_Gap_MW'].max() / 1000
curtailment = df[df['Net_Demand_MW'] < 0]['Net_Demand_MW'].sum() / 1000000 * -1 # TWh

# Calculate Date Range using the DataFrame Index (Fixes the single date issue)
start_date_str = dunkelflaute.index.min().strftime('%b %d')
end_date_str = dunkelflaute.index.max().strftime('%b %d')
date_range_str = f"{start_date_str} - {end_date_str}"

with col1:
    strategy_card("Peak Unmet Demand", f"{peak_gap_raw:,.1f} GW", "Raw Deficit")

with col2:
    # Color logic for the value
    val_color = "red" if peak_gap_fixed > 5 else "orange" if peak_gap_fixed > 0 else "green"
    # We inject the color style directly into the value string for the helper function
    styled_value = f'<span style="color:{val_color}">{peak_gap_fixed:,.1f} GW</span>'
    strategy_card("Gap After Batteries", styled_value, "Remaining Deficit")

with col3:
    strategy_card("Surplus Energy", f"{curtailment:,.1f} TWh", "Wasted / Curtailed")

with col4:
    strategy_card("Critical Window", date_range_str, "Worst 7-Day Event")

# --- 5. The "Crime Scene" Chart (Dunkelflaute) ---
st.subheader("🔎 The 'Dunkelflaute' Event (Worst 7 Days)")

fig = go.Figure()

# Demand Line
fig.add_trace(go.Scatter(
    x=dunkelflaute.index, y=dunkelflaute['Demand_2030_MW']/1000,
    mode='lines', name='Demand (GW)',
    line=dict(color='black', width=3)
))

# Clean Gen (Wind+Solar+Nuclear)
total_clean = (dunkelflaute['Wind_Gen_2030_MW'] + dunkelflaute['Solar_Gen_2030_MW'] + dunkelflaute['Nuclear_Gen_2030_MW']) / 1000
fig.add_trace(go.Scatter(
    x=dunkelflaute.index, y=total_clean,
    mode='lines', name='Clean Gen (GW)',
    line=dict(color='#2ca02c', width=1),
    fill='tozeroy'
))

# Battery Output (Stacked on top of Clean Gen)
battery_contribution = dunkelflaute['Battery_Output_MW'].clip(lower=0) / 1000
fig.add_trace(go.Scatter(
    x=dunkelflaute.index, y=total_clean + battery_contribution,
    mode='lines', name='With Batteries',
    line=dict(color='#1f77b4', width=0),
    fill='tonexty' # Fill between Clean Gen and This Line
))

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Power (GW)",
    height=500,
    hovermode="x unified",
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    margin=dict(l=0, r=0, t=30, b=0)
)
st.plotly_chart(fig, use_container_width=True)

# --- 6. Deep Dive: Battery State of Charge ---
with st.expander("🔋 View Battery State of Charge Analysis"):
    st.write("This chart shows how the batteries drained during the stress event.")
    
    fig_soc = go.Figure()
    fig_soc.add_trace(go.Scatter(
        x=dunkelflaute.index, y=dunkelflaute['Battery_Storage_MWh']/1000,
        mode='lines', name='Storage Level (GWh)',
        line=dict(color='orange', width=2)
    ))
    
    fig_soc.update_layout(
        title="Battery State of Charge (GWh)",
        yaxis_title="Energy Stored (GWh)",
        height=300,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    st.plotly_chart(fig_soc, use_container_width=True)

# --- 7. Strategic Insight Box ---
st.divider()
st.markdown("### 💡 Strategic Insight")

if peak_gap_fixed > 5:
    st.error(f"**CRITICAL RISK:** Even with {battery_cap}GW of batteries, the grid is short by {peak_gap_fixed:.1f} GW. This confirms that short-duration lithium-ion batteries cannot solve a multi-day Dunkelflaute. **Strategic Implication:** We need Hydrogen or Gas CCS.")
elif peak_gap_fixed > 0:
    st.warning(f"**MODERATE RISK:** The gap is reduced to {peak_gap_fixed:.1f} GW. We are close, but need either more duration or DSR (Demand Side Response).")
else:
    st.success("**SECURE:** This configuration successfully bridges the Dunkelflaute gap. The grid remains stable.")