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

# --- 1. Sidebar: Scenario Controls ---
st.sidebar.header("🛠️ Controls")

battery_cap = st.sidebar.slider("🔋 Battery Capacity (GW)", 0, 100, 30, 5)
battery_dur = st.sidebar.slider("⏳ Battery Duration (Hours)", 1, 12, 4, 1)
offshore_wind_target = st.sidebar.select_slider(
    "💨 Offshore Wind Target", 
    options=["Low (43GW)", "High (50GW)", "Extreme (60GW)"], 
    value="High (50GW)"
)

wind_gw = int(offshore_wind_target.split("(")[1].replace("GW)", ""))
CP30_TARGETS['Offshore Wind']['High'] = wind_gw 

st.sidebar.subheader("🧪 Mitigation Hierarchy")
st.sidebar.markdown("Enable tiers from the Strategic Levers tab:")

# CORRELATED CONTROLS: These now match the GW values in your Hierarchy Table
enable_interconnectors = st.sidebar.checkbox("Tier 1: Interconnectors (15 GW)", value=False)
enable_dsr = st.sidebar.checkbox("Tier 3: Demand Side Response (10 GW)", value=False)
enable_reserve = st.sidebar.checkbox("Tier 4: Strategic Reserve (30 GW)", value=False)

st.sidebar.divider()
st.sidebar.markdown("### 📉 Chart Legend")
st.sidebar.info("""
* 🟢 **Bottom:** Renewables & Nuclear.
* 🟠 **Middle:** Battery Discharge.
* 🟣 **Tiered:** Strategic Mitigations.
* 🔴 **Top:** Remaining Unmet Gap.
""")

# --- 2. Main Execution Engine ---
@st.cache_data
def load_and_run_simulation(bat_cap, bat_dur, wind_gw_val):
    weather = load_weather_template()
    peak_2030 = get_fes_peak_demand()
    targets = CP30_TARGETS.copy()
    targets['Offshore Wind'] = CP30_TARGETS['Offshore Wind'].copy() 
    targets['Offshore Wind']['High'] = wind_gw_val
    scenario_df = create_2030_profile(weather, targets, peak_2030)
    dispatched_df = run_simple_dispatch(scenario_df, bat_cap * 1000, bat_dur)
    return dispatched_df

df = load_and_run_simulation(battery_cap, battery_dur, wind_gw)
dunkelflaute, worst_date_timestamp = identify_dunkelflaute_window(df, window_days=7)

# CORRELATED MATH: Matching the Table precisely
mitigation_mw = 0
if enable_interconnectors: mitigation_mw += 15000
if enable_dsr: mitigation_mw += 10000
if enable_reserve: mitigation_mw += 30000

dunkelflaute['Adjusted_Gap_MW'] = (dunkelflaute['Unmet_Gap_MW'] - mitigation_mw).clip(lower=0)
peak_gap_fixed = dunkelflaute['Adjusted_Gap_MW'].max() / 1000

# --- 3. Dashboard Header ---
st.title("⚡ Clean Power 2030: The Resilience Test")
st.markdown("### Stress-testing the UK Grid against 'Dunkelflaute' severe weather events")
st.divider()

# --- 4. TABS ---
tab_context, tab_method, tab_market, tab_refs = st.tabs(["❄️ The Weather Challenge", "🧪 Methodology", "🏗️ Strategic Levers", "📚 References"])

with tab_context:
    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        st.markdown("""
        **The Scenario:** It is a cold, dark January. A high-pressure system sits over the North Sea. Wind output drops to <5% for 7 days. It is freezing, and heat pump demand spikes.
        
        **The Resilience Gap:**
        The Government's *Clean Power 2030* mission relies heavily on wind. This simulation models a **"Dunkelflaute"** event (German for "dark doldrums"), a prolonged period of low wind and minimal sunshine, severely limiting UK renewable energy production.
        
        **Why Batteries Aren't Enough:**
        Lithium-ion batteries are excellent at covering short durations (1-4 hours), but they cannot support the grid for the prolonged periods (5-7 days) seen in Dunkelflaute events.
        """)
        st.info("**Operational Reality:** When the gap opens, NESO issues a Loss of Load Probability (LoLP) warning. This gap must be filled by clean alternatives to prevent blackouts.")
    with col_c2:
        st.markdown('<div class="quote-box">"There is a need for large-scale long-duration storage to ensure security of supply."<br>— <b>The Royal Society</b></div>', unsafe_allow_html=True)

with tab_method:
    st.markdown("### 🧪 Methodology: The 'Digital Twin'")
    st.markdown("We stress-tested the 2030 grid using 2025 historic weather patterns scaled to NESO FES 2030 targets.")
    st.latex(r"\text{Flexibility Gap} = \text{Peak Demand} - (\text{Firm Gen} + \text{Renewables} + \text{Storage})")

