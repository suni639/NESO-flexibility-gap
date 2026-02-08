# 🇬🇧 Clean Power 2030: The Green Energy Gap
### *Stress-testing the UK grid against a 1-in-10-year wind drought.*

<br>

<h3 align="center">🚀 Click below to launch the interactive strategy dashboard:</h3>

<p align="center">
  <a href="https://neso-flexibility-gap-ngtgqkkhevm2uu4sa4ew2k.streamlit.app/" target="_blank">
    <img src="https://static.streamlit.io/badges/streamlit_badge_black_white.svg" alt="Open Live Streamlit Dashboard" height="85">
  </a>
</p>

<p align="center">
  <em>This runs the full simulation instantly in your web browser.<br>No installation or technical knowledge required.</em>
</p>

<br>

<p align="center">
  
![Project Status](https://img.shields.io/badge/Status-Complete-green) ![Python](https://img.shields.io/badge/Built%20With-Python%20%7C%20Streamlit-blue) ![Data](https://img.shields.io/badge/Data-NESO%20%7C%20Elexon%20%7C%20UK%20Gov-orange)
</p>

---

## 1. Project Objective & Key Findings

**The Goal:** To quantify the **"Clean Power Gap"**—the specific volume of firm, dispatchable capacity (GW) and energy (TWh) required to secure the UK grid during a severe weather stress event (Dunkelflaute), assuming the full delivery of the Government's Clean Power 2030 renewable targets.

**The Findings:**
* **The "Gap" Defined:** During a severe winter calm (modelled on 2025 weather patterns scaled to 2030), the grid faces a capacity shortfall of **~51 GW**, even after dispatching a targeted 25 GW battery fleet.
* **The Failure Mode:** Short-duration (Li-ion) batteries exhausted their energy reserves within the **first 24 hours** of the 120-hour stress window.
* **Strategic Implication:** The project shows the potential vulnerabilities of our energy system, and that "Flexibility" is not a single bucket. While batteries solve *intraday* volatility (seconds to hours), they provide **zero security** for *inter-day* weather risks. The 51 GW gap effectively defines the requirement for **Long Duration Energy Storage (LDES)** and Low-Carbon Gas (CCS/Hydrogen).

---

## 2. Context & Clean Power 2030 (CP30)

CP30 (Clean Power 2030) is the government’s comprehensive roadmap to achieve a decarbonised electricity system by 2030. 

Key aspects of the plan include:
* **Target:** Transitioning the energy mix so that "clean" sources—including renewables (wind, solar), nuclear, and carbon capture (CCS)—account for at least 95% of generation in a typical weather year.
* **Strategic Planning:** Commissioned by the Department for Energy Security and Net Zero (DESNZ) and developed by the National Energy System Operator (NESO), it replaces the previous developer-led approach with a coordinated, whole-system strategy.
* **Grid Connection Reform:** A major pillar of CP30 is overhauling the grid connection queue from a "first-come, first-served" basis to a "first ready and needed, first connected" model. This prioritises projects that are both viable and strategically aligned with the 2030 goals.
* **Infrastructure Investment:** It estimates a "once-in-a-generation" upgrade requiring approximately £40 billion in annual investment to build the necessary generation and network capacity.
* **Pathways:** The plan evaluates different technological routes, such as a "High Renewables" pathway focusing on 50GW of offshore wind, versus a "High Dispatch" pathway with more reliance on nuclear and low-carbon dispatchable power

### The Critical Question
As coal closes and gas is relegated to standby, what physically keeps the lights on when the wind output drops to <5% of capacity for multiple days?

---

## 3. The Threat: "Dunkelflaute" Events

In the context of CP30, ***Dunkelflaute*** (a German term for "dark doldrums"—periods with little-to-no solar or wind generation) is considered the acid test of the entire strategy.

While the UK aims for a system that is 95% clean, experts such as the National Energy System Operator (NESO) acknowledge that the remaining 5% of the time (i.e., the Dunkelflaute periods) presents the greatest technical and financial risk.

* **Definition:** Dunkelflaute is a period characterised by **low wind speeds (<10% capacity)**, **low solar irradiance**, and **cold temperatures** (driving high heating demand).

* **Scale of the Challenge:** These are recurring climate features, not anomalies. While minor lulls happen often, historical data confirms that severe events lasting **3–10 days** occur roughly every **2–5 years**. NESO’s analysis suggests that by 2030, the UK could face a deficit of tens of gigawatts during these periods. Current battery technology (which usually provides 2–4 hours of storage) is insufficient for this "long-duration" challenge.

* **The "Correlated Risk":** It's important to note that these events are caused by massive high-pressure systems that often sit over the entire North Sea region. This affects the UK, France, Germany, and the Netherlands simultaneously, drastically reducing the reliability of imports just when we'd need them most.

---

## 4. Mitigations & The "Dispatch Stack"

If batteries fail the 5-day test (as shown by the model), the project highlights the hierarchy of mitigations required to fill the 51 GW gap:

| Tier | Mitigation Strategy | Potential Impact | Risk / Limitation |
| :--- | :--- | :--- | :--- |
| **1** | **Interconnectors** | ~10-15 GW | **High Risk.** We can import power, but only if our neighbours aren't suffering the same weather event. |
| **2** | **Nuclear** | ~4-6 GW | **Inflexible.** Provides a stable floor (Baseload) but cannot easily "ramp up" to fill a sudden 50GW gap. |
| **3** | **Demand Side Response (DSR)** | ~5-10 GW | **Consumer Action.** Paying heavy industry to shut down and consumers to lower usage. |
| **4** | **The Strategic Reserve** | **~30 GW** | **The Gap Filler.** The remaining shortfall must be met by Gas with CCS (Carbon Capture), Hydrogen Turbines, or keeping unabated gas plants on standby as a "last resort" insurance policy. |

---

## 5. Data & Methodology

A **"Digital Twin"** approach was utilised to stress-test the 2030 grid:
* **Weather Profile:** Used **2025 Historic Demand & Settlement Data (Elexon)** to capture the exact physics of a "Cold Dunkelflaute" (load factors <3%).
* **Future Scaling:** Applied **NESO FES 2030** and **CP30 Action Plan** targets to scale the wind/solar amplitude (e.g., scaling wind output to hit 50 GW capacity).
* **Simulation Engine:** A custom Python dispatch engine calculated the net deficit half-hour by half-hour, prioritising `Renewables` > `Batteries` > `Fossil Backup`.

---

## 6. Project Limitations

* **Island Mode:** The model treats GB as an island. While conservative, this is standard "Security of Supply" planning practice, as relying on imports during a pan-European weather event is statistically dangerous.
* **Transmission Constraints:** The model assumes power generated in Scotland can freely reach London ("Copper Plate" assumption). In reality, transmission bottlenecks (the B6 boundary) would make the gap *worse* by trapping wind power in the North.

---

## 7. Expert Consensus & Sources

* **The Royal Society (2023):** *Large-scale Electricity Storage Report.* Concluded that wind/solar require up to **100 TWh** of storage (Hydrogen) to bridge weather gaps. Batteries offer only GWh scale.
* **NESO (2025):** *Clean Power 2030 Advice.* Acknowledges that unabated gas must remain on the system as a "strategic reserve" to ensure supply during these periods.
* **Climate Change Committee (CCC):** Continues to highlight "Security of Supply" as the primary risk of the 2030 target.

---

## 🖥️ How to Run This App (For Non-Technical Users)

You can run this simulation on your own computer to test different scenarios (e.g., "What if we double the batteries?").

### Prerequisites
1.  **Install Python:** Download and install Python (Version 3.10 or higher) from [python.org](https://www.python.org/downloads/).
    * *Note: During installation, tick the box that says "Add Python to PATH".*
2.  **Download Code:** Click the green **"Code"** button at the top of this GitHub page and select **"Download ZIP"**. Unzip the folder to your Desktop.

### Step 1: Install Dependencies
Open your computer's "Command Prompt" (Windows) or "Terminal" (Mac).
Type the following commands (press Enter after each line):

```bash
cd Desktop/NESO-flexibility-gap  # (Or whatever you named the folder)
pip install -r requirements.txt
```
*This installs the necessary tools (pandas, streamlit, plotly).*

### Step 2: Launch the Dashboard
In the same terminal window, type:

```bash
streamlit run app.py
```
A web browser window will open automatically. You can now use the sliders on the left to adjust the 2030 grid strategy and see if you can keep the lights on!

---

## 🧠 Glossary / Jargon Buster

| Term | Definition |
| :--- | :--- |
| **GW (Gigawatt)** | The **Speed** of power. How much electricity we need *right now*. (Peak UK demand is ~60 GW). |
| **GWh (Gigawatt-hour)** | The **Volume** of energy. How much is in the "tank" (battery). |
| **Dunkelflaute** | German for "Dark Lull." A period of cold, dark, still weather. |
| **Load Factor** | How hard a wind turbine is working. 100% = Full power. 5% = Barely spinning. |
| **Dispatchable** | Power sources we can turn on/off at will (Gas, Nuclear, Batteries). Wind is *not* dispatchable. |
