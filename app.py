import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION ---
API_URL = "https://quant-desk-backend-rata.onrender.com/api/v1"
st.set_page_config(page_title="Quant Desk Multi-Timeframe Terminal", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS ---
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.4rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.90rem !important; white-space: normal !important; color: #8892B0 !important; }
[data-testid="stMetricDelta"] { font-size: 0.85rem !important; }
table { width: 100%; border-collapse: collapse; }
th { color: #8892B0; font-size: 0.85rem; text-transform: uppercase; border-bottom: 1px solid #444 !important; }
td { font-size: 0.95rem; border-bottom: 1px solid #222 !important; padding: 6px 0px !important; }
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=60000, key="data_refresh")

# --- DATA FETCHING ---
@st.cache_data(ttl=30)
def get_telemetry():
    try:
        response = requests.get(f"{API_URL}/telemetry", timeout=10)
        if response.status_code == 200: return response.json()
    except: pass
    return {}

telemetry = get_telemetry()

# PULL LIVE TELEMETRY VARIABLES
LIVE_SPOT_PRICE = telemetry.get("spot_price", 64347.99)
FUNDING_RATE = telemetry.get("funding_rate", 0.00066)
FUNDING_RATE_PCT = FUNDING_RATE * 100
OPEN_INTEREST = telemetry.get("open_interest", "$7.02B")
ta = telemetry.get("ta", {"rsi": 58.0, "vwap": 63888.00, "atr_pct": 0.01})
scores = telemetry.get("scores", {"macro": 6.2, "swing": 42.0, "micro": 50.0})
macro_score = scores.get("macro", 6.2)
swing_score = scores.get("swing", 42.0)
micro_score = scores.get("micro", 50.0)
setups = telemetry.get("trade_setups", {})

plumbing = telemetry.get("macro_plumbing", {
    "dxy": {"value": "104.20", "delta": "-0.15"}, "us10y": {"value": "4.250%", "delta": "+0.020"},
    "vix": {"value": "14.50", "delta": "-0.50"}, "sp500": {"value": "5,200", "delta": "+45"}
})
insights = telemetry.get("insights", {})

# --- TIERED EXECUTION GATE LOGIC ---
macro_bull, macro_bear = macro_score >= 5.5, macro_score <= 4.5
if macro_bull and micro_score <= 45.0: exec_gate = "⚠️ COUNTER-TREND TRAP (MACRO 🐂 / MICRO 🐻)"
elif macro_bear and micro_score >= 55.0: exec_gate = "⚠️ COUNTER-TREND TRAP (MACRO 🐻 / MICRO 🐂)"
elif macro_bull and swing_score >= 52.0 and micro_score >= 50.0: exec_gate = "🟢 FULL DEPLOY (LONG)"
elif macro_bear and swing_score <= 48.0 and micro_score <= 48.0: exec_gate = "🔴 FULL DEPLOY (SHORT)"
elif macro_bull and swing_score <= 48.0 and micro_score <= 48.0: exec_gate = "🟡 TACTICAL HEDGE (SHORT PULLBACK)"
elif macro_bear and swing_score >= 52.0 and micro_score >= 50.0: exec_gate = "🟡 TACTICAL COUNTER (LONG BOUNCE)"
else: exec_gate = "⏳ SCALP ONLY / STAND DOWN"

# --- DYNAMIC KELLY CRITERION ---
W = (swing_score / 100.0) if swing_score >= 50.0 else ((100.0 - swing_score) / 100.0)
s_setups = setups.get("tactical", {})
s_entry, s_t2, s_sl = s_setups.get('entry', LIVE_SPOT_PRICE), s_setups.get('t2', 62800.00), s_setups.get('sl', 65411.00)
reward, risk = abs(s_entry - s_t2), abs(s_entry - s_sl)

if risk > 0:
    R = reward / risk
    quarter_kelly = max(0.0, ((W - ((1 - W) / R)) / 4) * 100)
else:
    quarter_kelly = 0.0
kelly_display = f"{quarter_kelly:.2f}%"

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("<h3 style='margin-bottom:20px;'>⚙️ Terminal Controls</h3>", unsafe_allow_html=True)
    st.markdown("<h5 style='color:#8892B0; margin-bottom:10px;'>🌐 Global Plumbing</h5>", unsafe_allow_html=True)
    
    pl1, pl2 = st.columns(2)
    dxy_raw = plumbing.get("dxy", {})
    sp500_raw = plumbing.get("sp500", {})
    us10y_raw = plumbing.get("us10y", {})
    vix_raw = plumbing.get("vix", {})
    
    dxy = dxy_raw if isinstance(dxy_raw, dict) else {"value": dxy_raw, "delta": "0.0"}
    sp500 = sp500_raw if isinstance(sp500_raw, dict) else {"value": sp500_raw, "delta": "0"}
    us10y = us10y_raw if isinstance(us10y_raw, dict) else {"value": us10y_raw, "delta": "0.0"}
    vix = vix_raw if isinstance(vix_raw, dict) else {"value": vix_raw, "delta": "0.0"}
    
    with pl1:
        st.metric("DXY Index", dxy.get("value", "104.20"), dxy.get("delta", "-0.15"), delta_color="inverse", help="US Dollar strength. Up is bearish for crypto.")
        st.metric("S&P 500", sp500.get("value", "5,200"), sp500.get("delta", "+45"), delta_color="normal", help="Global equity correlation. Up is bullish for crypto.")
    with pl2:
        st.metric("US 10Y Yield", us10y.get("value", "4.25%"), us10y.get("delta", "+0.02"), delta_color="inverse", help="Risk-free rate. Up is bearish for crypto.")
        st.metric("VIX", vix.get("value", "14.50"), vix.get("delta", "-0.50"), delta_color="inverse", help="Market fear gauge. Up is bearish for crypto.")
    
    st.caption("🟢 Bullish Signal | 🔴 Bearish Signal")
    st.markdown("<hr style='border:1px solid #333; margin: 20px 0;'>", unsafe_allow_html=True)
    st.markdown("<h5 style='color:#8892B0; margin-bottom:10px;'>💼 Active Trade Manager</h5>", unsafe_allow_html=True)
    
    col_t1, col_t2 = st.columns(2)
    with col_t1: track_macro = st.toggle("🟢 Macro", value=True)
    with col_t2: track_swing = st.toggle("🔴 Swing", value=True)
    st.markdown("<hr style='border:1px solid #333; margin: 20px 0;'>", unsafe_allow_html=True)

    if not track_macro and not track_swing: st.info("No active trades selected.")
    
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
                st.markdown(f"<p style='margin-bottom:2px; color:#8892B0;'>Live PnL:</p><h4 style='color:{pnl_color}; margin-top:0;'>{pnl_sign}&#36;{macro_pnl:,.2f} ({pnl_sign}{macro_roi:,.2f}%)</h4>", unsafe_allow_html=True)
                
    if track_swing:
        with st.expander("🔴 SWING: Active Short", expanded=True):
            swing_entry = st.number_input("Entry Price ($)", value=63993.00, step=10.0, key="s_entry")
            swing_collat = st.number_input("Collateral ($)", value=344.00, step=100.0, key="s_col")
            swing_lev = st.slider("Leverage", min_value=1.0, max_value=50.0, value=15.0, step=0.5, key="s_lev")
            if swing_entry > 0:
                swing_roi = ((swing_entry - LIVE_SPOT_PRICE) / swing_entry) * swing_lev * 100
                swing_pnl = (swing_roi / 100) * swing_collat
                pnl_color_s = "#00E676" if swing_pnl >= 0 else "#FF3366"
                pnl_sign_s = "+" if swing_pnl >= 0 else ""
                st.markdown(f"<p style='margin-bottom:2px; color:#8892B0;'>Live PnL:</p><h4 style='color:{pnl_color_s}; margin-top:0;'>{pnl_sign_s}&#36;{swing_pnl:,.2f} ({pnl_sign_s}{swing_roi:,.2f}%)</h4>", unsafe_allow_html=True)

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

# --- DYNAMIC SQUEEZE RISK BANNER ---
hm_data = telemetry.get("orderbook_heatmap", {})
upper_wall = hm_data.get("upper_wall", 65411) if hm_data else 65411
lower_wall = hm_data.get("lower_wall", 61582) if hm_data else 61582
ny_cvd_raw = telemetry.get("session_cvd", {}).get("new_york", {}).get("cvd", "")

if FUNDING_RATE < 0:
    st.warning(f"⚠️ **SYSTEM ALERT: SHORT SQUEEZE RISK** | **Avg Perp Funding: {FUNDING_RATE_PCT:.4f}%** | Negative funding paired with aggressive buying above \\${upper_wall:,.0f}.")
elif FUNDING_RATE_PCT > 0.10: 
    st.warning(f"⚠️ **SYSTEM ALERT: LONG DELEVERAGING RISK** | **Avg Perp Funding: {FUNDING_RATE_PCT:.4f}%** | High perp premium; late longs susceptible to liquidation.")
elif LIVE_SPOT_PRICE < ta.get("vwap", LIVE_SPOT_PRICE) and "+" in ny_cvd_raw:
    st.warning(f"⚠️ **SYSTEM ALERT: ABSORPTION / SQUEEZE RISK** | **Avg Perp Funding: {FUNDING_RATE_PCT:.4f}%** | Buyers absorbed below VWAP (\\${ta.get('vwap', 0):,.2f}). Liquidity wall at \\${upper_wall:,.0f}.")
else:
    st.info(f"ℹ️ **SYSTEM STATUS: NORMAL** | **Avg Perp Funding: {FUNDING_RATE_PCT:.4f}%** | Market structure balanced.")

def render_header(title):
    st.markdown(f"<h4 style='color: #E0E0E0; border-bottom: 1px solid #333; padding-bottom: 10px; margin-top: 40px; margin-bottom: 25px; text-transform: uppercase; letter-spacing: 1px;'>{title}</h4>", unsafe_allow_html=True)

# ==========================================
# SECTION 1: LIVE MARKET OVERVIEW
# ==========================================
render_header("📊 Live Market Overview")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Live Spot", f"${LIVE_SPOT_PRICE:,.2f}")
m2.metric("1H RSI", f"{ta.get('rsi', 58.0)}")
m3.metric("1H VWAP", f"${ta.get('vwap', 63888.0):,.2f}")
m4.metric("Open Interest", OPEN_INTEREST)
m5.metric("Kelly Limit", kelly_display)
m6.metric("Execution Gate", exec_gate)

# ==========================================
# SECTION 2: MULTI-TIMEFRAME MATRIX
# ==========================================
render_header("🧠 Decision Matrix")
col_macro, col_swing, col_micro = st.columns(3)

with col_macro:
    st.markdown("**🌐 1. MACRO HORIZON (2-6 WKS)**")
    if macro_score >= 5.5: st.success("Directive: LONG (🐂 BULL EXPANSION)")
    elif macro_score <= 4.5: st.error("Directive: SHORT (🐻 BEAR CONTRACTION)")
    else: st.warning("Directive: ⏳ NEUTRAL / CHOP")
    
    ma_setups = setups.get("macro", {})
    st.markdown(f"""
    | Parameter | Target / Level |
    | :--- | :--- |
    | **Macro Score** | `{macro_score} / 10` |
    | **Live Spot Exec** | `${LIVE_SPOT_PRICE:,.2f}` |
    | **Conservative T1** | `${ma_setups.get('t1', 70000.00):,.2f}` |
    | **Aggressive T2** | `${ma_setups.get('t2', 74000.00):,.2f}` |
    | **Stop Loss (SL)** | `${ma_setups.get('sl', 58000.00):,.2f}` |
    """)
    macro_rat = insights.get('rationales', {}).get('macro', 'Awaiting live data...')
    st.caption(f"**Rationale:** {macro_rat}")

with col_swing:
    st.markdown("**🔴 2. SWING TACTICAL (1-3 DAYS)**")
    if swing_score >= 52.0: st.success("Directive: TACTICAL LONG RALLY")
    elif swing_score <= 48.0: st.error("Directive: TACTICAL LIQUIDATION WAVE")
    else: st.warning("Directive: ⏳ CHOP / NO TRADE")
    
    sw_setups = setups.get("tactical", {})
    st.markdown(f"""
    | Parameter | Target / Level |
    | :--- | :--- |
    | **Swing Score** | `{swing_score} / 100` |
    | **Live Spot Exec** | `${LIVE_SPOT_PRICE:,.2f}` |
    | **Conservative T1** | `${sw_setups.get('t1', 63500.00):,.2f}` |
    | **Aggressive T2** | `${sw_setups.get('t2', 62800.00):,.2f}` |
    | **Stop Loss (SL)** | `${sw_setups.get('sl', 65411.00):,.2f}` |
    """)
    swing_rat = insights.get('rationales', {}).get('swing', 'Awaiting live data...')
    st.caption(f"**Rationale:** {swing_rat}")

with col_micro:
    st.markdown("**🎯 3. MICRO STF (1-4 HRS)**")
    micro_dir = insights.get('rationales', {}).get('micro_directive', '⏳ NEUTRAL / CHOP')
    
    if "🟢" in micro_dir: st.success(f"Directive: {micro_dir}")
    elif "🔴" in micro_dir: st.error(f"Directive: {micro_dir}")
    else: st.warning(f"Directive: {micro_dir}")
    
    mi_setups = setups.get("micro", {})
    st.markdown(f"""
    | Parameter | Target / Level |
    | :--- | :--- |
    | **Micro Score** | `{micro_score} / 100` |
    | **Live Spot Exec** | `${LIVE_SPOT_PRICE:,.2f}` |
    | **Conservative T1** | `${mi_setups.get('t1', 65000.00):,.2f}` |
    | **Aggressive T2** | `${mi_setups.get('t2', 65411.00):,.2f}` |
    | **Stop Loss (SL)** | `${mi_setups.get('sl', 63600.00):,.2f}` |
    """)
    micro_rat = insights.get('rationales', {}).get('micro', 'Awaiting live data...')
    st.caption(f"**Rationale:** {micro_rat}")

# ==========================================
# SECTION 3: PLAYBOOK MANIFESTO
# ==========================================
if insights or telemetry:
    render_header("📜 Playbook Manifesto")
    
    if "🟢" in exec_gate: playbook_color = st.success
    elif "🔴" in exec_gate: playbook_color = st.error
    elif "⚠️" in exec_gate or "🟡" in exec_gate: playbook_color = st.warning
    else: playbook_color = st.info
    
    vwap = ta.get("vwap", LIVE_SPOT_PRICE)
    
    # Let the backend dictate the dynamic thesis rather than overriding it with hardcoded NY logic
    dynamic_thesis = insights.get('liquidity_thesis', 'Awaiting live session data.')

    safe_guidance = insights.get('institutional_guidance', 'N/A')
    playbook_color(f"**🛡️ INSTITUTIONAL DIRECTIVE:** {safe_guidance}")
    playbook_color(f"**🧠 LIQUIDITY THESIS:** {dynamic_thesis}")

# ==========================================
# SECTION 4: RISK GATEWAY
# ==========================================
render_header("🛡️ Desk-Level Risk Gateway")
rg1, rg2, rg3, rg4 = st.columns(4)

blended_risk = round(((macro_score * 10) + swing_score + micro_score) / 3, 1)

clean_directive = exec_gate.split(" ", 1)[1] if " " in exec_gate else exec_gate
rg1.metric("Risk Base Score", f"{blended_risk} / 100")
rg2.metric("Desk Directive", clean_directive)
rg3.metric("Upper Liq Wall", f"${upper_wall:,.0f}")
rg4.metric("Lower Liq Wall", f"${lower_wall:,.0f}")

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
    
    z_matrix = hm_data.get("z_matrix", []) if hm_data else []
    
    # Safer validity check
    has_valid_data = (
        isinstance(z_matrix, list) 
        and len(z_matrix) > 0 
        and all(isinstance(row, (list, tuple, np.ndarray)) for row in z_matrix)
        and any(any(bool(v) for v in row) for row in z_matrix)
    )

    if hm_data and has_valid_data:
        try:
            z_array = np.asarray(z_matrix, dtype=float)
            
            # Ensure 2D
            if z_array.ndim != 2:
                raise ValueError("z_matrix must be 2-dimensional")
            
            time_steps = hm_data.get("time_steps", [])
            prices = hm_data.get("prices", [])
            
            # Optional but recommended: shape sanity
            if len(prices) != z_array.shape[0] or (time_steps and len(time_steps) != z_array.shape[1]):
                st.warning("Heatmap axis length mismatch – rendering without custom axes.")
                time_steps = None
                prices = None

            # Dynamic contrast
            positive = z_array[z_array > 0]
            if positive.size > 0:
                z_min = float(np.percentile(positive, 5))
                z_max = float(np.percentile(z_array, 95))
            else:
                z_min, z_max = 0.0, 15.0
            
            if z_min == z_max:
                z_max = z_min + 1.0

            fig_heatmap = go.Figure(data=go.Heatmap(
                z=z_array,
                x=time_steps if time_steps else None,
                y=prices if prices else None,
                colorscale='Turbo',
                showscale=True,
                zmin=z_min,
                zmax=z_max,
                colorbar=dict(
                    title=dict(text="Depth", font=dict(color="#8892B0")),
                    thickness=12,
                    len=0.8,
                    tickfont=dict(color="#8892B0")
                )
            ))
            
            fig_heatmap.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=20, b=0),
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(
                    title=dict(text="Spot Price ($)", font=dict(color="#8892B0")),
                    tickformat="$,.0f",
                    showgrid=True,
                    gridcolor='rgba(255,255,255,0.05)',
                    tickfont=dict(color="#8892B0")
                ),
                xaxis=dict(showgrid=False, tickfont=dict(color="#8892B0"))
            )
            
            fig_heatmap.add_hline(
                y=upper_wall, line_dash="dot", line_color="#FF3366", line_width=1,
                annotation_text="Upper Wall", annotation_font=dict(color="#FF3366")
            )
            fig_heatmap.add_hline(
                y=lower_wall, line_dash="dot", line_color="#00E676", line_width=1,
                annotation_text="Lower Support", annotation_font=dict(color="#00E676")
            )
            
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
        except Exception as e:
            st.warning(f"Heatmap render failed: {e}")
            st.info("🗺️ Heatmap buffer initializing... collecting rolling snapshots.")
    else:
        st.info("🗺️ Heatmap buffer initializing... collecting rolling snapshots.")
        
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
        st.markdown("**⚠️ Upcoming Catalysts & Filters**")
        for cat in insights.get("catalysts", []): 
            st.write(f"- {cat}")
            
    with guide_col:
        st.markdown("**🧭 Desk-Level Action Plan**")
        raw_action = insights.get("action_plan", "Execute scaling limits only at structural value nodes.")
        # Strip out any lingering markdown asterisk/formatting corruption from JSON transfer
        action_plan_clean = raw_action.replace("*", "").replace("  ", " ")
        
        if "TRAP" in action_plan_clean: st.error(action_plan_clean)
        elif "favorable" in action_plan_clean: st.success(action_plan_clean)
        else: st.warning(action_plan_clean)
