import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

# --- CONFIGURATION ---
API_URL = "https://quant-desk-backend-rata.onrender.com/api/v1"

st.set_page_config(
    page_title="Quant Desk Multi-Timeframe Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DATA FETCHING (TALKING TO YOUR BACKEND) ---
@st.cache_data(ttl=20)
def get_telemetry():
    """Fetches all data from your Render backend API."""
    try:
        response = requests.get(f"{API_URL}/telemetry", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

telemetry = get_telemetry()

# --- SIDEBAR CONTROLS & PLUMBING ---
with st.sidebar:
    st.header("⚙️ Terminal Controls")
    
    st.markdown("### 🌐 Global Plumbing")
    st.metric("DXY Index", "99.80", "-0.15")
    st.metric("US 10Y Yield", "4.74%", "+0.02")
    st.caption("Expanding Macro Liquidity Proxy")
    
    st.markdown("---")
    
    # Corrected Trade Manager: Independent Ideas & 50x Manual Cap
    st.markdown("### 💼 Active Trade Manager")
    
    st.markdown("**Macro Position (2-6 Wks)**")
    st.success("🟢 Active Long (Bull Expansion)")
    macro_lev = st.slider("Macro Leverage", min_value=1.0, max_value=50.0, value=5.0, step=0.5, help="System Max Cap: 10.0x")
    
    st.markdown("**Swing Position (4-24 Hrs)**")
    st.error("🔴 Active Short (Liquidation Wave)")
    swing_lev = st.slider("Swing Leverage", min_value=1.0, max_value=50.0, value=12.5, step=0.5, help="System Max Cap: 10.0x")
    
    st.caption("✅ Independent Trade Ideas Enforced")
    st.caption("⚠️ System Rec Max Cap: 10.0x")

# --- HEADER & GLOBAL OVERVIEW ---
header_col1, header_col2 = st.columns([5, 1])
with header_col1:
    st.title("⚡ QUANT DESK MULTI-TIMEFRAME TERMINAL")
    st.caption("Institutional Decision Matrix & Execution Gateway")
with header_col2:
    # Settings Dropdown at the Top Right
    with st.popover("⚙️ Settings"):
        st.markdown("**API Connection**")
        if st.button("🔄 Force Telemetry Sync"):
            get_telemetry.clear()
            st.rerun()

st.markdown("## 📊 Live Market Overview")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("LIVE SPOT", "$63,816.00")
m2.metric("1H RSI", "58.0")
m3.metric("OPEN INTEREST", "$6.96B")
m4.metric("KELLY LIMIT", "2.5%")
m5.metric("EXECUTION GATE", "⏳ STAND DOWN")

st.markdown("---")

# --- THREE-PILLAR DECISION MATRIX ---
col_macro, col_swing, col_micro = st.columns(3)

with col_macro:
    st.subheader("🌐 1. MACRO HORIZON (2-6 WKS)")
    st.metric("Macro Score Rating", "6.2 / 10")
    st.success("Playbook Directive: LONG (🐂 BULL EXPANSION)")
    st.write("**EMA Anchor Entry:** $63,177.84")
    st.write("**Target 1 (2.0x ATR):** $67,006.80")

with col_swing:
    st.subheader("⚡ 2. TACTICAL SWING (4-24 HRS)")
    st.metric("Tactical Momentum Score", "42.0 / 100")
    st.error("Playbook Directive: TACTICAL LIQUIDATION WAVE")
    st.write("**Retest Entry Trigger:** $63,496.92")
    st.write("**Downward Target 1:** $60,625.20")

with col_micro:
    st.subheader("🎯 3. MICRO STF (1-4 HRS)")
    st.metric("Micro STF Score", "50.0 / 100")
    st.warning("Playbook Directive: ⏳ NEUTRAL / CHOP")
    st.write("**Live Spot Execution:** $63,816.00")
    st.write("**Upper ATR Target:** $65,411.40")

st.markdown("---")

# --- DESK-LEVEL RISK & EXECUTION GATEWAY ---
st.markdown("## 🛡️ DESK-LEVEL RISK & EXECUTION GATEWAY")
rg1, rg2, rg3 = st.columns(3)
rg1.metric("Hierarchical Base Score", "42.8 / 100")
rg2.metric("Enforced Risk Action", "SCALE DOWN RISK (HEDGE ON)")
rg3.metric("Active Liquidation Walls", "Upper $65,411 | Lower $61,582")

st.markdown("---")

# --- INSTITUTIONAL DESK TELEMETRY SECTION ---
st.markdown("## 🔬 INSTITUTIONAL DESK TELEMETRY & LIQUIDITY")

if not telemetry:
    st.error("⚠️ Backend API is currently unreachable or booting up. Please wait 30 seconds and refresh the page...")
else:
    # 1. MARKET SESSION VOLUME & OPEN INFLOW
    st.markdown("### 🕒 Market Session Volume & Open Inflow")
    session_info = telemetry.get("session_cvd", {})
    sc1, sc2, sc3 = st.columns(3)
    
    with sc1:
        st.metric(session_info.get("asia", {}).get("name", "Asia Open"),
                  session_info.get("asia", {}).get("cvd", "N/A"),
                  session_info.get("asia", {}).get("delta", ""))
    with sc2:
        st.metric(session_info.get("london", {}).get("name", "London Open"),
                  session_info.get("london", {}).get("cvd", "N/A"),
                  session_info.get("london", {}).get("delta", ""))
    with sc3:
        st.metric(session_info.get("new_york", {}).get("name", "NY Open"),
                  session_info.get("new_york", {}).get("cvd", "N/A"),
                  session_info.get("new_york", {}).get("delta", ""))
    
    st.markdown("---")
    
    # 2. LIQUIDITY HEATMAP & VOLATILITY SKEW
    viz_col1, viz_col2 = st.columns([2, 1])
    
    with viz_col1:
        st.markdown("### 🗺️ Order Book Liquidity Heatmap")
        hm_data = telemetry.get("orderbook_heatmap", {})
        if hm_data:
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=hm_data["z_matrix"], 
                x=hm_data["time_steps"], 
                y=hm_data["prices"],
                colorscale='Plasma', 
                showscale=True,
                colorbar=dict(title="Depth", thickness=10, len=0.75)
            ))
            fig_heatmap.update_layout(
                height=400, 
                margin=dict(l=10, r=10, t=30, b=10), 
                template="plotly_dark",
                yaxis=dict(title="Spot Price ($)", tickformat="$,.0f", showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                xaxis=dict(title="Time (UTC)", showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            )
            fig_heatmap.add_hline(y=hm_data["upper_wall"], line_dash="dash", line_color="#FF4B4B", annotation_text="Upper ATR Wall")
            fig_heatmap.add_hline(y=hm_data["lower_wall"], line_dash="dash", line_color="#00FF00", annotation_text="Lower Support")
            st.plotly_chart(fig_heatmap, use_container_width=True)
    
    with viz_col2:
        st.markdown("### 📉 Deribit Volatility Skew")
        vs_data = telemetry.get("volatility_skew", {})
        if vs_data:
            fig_skew = go.Figure(data=go.Scatter(
                x=vs_data["deltas"], 
                y=vs_data["iv_surface"], 
                mode='lines+markers', 
                line=dict(color='#00FFFF', width=3, shape='spline'),
                marker=dict(size=10, symbol='diamond', color='#00FFFF', line=dict(width=1, color='white')),
                fill='tozeroy',
                fillcolor='rgba(0, 255, 255, 0.05)'
            ))
            fig_skew.update_layout(
                height=400, 
                margin=dict(l=10, r=10, t=30, b=10), 
                template="plotly_dark", 
                xaxis=dict(title="Delta (Puts ← 50 → Calls)", autorange="reversed", showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(title="Implied Volatility (%)", showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            )
            st.plotly_chart(fig_skew, use_container_width=True)
            
    st.markdown("---")
    
    # 3. ON-CHAIN MACRO FLOWS
    st.markdown("### ⛓️ On-Chain Exchange Flows")
    oc_data = telemetry.get("onchain_flows", {})
    oc1, oc2, oc3 = st.columns(3)
    
    with oc1:
        st.metric("24H BTC Net Exchange Flow", oc_data.get("btc_netflow_24h", "N/A"), "Cold Storage Absorption")
    with oc2:
        st.metric("24H Stablecoin Mint Velocity", oc_data.get("stablecoin_mint_24h", "N/A"), "Purchasing Power Expansion")
    with oc3:
        st.metric("Global Exchange Reserve Trend", oc_data.get("exchange_reserve_trend", "N/A"))
