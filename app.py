import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION ---
API_URL = "https://quant-desk-backend-rata.onrender.com/api/v1"

st.set_page_config(
    page_title="Quant Desk Multi-Timeframe Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR CLEANER METRICS ---
st.markdown(
    """
    <style>
    /* Shrink the main metric value font size */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important; 
    }
    /* Shrink the label size and allow text to wrap instead of truncating */
    [data-testid="stMetricLabel"] {
        font-size: 0.95rem !important;
        white-space: normal !important; 
    }
    /* Shrink the delta indicator font size */
    [data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Auto-refresh the page every 30 seconds (30,000 milliseconds)
st_autorefresh(interval=30000, key="data_refresh")

# --- DATA FETCHING (TALKING TO YOUR BACKEND) ---
@st.cache_data(ttl=30)
def get_telemetry():
    """Fetches all data from your Render backend API."""
    try:
        response = requests.get(f"{API_URL}/telemetry", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}

telemetry = get_telemetry()

# Pull the live spot price directly from backend telemetry, fallback to 63816.00
LIVE_SPOT_PRICE = telemetry.get("spot_price", 63816.00)

# --- SIDEBAR CONTROLS & PLUMBING ---
with st.sidebar:
    st.header("⚙️ Terminal Controls")
    
    st.markdown("### 🌐 Global Plumbing")
    st.metric("DXY Index", "99.80", "-0.15")
    st.metric("US 10Y Yield", "4.74%", "+0.02")
    st.caption("Expanding Macro Liquidity Proxy")
    
    st.markdown("---")
    
    # Fully Functional Trade Manager with Selection Toggles
    st.markdown("### 💼 Active Trade Manager")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        track_macro = st.toggle("🟢 Macro", value=True)
    with col_t2:
        track_swing = st.toggle("🔴 Swing", value=True)
        
    st.markdown("---")
    
    if not track_macro and not track_swing:
        st.info("No active trades selected for tracking.")

    # 1. MACRO LONG POSITION
    if track_macro:
        with st.expander("🟢 MACRO: Active Long", expanded=True):
            st.caption("Multi-Week Bull Expansion")
            macro_entry = st.number_input("Entry Price ($)", value=63177.84, step=10.0, key="m_entry")
            macro_collat = st.number_input("Collateral ($)", value=10000.00, step=100.0, key="m_col")
            macro_lev = st.slider("Leverage", min_value=1.0, max_value=50.0, value=5.0, step=0.5, key="m_lev")
            
            if macro_entry > 0:
                macro_roi = ((LIVE_SPOT_PRICE - macro_entry) / macro_entry) * macro_lev * 100
                macro_pnl = (macro_roi / 100) * macro_collat
                pnl_color = "#00FF00" if macro_pnl >= 0 else "#FF4B4B"
                pnl_sign = "+" if macro_pnl >= 0 else ""
                
                st.markdown("**Live PnL:**")
                st.markdown(f"<h3 style='color:{pnl_color}; margin-top:-15px;'>{pnl_sign}${macro_pnl:,.2f} ({pnl_sign}{macro_roi:,.2f}%)</h3>", unsafe_allow_html=True)

    # 2. SWING SHORT POSITION
    if track_swing:
        with st.expander("🔴 SWING: Active Short", expanded=True):
            st.caption("Tactical Liquidation Wave")
            swing_entry = st.number_input("Entry Price ($)", value=63496.92, step=10.0, key="s_entry")
            swing_collat = st.number_input("Collateral ($)", value=10000.00, step=100.0, key="s_col")
            swing_lev = st.slider("Leverage", min_value=1.0, max_value=50.0, value=12.5, step=0.5, key="s_lev")
            
            if swing_entry > 0:
                swing_roi = ((swing_entry - LIVE_SPOT_PRICE) / swing_entry) * swing_lev * 100
                swing_pnl = (swing_roi / 100) * swing_collat
                pnl_color_s = "#00FF00" if swing_pnl >= 0 else "#FF4B4B"
                pnl_sign_s = "+" if swing_pnl >= 0 else ""
                
                st.markdown("**Live PnL:**")
                st.markdown(f"<h3 style='color:{pnl_color_s}; margin-top:-15px;'>{pnl_sign_s}${swing_pnl:,.2f} ({pnl_sign_s}{swing_roi:,.2f}%)</h3>", unsafe_allow_html=True)

# --- HEADER & GLOBAL OVERVIEW ---
header_col1, header_col2 = st.columns([5, 1])
with header_col1:
    st.title("⚡ QUANT DESK MULTI-TIMEFRAME TERMINAL")
    st.caption("Institutional Decision Matrix & Execution Gateway")
with header_col2:
    with st.popover("⚙️ Settings"):
        st.markdown("**API Connection**")
        if st.button("🔄 Force Telemetry Sync"):
            get_telemetry.clear()
            st.rerun()

st.markdown("## 📊 Live Market Overview")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("LIVE SPOT", f"${LIVE_SPOT_PRICE:,.2f}")
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
    st.write(f"**Live Spot Execution:** ${LIVE_SPOT_PRICE:,.2f}")
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
                colorscale='Magma', # Sleeker dark-to-bright scale
                zsmooth='best',     # Blends blocks into a fluid surface
                showscale=True,
                colorbar=dict(title=dict(text="Depth", font=dict(color="#8892B0")), thickness=12, len=0.8, tickfont=dict(color="#8892B0"))
            ))
            fig_heatmap.update_layout(
                height=420, 
                margin=dict(l=10, r=10, t=30, b=10), 
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", # Transparent background
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(title="Spot Price ($)", tickformat="$,.0f", showgrid=True, gridcolor='rgba(255,255,255,0.05)', titlefont=dict(color="#8892B0"), tickfont=dict(color="#8892B0")),
                xaxis=dict(title="Time (UTC)", showgrid=False, titlefont=dict(color="#8892B0"), tickfont=dict(color="#8892B0"))
            )
            fig_heatmap.add_hline(y=hm_data["upper_wall"], line_dash="dot", line_color="#FF3366", line_width=2, annotation_text="Upper ATR Wall", annotation_font=dict(color="#FF3366"))
            fig_heatmap.add_hline(y=hm_data["lower_wall"], line_dash="dot", line_color="#00E676", line_width=2, annotation_text="Lower Support", annotation_font=dict(color="#00E676"))
            st.plotly_chart(fig_heatmap, use_container_width=True)
    
    with viz_col2:
        st.markdown("### 📉 Deribit Volatility Skew")
        vs_data = telemetry.get("volatility_skew", {})
        if vs_data:
            fig_skew = go.Figure()
            
            # Layer 1: Glow Effect
            fig_skew.add_trace(go.Scatter(
                x=vs_data["deltas"], y=vs_data["iv_surface"], 
                mode='lines', line=dict(color='rgba(0, 255, 204, 0.2)', width=8, shape='spline'),
                hoverinfo='skip', showlegend=False
            ))
            
            # Layer 2: Main sharp line with hollow markers
            fig_skew.add_trace(go.Scatter(
                x=vs_data["deltas"], y=vs_data["iv_surface"], 
                mode='lines+markers', 
                line=dict(color='#00FFCC', width=3, shape='spline'),
                marker=dict(size=10, symbol='diamond', color='#0E1117', line=dict(width=2, color='#00FFCC')),
                fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.08)', showlegend=False
            ))
            
            fig_skew.update_layout(
                height=420, 
                margin=dict(l=10, r=10, t=30, b=10), 
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", 
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="Delta (Puts ← 50 → Calls)", autorange="reversed", showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False, titlefont=dict(color="#8892B0"), tickfont=dict(color="#8892B0")),
                yaxis=dict(title="Implied Volatility (%)", showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False, titlefont=dict(color="#8892B0"), tickfont=dict(color="#8892B0"))
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
