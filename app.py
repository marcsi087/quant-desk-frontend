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

# --- CUSTOM CSS ---
st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.90rem !important; white-space: normal !important; color: #8892B0 !important; }
    [data-testid="stMetricDelta"] { font-size: 0.85rem !important; }
    table { width: 100%; border-collapse: collapse; }
    th { color: #8892B0; font-size: 0.85rem; text-transform: uppercase; border-bottom: 1px solid #444 !important; }
    td { font-size: 0.95rem; border-bottom: 1px solid #222 !important; padding: 6px 0px !important; }
    </style>
    """,
    unsafe_allow_html=True
)

st_autorefresh(interval=30000, key="data_refresh")

# --- DATA FETCHING ---
@st.cache_data(ttl=30)
def get_telemetry():
    try:
        response = requests.get(f"{API_URL}/telemetry", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}

telemetry = get_telemetry()

# PULL LIVE TELEMETRY VARIABLES
LIVE_SPOT_PRICE = telemetry.get("spot_price", 64347.99)
FUNDING_RATE = telemetry.get("funding_rate", 0.00066)
FUNDING_RATE_PCT = FUNDING_RATE * 100
OPEN_INTEREST = telemetry.get("open_interest", "$7.02B")

ta = telemetry.get("ta", {"rsi": 58.0, "vwap": 63888.00})
scores = telemetry.get("scores", {"macro": 6.2, "swing": 42.0, "micro": 50.0})
macro_score = scores.get("macro", 6.2)
swing_score = scores.get("swing", 42.0)
micro_score = scores.get("micro", 50.0)

setups = telemetry.get("trade_setups", {})
plumbing = telemetry.get("macro_plumbing", {"dxy": "99.80", "us10y": "4.74%"})
insights = telemetry.get("insights", {})

# --- TIERED EXECUTION GATE LOGIC ---
# Define the baseline regime (Assuming > 5.0 is Bullish, < 5.0 is Bearish)
macro_bull = macro_score >= 5.0

# Tier 1: Perfect Alignment (Trend + Momentum)
if macro_bull and swing_score >= 55.0 and micro_score >= 50.0:
    exec_gate = "🟢 FULL DEPLOY (LONG)"
elif not macro_bull and swing_score <= 45.0 and micro_score <= 45.0:
    exec_gate = "🔴 FULL DEPLOY (SHORT)"

# Tier 2: Aggressive Tactical (Trading against the Macro trend on momentum)
elif macro_bull and swing_score <= 45.0 and micro_score <= 45.0:
    exec_gate = "🟡 TACTICAL HEDGE (SHORT PULLBACK)"
elif not macro_bull and swing_score >= 55.0 and micro_score >= 50.0:
    exec_gate = "🟡 TACTICAL COUNTER (LONG BOUNCE)"

# Tier 3: Choppy / Mixed Signals
else:
    exec_gate = "⏳ SCALP ONLY / STAND DOWN"

# --- DYNAMIC KELLY CRITERION ---
# W = Win Rate (Proxied by Tactical Score)
W = swing_score / 100.0

# R = Reward/Risk Ratio (Derived from Tactical Setups)
s_setups = setups.get("tactical", {})
s_entry = s_setups.get('entry', LIVE_SPOT_PRICE)
s_t2 = s_setups.get('t2', 62800.00)
s_sl = s_setups.get('sl', 65411.00)

reward = abs(s_entry - s_t2)
risk = abs(s_entry - s_sl)

if risk > 0:
    R = reward / risk
    # Kelly Formula: K = W - ((1 - W) / R)
    kelly_fraction = W - ((1 - W) / R)
    quarter_kelly = max(0.0, (kelly_fraction / 4) * 100)
else:
    quarter_kelly = 0.0

kelly_display = f"{quarter_kelly:.2f}%"

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("<h3 style='margin-bottom:20px;'>⚙️ Terminal Controls</h3>", unsafe_allow_html=True)
    st.markdown("<h5 style='color:#8892B0; margin-bottom:10px;'>🌐 Global Plumbing</h5>", unsafe_allow_html=True)
    st.metric("DXY Index", plumbing.get("dxy", "99.80"), "-0.15")
    st.metric("US 10Y Yield", plumbing.get("us10y", "4.74%"), "+0.02")
    st.caption("Expanding Macro Liquidity Proxy")
    
    st.markdown("<hr style='border:1px solid #333; margin: 20px 0;'>", unsafe_allow_html=True)
    
    st.markdown("<h5 style='color:#8892B0; margin-bottom:10px;'>💼 Active Trade Manager</h5>", unsafe_allow_html=True)
    col_t1, col_t2 = st.columns(2)
    with col_t1: track_macro = st.toggle("🟢 Macro", value=True)
    with col_t2: track_swing = st.toggle("🔴 Swing", value=True)
        
    st.markdown("<hr style='border:1px solid #333; margin: 20px 0;'>", unsafe_allow_html=True)
    
    if not track_macro and not track_swing:
        st.info("No active trades selected.")

    if track_macro:
        with st.expander("🟢 MACRO: Active Long", expanded=True):
            macro_entry = st.number_input("Entry Price ($)", value=63177.84, step=10.0, key="m_entry")
            macro_collat = st.number_input("Collateral ($)", value=10000.00, step=100.0, key="m_col")
            macro_lev = st.slider("Leverage", min_value=1.0, max_value=50.0, value=5.0, step=0.5, key="m_lev")
            if macro_entry > 0:
                macro_roi = ((LIVE_SPOT_PRICE - macro_entry) / macro_entry) * macro_lev * 100
                macro_pnl = (macro_roi / 100) * macro_collat
                pnl_color = "#00E676" if macro_pnl >= 0 else "#FF3366"
                pnl_sign = "+" if macro_pnl >= 0 else ""
                st.markdown(f"<p style='margin-bottom:2px; color:#8892B0;'>Live PnL:</p><h4 style='color:{pnl_color}; margin-top:0;'>{pnl_sign}${macro_pnl:,.2f} ({pnl_sign}{macro_roi:,.2f}%)</h4>", unsafe_allow_html=True)

    if track_swing:
        with st.expander("🔴 SWING: Active Short", expanded=True):
            swing_entry = st.number_input("Entry Price ($)", value=64260.00, step=10.0, key="s_entry")
            swing_collat = st.number_input("Collateral ($)", value=319.00, step=100.0, key="s_col")
            swing_lev = st.slider("Leverage", min_value=1.0, max_value=50.0, value=30.0, step=0.5, key="s_lev")
            if swing_entry > 0:
                swing_roi = ((swing_entry - LIVE_SPOT_PRICE) / swing_entry) * swing_lev * 100
                swing_pnl = (swing_roi / 100) * swing_collat
                pnl_color_s = "#00E676" if swing_pnl >= 0 else "#FF3366"
                pnl_sign_s = "+" if swing_pnl >= 0 else ""
                st.markdown(f"<p style='margin-bottom:2px; color:#8892B0;'>Live PnL:</p><h4 style='color:{pnl_color_s}; margin-top:0;'>{pnl_sign_s}${swing_pnl:,.2f} ({pnl_sign_s}{swing_roi:,.2f}%)</h4>", unsafe_allow_html=True)

# --- HEADER & OVERVIEW ---
header_col1, header_col2 = st.columns([5, 1])
with header_col1:
    st.markdown("<h2 style='margin-bottom:0;'>⚡ QUANT DESK TERMINAL</h2>", unsafe_allow_html=True)
    st.caption("Institutional Decision Matrix & Execution Gateway")
with header_col2:
    with st.popover("⚙️ Settings"):
        st.markdown("**API Connection**")
        if st.button("🔄 Force Sync"):
            get_telemetry.clear()
            st.rerun()

# --- DYNAMIC RISK BANNER ---
if FUNDING_RATE < 0:
    st.warning(f"⚠️ **SYSTEM ALERT: SHORT SQUEEZE RISK** | **Avg Perp Funding: {FUNDING_RATE_PCT:.4f}%** | Negative CVD paired with massive liquidity above $65.4k.")
else:
    st.info(f"ℹ️ **SYSTEM STATUS: NORMAL** | **Avg Perp Funding: {FUNDING_RATE_PCT:.4f}%** | Market structure balanced.")

# ==========================================
# HELPER FUNCTION FOR CLEAN HEADERS
# ==========================================
def render_header(title):
    st.markdown(f"""
        <h4 style='
            color: #E0E0E0; 
            border-bottom: 1px solid #333; 
            padding-bottom: 10px; 
            margin-top: 40px; 
            margin-bottom: 25px; 
            text-transform: uppercase; 
            letter-spacing: 1px;
        '>{title}</h4>
    """, unsafe_allow_html=True)

# ==========================================
# SECTION 1: LIVE MARKET OVERVIEW
# ==========================================
render_header("📊 Live Market Overview")

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Live Spot", f"${LIVE_SPOT_PRICE:,.2f}")
m2.metric("1H RSI", f"{ta.get('rsi', 58.0)}")
m3.metric("1H VWAP", f"${ta.get('vwap', 63888.0):,.2f}")
m4.metric("Open Interest", OPEN_INTEREST)
m5.metric("Kelly Limit", kelly_display) # <-- Updated to dynamic variable
m6.metric("Execution Gate", exec_gate)

# ==========================================
# SECTION 2: MULTI-TIMEFRAME MATRIX (SPREADSHEET GRID W/ T1, T2, SL)
# ==========================================
render_header("🧠 Decision Matrix")

col_macro, col_swing, col_micro = st.columns(3)

with col_macro:
    st.markdown("**🌐 1. MACRO HORIZON (2-6 WKS)**")
    if macro_score >= 6.0:
        st.success("Directive: LONG (🐂 BULL EXPANSION)")
    elif macro_score <= 4.0:
        st.error("Directive: SHORT (🐻 BEAR CONTRACTION)")
    else:
        st.warning("Directive: ⏳ NEUTRAL / CHOP")
        
    m_setups = setups.get("macro", {})
    st.markdown(f"""
    | Parameter | Target / Level |
    | :--- | :--- |
    | **Macro Score** | `{macro_score} / 10` |
    | **Entry Zone** | `${m_setups.get('entry', 63177):,.2f}` |
    | **Conservative T1** | `${m_setups.get('t1', 66000):,.2f}` |
    | **Aggressive T2** | `${m_setups.get('t2', 68200):,.2f}` |
    | **Stop Loss (SL)** | `${m_setups.get('sl', 62400):,.2f}` |
    """)

with col_swing:
    st.markdown("**⚡ 2. TACTICAL SWING (4-24 HRS)**")
    if swing_score >= 60.0:
        st.success("Directive: TACTICAL LONG RALLY")
    elif swing_score <= 45.0:
        st.error("Directive: TACTICAL LIQUIDATION WAVE")
    else:
        st.warning("Directive: ⏳ CHOP / NO TRADE")
        
    s_setups = setups.get("tactical", {})
    st.markdown(f"""
    | Parameter | Target / Level |
    | :--- | :--- |
    | **Tactical Score** | `{swing_score} / 100` |
    | **Entry Zone** | `${s_setups.get('entry', LIVE_SPOT_PRICE):,.2f}` |
    | **Conservative T1** | `${s_setups.get('t1', 63850):,.2f}` |
    | **Aggressive T2** | `${s_setups.get('t2', 62800):,.2f}` |
    | **Stop Loss (SL)** | `${s_setups.get('sl', 65411):,.2f}` |
    """)

with col_micro:
        st.markdown("**🎯 3. MICRO STF (1-4 HRS)**")
        if micro_score >= 60.0:
            st.success("Directive: 🟢 AGGRESSIVE LONG")
        elif micro_score <= 40.0:
            st.error("Directive: 🔴 AGGRESSIVE SHORT")
        else:
            st.warning("Directive: ⏳ NEUTRAL / CHOP")
        
        mi_setups = setups.get("micro", {})
        mi_t1 = mi_setups.get('t1', 65000.00)
        mi_t2 = mi_setups.get('t2', 65411.00)
        mi_sl = mi_setups.get('sl', 63600.00)
        
        # --- DIRECTIONAL INVERSION PATCH ---
        # If score indicates a short, but T1 is plotted above the live spot, invert the matrix
        if micro_score <= 40.0 and mi_t1 > LIVE_SPOT_PRICE:
            delta_t1 = mi_t1 - LIVE_SPOT_PRICE
            delta_t2 = mi_t2 - LIVE_SPOT_PRICE
            delta_sl = LIVE_SPOT_PRICE - mi_sl
            
            mi_t1 = LIVE_SPOT_PRICE - delta_t1
            mi_t2 = LIVE_SPOT_PRICE - delta_t2
            mi_sl = LIVE_SPOT_PRICE + delta_sl
            
        st.markdown(f"""
        | Parameter | Target / Level |
        | :--- | :--- |
        | **Micro Score** | `{micro_score} / 100` |
        | **Live Spot Exec** | `${LIVE_SPOT_PRICE:,.2f}` |
        | **Conservative T1** | `${mi_t1:,.2f}` |
        | **Aggressive T2** | `${mi_t2:,.2f}` |
        | **Stop Loss (SL)** | `${mi_sl:,.2f}` |
        """)

# ==========================================
# SECTION 3: PLAYBOOK MANIFESTO
# ==========================================
if insights:
    render_header("📜 Playbook Manifesto")
    if macro_score >= 6.0:
        playbook_color = st.success
    elif macro_score <= 4.0:
        playbook_color = st.error
    else:
        playbook_color = st.info
    
    playbook_color(f"**🛡️ INSTITUTIONAL DIRECTIVE:** {insights.get('institutional_guidance', 'N/A')}")
    playbook_color(f"**🧠 LIQUIDITY THESIS:** {insights.get('liquidity_thesis', 'N/A')}")

# ==========================================
# SECTION 4: RISK GATEWAY
# ==========================================
render_header("🛡️ Desk-Level Risk Gateway")

rg1, rg2, rg3, rg4 = st.columns(4)
rg1.metric("Risk Base Score", "42.8 / 100")
rg2.metric("Desk Directive", "SCALE DOWN (HEDGE)")
rg3.metric("Upper Liq Wall", "$65,411")
rg4.metric("Lower Liq Wall", "$61,582")

# ==========================================
# SECTION 5: TELEMETRY & CHARTS
# ==========================================
render_header("🔬 Telemetry & Liquidity")

if not telemetry:
    st.error("⚠️ Backend API is currently unreachable. Retrying in 30 seconds...")
else:
    session_info = telemetry.get("session_cvd", {})
    sc1, sc2, sc3 = st.columns(3)
    with sc1: st.metric(session_info.get("asia", {}).get("name", "Asia Open"), session_info.get("asia", {}).get("cvd", "N/A"), session_info.get("asia", {}).get("delta", ""))
    with sc2: st.metric(session_info.get("london", {}).get("name", "London Open"), session_info.get("london", {}).get("cvd", "N/A"), session_info.get("london", {}).get("delta", ""))
    with sc3: st.metric(session_info.get("new_york", {}).get("name", "NY Open"), session_info.get("new_york", {}).get("cvd", "N/A"), session_info.get("new_york", {}).get("delta", ""))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    viz_col1, viz_col2 = st.columns([2, 1])
    with viz_col1:
        st.markdown("**🗺️ Order Book Liquidity Heatmap**")
        hm_data = telemetry.get("orderbook_heatmap", {})
        if hm_data:
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=hm_data["z_matrix"], x=hm_data["time_steps"], y=hm_data["prices"],
                colorscale='Turbo', showscale=True,
                colorbar=dict(title=dict(text="Depth", font=dict(color="#8892B0")), thickness=12, len=0.8, tickfont=dict(color="#8892B0"))
            ))
            fig_heatmap.update_layout(
                height=400, margin=dict(l=0, r=0, t=20, b=0), template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(title=dict(text="Spot Price ($)", font=dict(color="#8892B0")), tickformat="$,.0f", showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color="#8892B0")),
                xaxis=dict(showgrid=False, tickfont=dict(color="#8892B0"))
            )
            fig_heatmap.add_hline(y=hm_data["upper_wall"], line_dash="dot", line_color="#FF3366", line_width=1, annotation_text="Upper Wall", annotation_font=dict(color="#FF3366"))
            fig_heatmap.add_hline(y=hm_data["lower_wall"], line_dash="dot", line_color="#00E676", line_width=1, annotation_text="Lower Support", annotation_font=dict(color="#00E676"))
            st.plotly_chart(fig_heatmap, use_container_width=True)
    
    with viz_col2:
        st.markdown("**📉 Deribit Volatility Skew**")
        vs_data = telemetry.get("volatility_skew", {})
        if vs_data:
            fig_skew = go.Figure()
            fig_skew.add_trace(go.Scatter(
                x=vs_data["deltas"], y=vs_data["iv_surface"], 
                mode='lines', line=dict(color='rgba(0, 255, 204, 0.2)', width=8, shape='spline'),
                hoverinfo='skip', showlegend=False
            ))
            fig_skew.add_trace(go.Scatter(
                x=vs_data["deltas"], y=vs_data["iv_surface"], 
                mode='lines', line=dict(color='#00FFCC', width=3, shape='spline'),
                fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.08)', showlegend=False
            ))
            fig_skew.update_layout(
                height=400, margin=dict(l=0, r=0, t=20, b=0), template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title=dict(text="Delta", font=dict(color="#8892B0")), autorange="reversed", showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False, tickfont=dict(color="#8892B0")),
                yaxis=dict(title=dict(text="Implied Volatility (%)", font=dict(color="#8892B0")), showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False, tickfont=dict(color="#8892B0"))
            )
            st.plotly_chart(fig_skew, use_container_width=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("**⛓️ On-Chain Exchange Flows**")
    oc_data = telemetry.get("onchain_flows", {})
    oc1, oc2, oc3 = st.columns(3)
    with oc1: st.metric("24H Net Exchange Flow", oc_data.get("btc_netflow_24h", "N/A"), "Cold Storage Absorption")
    with oc2: st.metric("24H Stablecoin Mint", oc_data.get("stablecoin_mint_24h", "N/A"), "Purchasing Power")
    with oc3: st.metric("Global Reserve Trend", oc_data.get("exchange_reserve_trend", "N/A"))

# ==========================================
# SECTION 6: QUANTITATIVE MARKET DATA & ANALYTICAL GUIDANCE
# ==========================================
if insights:
    render_header("📝 Quantitative Market Data & Guidance")
    
    vp_col, cat_col, guide_col = st.columns(3)
    
    with vp_col:
        st.markdown("**📊 Volume Profile**")
        vp = insights.get("volume_profile", {})
        st.write(f"- **Point of Control (POC):** {vp.get('poc', 'N/A')}")
        st.write(f"- **Value Area High (VAH):** {vp.get('vah', 'N/A')}")
        st.write(f"- **Value Area Low (VAL):** {vp.get('val', 'N/A')}")
        
    with cat_col:
        st.markdown("**⚠️ Upcoming Catalysts**")
        for cat in insights.get("catalysts", []):
            st.write(f"- {cat}")
            
    with guide_col:
        st.markdown("**🧭 Desk-Level Action Plan**")
        st.info("Execute scaling limits only at structural value nodes. Monitor funding rate bleed closely for squeeze continuation.")
