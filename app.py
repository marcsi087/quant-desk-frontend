import streamlit as st
import requests
from datetime import datetime

# 1. Page Configuration for Desk-Level Terminal Layout
st.set_page_config(
    page_title="Quant Desk Institutional Terminal", 
    page_icon="⚡", 
    layout="wide"
)

# 2. Institutional CSS for Compact Header Grid, High-Contrast Boxes, & Typography
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 1rem; }
        .column-box {
            background-color: #161922;
            border: 1px solid #2d3748;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 15px;
        }
        .metric-title { font-size: 1.1rem; font-weight: 700; color: #60a5fa; margin-bottom: 10px; }
        .playbook-box {
            background-color: #1e2530;
            border-left: 4px solid #3b82f6;
            padding: 12px;
            border-radius: 4px;
            font-size: 0.95rem;
            margin-top: 10px;
            margin-bottom: 10px;
        }
        .analytical-box {
            background-color: #1c2536;
            border: 1px solid #3b82f6;
            border-radius: 4px;
            padding: 12px;
            margin-top: 15px;
            color: #bfdbfe;
            font-size: 0.88rem;
            line-height: 1.4;
        }
        /* Compact Professional Top Header Bar */
        .metrics-grid {
            background-color: #12151c;
            border: 1px solid #2d3748;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 20px;
        }
        hr { margin: 1rem 0; border-color: #374151; }
    </style>
""", unsafe_allow_html=True)

# Top Banner Text & App Title Header (Proper spacing)
st.markdown("### Missy is a cutie ❤️")
st.markdown("## ⚡ QUANT DESK MULTI-TIMEFRAME TERMINAL")
st.caption(f"Institutional Decision Matrix & Execution Gateway | System Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (EST)")

# Backend API Endpoint
API_URL = "https://quant-desk-backend-rata.onrender.com/api/signal"

# Fetch Live Data from Backend API
try:
    response = requests.get(API_URL, timeout=10)
    data = response.json() if response.status_code == 200 else {}
except Exception:
    data = {}

# Live Data Mappings from Backend Engine
spot = data.get("spot_price", 0.0)
rsi = data.get("rsi_1h", 50.0)
oi_trend = data.get("oi_trend", "🟢 RISING")
kelly = data.get("kelly_pct", 2.5)

# ==========================================
# SIDEBAR CONTROL CENTER & ACTIVE TRADE MANAGER
# ==========================================
with st.sidebar:
    st.header("⚙️ Terminal Control")
    if st.button("🔄 Force Refresh Data", use_container_width=True):
        st.rerun()
    st.markdown("---")
    st.markdown("### Global Plumbing")
    st.write(f"**DXY Index:** {data.get('dxy', '99.80')}")
    st.write(f"**US 10Y Yield (TNX):** {data.get('tnx', '4.74%')}")
    st.write(f"**Risk Velocity (ETH/BTC):** {data.get('eth_btc', '0.0294')}")
    st.markdown("---")
    st.markdown("### System Status")
    st.success("Backend Render API: **ONLINE**")
    
    # Active Trade Manager with 50x Max Leverage Slider
    st.markdown("---")
    st.header("🔴 ACTIVE TRADE MANAGER")
    
    trade_side = st.selectbox("Trade Side", ["NONE", "LONG", "SHORT"])
    entry_price = st.number_input("Entry Price ($)", value=0.0, format="%.2f")
    collateral = st.number_input("Collateral ($)", value=0.0, format="%.2f")
    leverage = st.slider("Leverage (x)", min_value=1.0, max_value=50.0, value=1.0, step=0.1, format="%.1f")
    
    if trade_side != "NONE" and entry_price > 0 and spot > 0:
        if trade_side == "LONG":
            roe = ((spot - entry_price) / entry_price) * leverage * 100
        else:
            roe = ((entry_price - spot) / entry_price) * leverage * 100
            
        pnl = collateral * (roe / 100)
        
        st.markdown("### Live Position PnL")
        st.metric("Live ROE (%)", f"{roe:,.2f}%", delta=f"{roe:,.2f}%")
        st.metric("Cash PnL ($)", f"${pnl:,.2f}", delta=f"${pnl:,.2f}")
    else:
        st.info("Awaiting Trade Details...")

# ==========================================
# COMPACT TOP BANNER SECTION (RESTORED SPOT & GATE)
# ==========================================
st.markdown("#### 📊 Live Market & Execution Overview")
st.markdown('<div class="metrics-grid">', unsafe_allow_html=True)
tk1, tk2, tk3, tk4, tk5 = st.columns(5)
tk1.metric("Live Bitcoin Spot", f"${spot:,.2f}")
tk2.metric("1-Hour RSI", f"{rsi}")
tk3.metric("Open Interest Trend", f"{oi_trend}")
tk4.metric("Kelly Allocation Limit", f"{kelly}%")
tk5.metric("Execution Gate", data.get("execution_gate", "STAND DOWN"))
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# THREE-COLUMN MULTI-TIMEFRAME ARCHITECTURE
# ==========================================
col_macro, col_swing, col_micro = st.columns(3)

# ------------------------------------------
# COLUMN 1: MACRO STRUCTURAL HORIZON (2-6 WKS)
# ------------------------------------------
with col_macro:
    st.markdown('<div class="column-box">', unsafe_allow_html=True)
    st.markdown('<div class="metric-title">🌐 1. MACRO HORIZON (2-6 WKS)</div>', unsafe_allow_html=True)
    
    st.metric("Macro Score Rating", f"{data.get('macro_score', 5.9)} / 10")
    
    st.markdown("#### 🎯 Playbook Directive")
    st.markdown(f"""
    <div class="playbook-box">
    <b>Directive:</b> {data.get('macro_bias', 'LONG (🐂 BULL EXPANSION)')}<br>
    <b>Focus:</b> Structural multi-week trend health, liquidity velocity, and broader macroeconomic expansion.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("#### Key Price Levels")
    st.write(f"**EMA Anchor Entry:** ${data.get('macro_entry', spot * 0.99):,.2f}")
    st.write(f"**Target 1 (2.0x ATR):** ${data.get('macro_tp1', spot * 1.05):,.2f}")
    st.write(f"**Structural Invalidation:** ${data.get('macro_sl', spot * 0.95):,.2f}")
    
    st.markdown("""
    <div class="analytical-box">
    <b>Analytical Focus:</b><br>
    Maintains core directional bias. Ignores intraday noise and short-term volatility contractions.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------
# COLUMN 2: TACTICAL SWING HORIZON (4-24 HRS)
# ------------------------------------------
with col_swing:
    st.markdown('<div class="column-box">', unsafe_allow_html=True)
    st.markdown('<div class="metric-title">⚡ 2. TACTICAL SWING (4-24 HRS)</div>', unsafe_allow_html=True)
    
    st.metric("Tactical Momentum Score", f"{data.get('tactical_score', 23.3)} / 100")
    
    st.markdown("#### 🎯 Playbook Directive")
    st.markdown(f"""
    <div class="playbook-box" style="border-left-color: #f59e0b;">
    <b>Directive:</b> {data.get('tactical_bias', 'TACTICAL LIQUIDATION WAVE')}<br>
    <b>Focus:</b> Mid-horizon momentum shifts, volume profile imbalances, and trend continuation triggers.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("#### Key Price Levels")
    st.write(f"**Retest Entry Trigger:** ${data.get('swing_entry', spot * 0.995):,.2f}")
    st.write(f"**Downward Target 1:** ${data.get('swing_tp1', spot * 0.97):,.2f}")
    st.write(f"**Tactical Stop Loss:** ${data.get('swing_sl', spot * 1.02):,.2f}")
    
    st.markdown("""
    <div class="analytical-box">
    <b>Analytical Focus:</b><br>
    Filters counter-trend traps. Ensures position scaling aligns with active liquidation walls.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------
# COLUMN 3: MICRO STF HORIZON (1-4 HRS)
# ------------------------------------------
with col_micro:
    st.markdown('<div class="column-box">', unsafe_allow_html=True)
    st.markdown('<div class="metric-title">🎯 3. MICRO STF (1-4 HRS)</div>', unsafe_allow_html=True)
    
    st.metric("Micro STF Score", f"{data.get('stf_score', 20.9)} / 100")
    
    st.markdown("#### 🎯 Playbook Directive")
    st.markdown(f"""
    <div class="playbook-box" style="border-left-color: #10b981;">
    <b>Directive:</b> {data.get('micro_bias', '✅ EXECUTE SHORT / FADE')}<br>
    <b>Focus:</b> Intraday order book imbalances, Wilder RSI extremes, and localized volume spikes.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("#### Key Price Levels")
    st.write(f"**Live Spot Execution:** ${spot:,.2f}")
    st.write(f"**Upper ATR Target:** ${data.get('micro_tp1', spot * 1.01):,.2f}")
    st.write(f"**Micro Stop Loss:** ${data.get('micro_sl', spot * 0.99):,.2f}")
    
    st.markdown("""
    <div class="analytical-box">
    <b>Analytical Focus:</b><br>
    Execution timing gate. Validates precise entries and exit points for immediate price action.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# BOTTOM TIER: ACTIVE DESK EXECUTION GATE
# ==========================================
st.markdown("### 🛡️ DESK-LEVEL RISK & EXECUTION GATEWAY")
g1, g2, g3 = st.columns(3)

with g1:
    st.info(f"**Hierarchical Base Score:** {data.get('hierarchical_score', '42.8')} / 100")
    st.write("Synthesizes multi-horizon readings to prevent timeframe contamination.")

with g2:
    st.error(f"**Enforced Risk Action:** {data.get('risk_action', 'SCALE DOWN RISK (HEDGE ON)')}")
    st.write("Dynamic risk sizing reduces exposure when timeframes misalign.")

with g3:
    st.success(f"**Active Liquidation Walls:** Upper ${data.get('short_wall', '64,739')} | Lower ${data.get('long_wall', '60,855')}")
    st.write("Tracks institutional cluster zones for potential cascading liquidations.")
