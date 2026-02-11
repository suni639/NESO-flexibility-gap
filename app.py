import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.cp30_targets import CP30_TARGETS
from src.data_loader import load_weather_template, get_fes_peak_demand, create_2030_profile
from src.gap_analysis import identify_dunkelflaute_window, run_simple_dispatch

# --- Page Config ---
st.set_page_config(page_title="CP30: The Resilience Test", layout="wide", page_icon="⚡")

# --- CSS for "Strategy Grade" Cards ---
st.markdown("""
<style>
    .metric-card {
        background-color: #F8F9FA;
        border: 1px solid #E9ECEF;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 15px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.05);
    }
    .metric-label {
        font-size: 13px;
        font-weight: 700;
        color: #6C757D;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 800;
        color: #212529;
    }
    .metric-sub {
        font-size: 12px;
        color: #ADB5BD;
        margin-top: 5px;
    }
    .quote-box {
        border-left: 4px solid #FF4B4B;
        background-color: #FFF5F5;
        padding: 15px;
        border-radius: 5px;
        font-style: italic;
        color: #444;
        margin-bottom: 15px;
    }
    /* Compact Sidebar */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
        padding-bottom: 1rem;
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

# --- 1. Sidebar: Scenario Controls (Compacted) ---
st.sidebar.header("🛠️ Controls")

# Scenario Sliders
battery_cap = st.sidebar.slider("🔋 Battery Capacity (GW)", 0, 100, 30, 5)
battery_dur = st.sidebar.slider("⏳ Battery Duration (Hours)", 1, 12, 4, 1)
offshore_wind_target = st.sidebar.select_slider(
    "💨 Offshore Wind Target", 
    options=["Low (43GW)", "High (50GW)", "Extreme (60GW)"], 
    value="High (50GW)"
)

# Parse sliders
wind_gw = int(offshore_wind_target.split("(")[1].replace("GW)", ""))
CP30_TARGETS['Offshore Wind']['High'] = wind_gw 

st.sidebar.subheader("🧪 Mitigations")
enable_hydrogen = st.sidebar.checkbox("Hydrogen / CCS (5 GW)", value=False)
enable_dsr = st.sidebar.checkbox("Aggressive DSR (3 GW)", value=False)

# --- NEW: Chart Legend in Sidebar ---
st.sidebar.divider()
st.sidebar.markdown("### 📉 Chart Legend")
st.sidebar.info("""
**Visualising the Dispatch Stack:**

* 🟢 **Bottom (Green/Blue):** Must-run Renewables & Nuclear.
* 🟠 **Middle (Orange):** Batteries discharging to shave peaks (note how they empty quickly).
* 🔴 **Top (Red):** The **Unmet Gap**. This is the risk zone where strategic reserves are required.
""")

# --- 2. Main Execution Engine ---
@st.cache_data
def load_and_run_simulation(bat_cap, bat_dur, wind_gw_val):
    # Load Data (Cached so it's fast)
    weather = load_weather_template()
    peak_2030 = get_fes_peak_demand()
    
    # Safety Copy
    targets = CP30_TARGETS.copy()
    targets['Offshore Wind'] = CP30_TARGETS['Offshore Wind'].copy() 
    targets['Offshore Wind']['High'] = wind_gw_val
    
    scenario_df = create_2030_profile(weather, targets, peak_2030)
    
    # Run Battery Dispatch
    dispatched_df = run_simple_dispatch(
        scenario_df, 
        battery_capacity_mw=bat_cap * 1000, 
        battery_duration_hours=bat_dur
    )
    
    return dispatched_df

# Run the logic
df = load_and_run_simulation(battery_cap, battery_dur, wind_gw)
dunkelflaute, worst_date_timestamp = identify_dunkelflaute_window(df, window_days=7)

# Apply Strategic Mitigations
mitigation_mw = 0
if enable_hydrogen: mitigation_mw += 5000
if enable_dsr: mitigation_mw += 3000

# Adjust the Gap
dunkelflaute['Adjusted_Gap_MW'] = (dunkelflaute['Unmet_Gap_MW'] - mitigation_mw).clip(lower=0)
peak_gap_fixed = dunkelflaute['Adjusted_Gap_MW'].max() / 1000

# --- 3. Dashboard Header ---
st.title("⚡ Clean Power 2030: The Resilience Test")
st.markdown("### Stress-testing the UK Grid against 'Dunkelflaute' severe weather events")
st.divider()

# --- 4. KPI Metrics Row (Top) ---
col1, col2, col3, col4 = st.columns(4)

curtailment = df[df['Net_Demand_MW'] < 0]['Net_Demand_MW'].sum() / 1000000 * -1 
start_date_str = dunkelflaute.index.min().strftime('%d %b')
end_date_str = dunkelflaute.index.max().strftime('%d %b')

with col1:
    strategy_card("Event Window", f"{start_date_str} - {end_date_str}", "Worst 7 Days (2025 Data)")

with col2:
    strategy_card("Clean Surplus", f"{curtailment:,.1f} TWh", "Wasted Energy (Pre-Event)")

with col3:
    strategy_card("Battery Exhaustion", "Day 2", "Of 7-Day Event")

with col4:
    val_color = "#FF4B4B" if peak_gap_fixed > 5 else "#FFA500" if peak_gap_fixed > 0 else "#28A745"
    styled_value = f'<span style="color:{val_color}">{peak_gap_fixed:,.1f} GW</span>'
    strategy_card("Real-World Gap", styled_value, "Unmet Peak Demand")

# --- 5. The "Merit Order" Chart (Stacked Area) ---
st.subheader("🔎 The Dispatch Stack")

fig = go.Figure()

# 1. Nuclear (Baseload - The Floor)
fig.add_trace(go.Scatter(
    x=dunkelflaute.index, 
    y=dunkelflaute['Nuclear_Gen_2030_MW']/1000,
    mode='lines', 
    name='Nuclear (Baseload)',
    stackgroup='one', 
    line=dict(width=0, color='#2ca02c'), # Green
    fillcolor='rgba(44, 160, 44, 0.6)'
))

# 2. Wind & Solar (Variable - The Bulk)
fig.add_trace(go.Scatter(
    x=dunkelflaute.index, 
    y=(dunkelflaute['Wind_Gen_2030_MW'] + dunkelflaute['Solar_Gen_2030_MW'])/1000,
    mode='lines', 
    name='Wind & Solar',
    stackgroup='one',
    line=dict(width=0, color='#1f77b4'), # Blue
    fillcolor='rgba(31, 119, 180, 0.6)'
))

# 3. Battery Discharge (The Peaker)
fig.add_trace(go.Scatter(
    x=dunkelflaute.index, 
    y=dunkelflaute['Battery_Output_MW'].clip(lower=0)/1000,
    mode='lines', 
    name='Battery Discharge',
    stackgroup='one',
    line=dict(width=0, color='#ff7f0e'), # Orange
    fillcolor='rgba(255, 127, 14, 0.8)'
))

# 4. Mitigation (Hydrogen/DSR) if selected
if mitigation_mw > 0:
    mitigation_series = pd.Series(mitigation_mw/1000, index=dunkelflaute.index)
    fig.add_trace(go.Scatter(
        x=dunkelflaute.index,
        y=mitigation_series,
        mode='lines',
        name='Strategic Reserve (H2/DSR)',
        stackgroup='one',
        line=dict(width=0, color='#9467bd'), # Purple
        fillcolor='rgba(148, 103, 189, 0.6)'
    ))

# 5. The Gap (The Deficit)
gap_to_fill = (dunkelflaute['Adjusted_Gap_MW'] / 1000).clip(lower=0)

fig.add_trace(go.Scatter(
    x=dunkelflaute.index, 
    y=gap_to_fill,
    mode='lines', 
    name='UNMET GAP (Risk)',
    stackgroup='one',
    line=dict(width=0, color='#d62728'), # Red
    fillcolor='rgba(214, 39, 40, 0.5)' # Semi-transparent Red
))

# 6. The Demand Line (The Ceiling)
fig.add_trace(go.Scatter(
    x=dunkelflaute.index, 
    y=dunkelflaute['Demand_2030_MW']/1000,
    mode='lines', 
    name='System Demand',
    line=dict(color='black', width=2, dash='dot')
))

fig.update_layout(
    yaxis_title="Power Generation (GW)",
    height=550,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=0, r=0, t=30, b=0)
)
st.plotly_chart(fig, use_container_width=True)

# Gap Analysis Message (Kept under chart for context)
if peak_gap_fixed > 5:
    st.error(f"⚠️ **Analysis:** Even with mitigations, a **{peak_gap_fixed:.1f} GW gap** remains. This confirms the critical need for Long Duration Energy Storage (LDES).")

# --- 6. TABS (Bottom) ---
st.divider()
st.markdown("### 📚 Context & Methodology")
tab_context, tab_method, tab_market, tab_refs = st.tabs(["❄️ The Weather Challenge", "🧪 Methodology", "🏗️ Strategic Levers", "📚 References"])

with tab_context:
    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        st.markdown("""
        **The Scenario:** It's a cold, dark January. A high-pressure system sits over the North Sea. Wind output drops to <5% for 7 days. It's freezing, and heat pump demand spikes.
        
        **The Resilience Gap:**
        The Government's *Clean Power 2030* mission relies heavily on wind. This simulation models a **"Dunkelflaute"** event (German for "dark doldrums"), a prolonged period of low wind and minimal sunshine, severely limiting UK renewable energy production.
                    
        During a Dunkelflaute, wind/solar output can drop to near zero, as seen in recent events across Europe where wind provided only 3-4% of demand during peak times.
        
        **Why Batteries Aren't Enough:**
        Lithium-ion batteries are excellent at covering short durations (1-4 hours), but they cannot support the grid for the prolonged periods (5-7 days) seen in Dunkelflaute events. Once they empty, the grid requires **Firm Power** (Nuclear, Hydrogen, or gas) to keep the lights on.
        """)
        
        st.info("""
        **Operational Reality:**
        When the gap opens (i.e. supply cannot meet demand), NESO (National Energy System Operator) issues a **Loss of Load Probability (LoLP)** warning. In today's market, this gap is filled by expensive, high-carbon gas turbines (OCGTs). By 2030, the national objective is to fill it with clean alternatives; however, the question is whether the planned capacity will be sufficient to prevent blackouts during extreme weather events.
        """)

    with col_c2:
        st.markdown("""
        <div class="quote-box">
        "Wind and solar generated electricity cannot be relied upon to meet demand... There is a need for large-scale long-duration storage to ensure security of supply."
        <br>— <b>The Royal Society</b>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Reference: Royal Society Large-Scale Energy Storage Report (2023)")

with tab_method:
    st.markdown("### 🧪 Methodology: The 'Digital Twin'")
    st.markdown("""
    The 2030 energy demand forecast was stress tested using a "Digital Twin" approach:
    
    1.  **Weather Pattern:** 2025 demand and settlement data (Elexon) was used to identify the worst 7-day "cold and calm" window.
    2.  **Future Scaling:** **NESO FES 2030** and **CP30 Action Plan** targets were used to scale the wind and solar capacity.
    3.  **Dispatch Engine:** A custom Python engine (see codebase link in References) calculated the net deficit half-hour by half-hour, prioritising:
        * `Renewables (Zero Marginal Cost)`
        * `Nuclear (Baseload)`
        * `Battery Storage (Limited Duration)`
        * `Strategic Reserve (The Gap)`
    """)
    
    st.latex(r"\text{Flexibility Gap} = \text{Peak Demand} - (\text{Firm Gen} + \text{Renewables} + \text{Storage})")

with tab_market:
    st.markdown("### 🏗️ Closing the Loop: Market Reform")
    st.markdown("""
    Building hardware is only half the solution. To secure the grid, **Market Reform** is needed to value flexibility correctly.
    
    #### 1. Locational Marginal Pricing (LMP)
    * **Problem:** Currently, the UK has one national price. There is limited incentive to locate batteries where the grid is weakest.
    * **Solution:** Zonal pricing would create high-price signals in the South and London, encouraging storage assets to be built where demand is highest.
    
    #### 2. REMA (Review of Electricity Market Arrangements)
    * **Problem:** The current market pays for "Generation."
    * **Solution:** REMA aims to create a market for "Availability"—paying assets (like Hydrogen turbines) just to sit there and wait for a Dunkelflaute.
    """)

with tab_refs:
    st.markdown("### 📚 References & Resources")
    st.markdown("Sources used to build this stress-test model and define the strategic context:")
    
    col_ref1, col_ref2 = st.columns(2)
    
    with col_ref1:
        st.markdown("#### Industry Reports")
        st.markdown("""
        * **The Royal Society:** [Large-Scale Energy Storage](https://royalsociety.org/news-resources/projects/low-carbon-energy-programme/large-scale-electricity-storage/)
        * **NESO (National Energy System Operator):** [Future Energy Scenarios (FES)](https://www.neso.energy/publications/future-energy-scenarios-fes)
        * **Wood Mackenzie:** [Critical Risks of "Dunkelflaute"](https://www.woodmac.com/press-releases/wood-mackenzie-study-reveals-critical-risks-of-europes-dunkelflaute-renewable-energy-droughts/)
        * **BEIS (UK Department for Business, Energy & Industrial Strategy):** [Clean Power 2030 Action Plan](https://www.gov.uk/government/publications/clean-power-2030-action-plan)
        """)
        
    with col_ref2:
        st.markdown("#### Project Codebase")
        st.markdown("""
        The full simulation engine, dispatch logic, and data loaders are open-source.
        
        * 💻 **GitHub Repository:** [suni639/NESO-flexibility-gap](https://github.com/suni639/NESO-flexibility-gap)
        """)