with tab_market:
    st.markdown("### 🏗️ Strategic Levers & Market Reform")
    st.markdown("#### The Mitigation Hierarchy: The 'Dispatch Stack'")
    st.markdown("""
    When renewables and batteries are exhausted, the system operator relies on this sequence:

    | Tier | Mitigation Strategy | Potential Impact | Risk / Limitation |
    | :--- | :--- | :--- | :--- |
    | **1** | **Interconnectors** | **15 GW** | **High Risk.** Neighbours often face the same weather event. |
    | **2** | **Nuclear** | **4-6 GW** | **Inflexible.** Baseline only; cannot 'ramp up' for peaks. |
    | **3** | **Demand Side Response (DSR)** | **10 GW** | **Consumer Action.** Paying users to turn off. |
    | **4** | **The Strategic Reserve** | **30 GW** | **The Gap Filler.** Gas with CCS, Hydrogen, or Backup Gas. |
    """)
    st.divider()
    st.markdown("#### Necessary Market Reforms")
    st.write("1. **Locational Marginal Pricing (LMP):** Incentivising batteries to sit where demand is highest.")
    st.write("2. **REMA:** Moving the market to pay for 'Availability' rather than just 'Generation'.")

with tab_refs:
    st.markdown("### 📚 References & Resources")
    st.markdown("* **NESO:** [Future Energy Scenarios](https://www.neso.energy/publications/future-energy-scenarios-fes)")
    st.markdown("* **GitHub:** [suni639/NESO-flexibility-gap](https://github.com/suni639/NESO-flexibility-gap)")

# --- 5. KPI Metrics Row ---
st.divider()
col1, col2, col3, col4 = st.columns(4)
start_date_str = dunkelflaute.index.min().strftime('%d %b')
end_date_str = dunkelflaute.index.max().strftime('%d %b')

with col1: strategy_card("Event Window", f"{start_date_str} - {end_date_str}", "Worst 7 Days")
with col2: strategy_card("Clean Surplus", f"{curtailment:,.1f} TWh", "Wasted Pre-Event")
with col3: strategy_card("Battery Exhaustion", "Day 2", "Of 7-Day Event")
with col4: 
    val_color = "#FF4B4B" if peak_gap_fixed > 5 else "#28A745"
    strategy_card("Real-World Gap", f'<span style="color:{val_color}">{peak_gap_fixed:,.1f} GW</span>', "Unmet Peak Demand")

# --- 6. The Chart ---
st.divider()
st.subheader("🔎 The Dispatch Stack")
fig = go.Figure()
# Nuclear
fig.add_trace(go.Scatter(x=dunkelflaute.index, y=dunkelflaute['Nuclear_Gen_2030_MW']/1000, name='Nuclear', stackgroup='one', fillcolor='rgba(44, 160, 44, 0.6)', line=dict(width=0)))
# Wind/Solar
fig.add_trace(go.Scatter(x=dunkelflaute.index, y=(dunkelflaute['Wind_Gen_2030_MW'] + dunkelflaute['Solar_Gen_2030_MW'])/1000, name='Wind & Solar', stackgroup='one', fillcolor='rgba(31, 119, 180, 0.6)', line=dict(width=0)))
# Batteries
fig.add_trace(go.Scatter(x=dunkelflaute.index, y=dunkelflaute['Battery_Output_MW'].clip(lower=0)/1000, name='Batteries', stackgroup='one', fillcolor='rgba(255, 127, 14, 0.8)', line=dict(width=0)))
# Mitigations (Dynamic)
if mitigation_mw > 0:
    fig.add_trace(go.Scatter(x=dunkelflaute.index, y=pd.Series(mitigation_mw/1000, index=dunkelflaute.index), name='Tiers 1-4 Mitigations', stackgroup='one', fillcolor='rgba(148, 103, 189, 0.6)', line=dict(width=0)))
# Remaining Gap
fig.add_trace(go.Scatter(x=dunkelflaute.index, y=(dunkelflaute['Adjusted_Gap_MW']/1000), name='UNMET GAP', stackgroup='one', fillcolor='rgba(214, 39, 40, 0.5)', line=dict(width=0)))
# Demand Line
fig.add_trace(go.Scatter(x=dunkelflaute.index, y=dunkelflaute['Demand_2030_MW']/1000, name='System Demand', line=dict(color='black', width=2, dash='dot')))

fig.update_layout(yaxis_title="GW", height=550, hovermode="x unified", legend=dict(orientation="h", y=1.02, x=1))
st.plotly_chart(fig, use_container_width=True)

st.markdown("### 📝 Mind The Gap")
st.write("Visualising how the dispatch stack evolves. Red areas show where current clean capacity falls short of demand.")