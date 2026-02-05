# Plotly chart configurations
import plotly.graph_objects as go
import pandas as pd

def plot_dunkelflaute(stress_df):
    """
    Plots the specific 5-day Dunkelflaute event.
    """
    fig = go.Figure()
    
    # 1. The Demand Line (The Target)
    fig.add_trace(go.Scatter(
        x=stress_df.index, y=stress_df['Demand_2030_MW'],
        mode='lines', name='Demand (2030)',
        line=dict(color='black', width=3)
    ))
    
    # 2. The Clean Generation (Wind + Solar + Nuclear)
    total_clean = (stress_df['Wind_Gen_2030_MW'] + 
                   stress_df['Solar_Gen_2030_MW'] + 
                   stress_df['Nuclear_Gen_2030_MW'])
                   
    fig.add_trace(go.Scatter(
        x=stress_df.index, y=total_clean,
        mode='lines', name='Total Clean Gen',
        line=dict(color='green', width=1),
        fill='tozeroy' # Fills area under curve
    ))
    
    # 3. The Gap (Red Area)
    # We cheat visually by plotting the Gap as a filled area between Clean and Demand
    # Ideally, use a stacked bar or simple fill, but this is clear enough for now.
    
    fig.update_layout(
        title="The 'Dunkelflaute' Event: 5 Days of Low Wind",
        xaxis_title="Date",
        yaxis_title="Power (MW)",
        template="plotly_white",
        height=500
    )
    
    return fig
