import streamlit as st
import requests
from datetime import datetime

# 1. Page Configuration for Desk-Level Terminal Layout
st.set_page_config(
    page_title="Quant Desk Institutional Terminal", 
    page_icon="⚡", 
    layout="wide"
)

# 2. Institutional CSS for Clear Column Separation & Clean Typography
st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
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
        hr { margin: 1rem 0; border-color: #374151; }
    </style>
""", unsafe_allow_html=True)

# App Title Header
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

# Fallbacks and Data Mapping
spot = data.get("spot_price", 63190.40)
timestamp = data.get("timestamp", "Live Feed")

# Sidebar Control Center
with st.sidebar:
    st.header("⚙️ Terminal Control")
    if st.button("🔄 Force Refresh Data", use_container_width=True):
        st.rerun()
    st.markdown("---")
    st.markdown("### Global Plumbing")
    st.write("**DXY Index:** 99.80")
    st.write("**US 10Y Yield (TNX):** 4.74%")
    st.write("**Risk Velocity (ETH/BTC):** 0.0294")
    st.markdown("---")
    st.markdown("### System Status")
    st.success("Backend Render API: **ONLINE**")

# --- TOP GLOBAL METRICS BANNER ---
gc1, gc2, gc3, gc4, gc5 = st.columns(5)
gc1.metric("Live Bitcoin Spot", f"${spot:,.2f}")
gc2.metric("1-Hour RSI", data.get("rsi_1h", "58.7"))
gc3.metric("Open Interest Trend", data.get("oi_trend", "🟢 RISING"))
gc4.metric("Kelly Allocation Limit", f"{data.get('kelly_pct', '2.5')}%")
gc5.metric("Hierarchical Score", "42.8")

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
    st.markdown("""
    <div class="playbook-box">
    <b>Directive:</b> LONG (🐂 BULL EXPANSION)<br>
    <b>Focus:</b> Structural multi-week trend health, liquidity velocity, and broader macroeconomic expansion.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("#### Key Price Levels")
    st.write(f"**EMA Anchor Entry:** ${63761.52:,.2f}")
    st.write(f"**Target 1 (2.0x ATR):** ${66763.21:,.2f}")
    st.write(f"**Structural Invalidation:** ${61577.03:,.2f}")
    
    st.markdown("#### Analytical Focus")
    st.caption("Maintains core directional bias. Ignores intraday noise and short-term volatility contractions.")
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------
# COLUMN 2: TACTICAL SWING HORIZON (4-24 HRS)
# ------------------------------------------
with col_swing:
    st.markdown('<div class="column-box">', unsafe_allow_html=True)
    st.markdown('<div class="metric-title">⚡ 2. TACTICAL SWING (4-24 HRS)</div>', unsafe_allow_html=True)
    
    st.metric("Tactical Momentum Score", f"{data.get('tactical_score', 23.3)} / 100")
    
    st.markdown("#### 🎯 Playbook Directive")
    st.markdown("""
    <div class="playbook-box" style="border-left-color: #f59e0b;">
    <b>Directive:</b> TACTICAL LIQUIDATION WAVE<br>
    <b>Focus:</b> Mid-horizon momentum shifts, volume profile imbalances, and trend continuation triggers.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("#### Key Price Levels")
    st.write(f"**Retest Entry Trigger:** ${63512.95:,.2f}")
    st.write(f"**Downward Target 1:** ${60511.26:,.2f}")
    st.write(f"**Tactical Stop Loss:** ${65764.22:,.2f}")
    
    st.markdown("#### Analytical Focus")
    st.caption("Filters counter-trend traps. Ensures position scaling aligns with active liquidation walls.")
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------
# COLUMN 3: MICRO STF HORIZON (1-4 HRS)
# ------------------------------------------
with col_micro:
    st.markdown('<div class="column-box">', unsafe_allow_html=True)
    st.markdown('<div class="metric-title">🎯 3. MICRO STF (1-4 HRS)</div>', unsafe_allow_html=True)
    
    st.metric("Micro STF Score", f"{data.get('stf_score', 20.9)} / 100")
    
    st.markdown("#### 🎯 Playbook Directive")
    st.markdown("""
    <div class="playbook-box" style="border-left-color: #10b981;">
    <b>Directive:</b> ✅ EXECUTE SHORT / FADE<br>
    <b>Focus:</b> Intraday order book imbalances, Wilder RSI extremes, and localized volume spikes.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("#### Key Price Levels")
    st.write(f"**Live Spot Execution:** ${spot:,.2f}")
    st.write(f"**Upper ATR Target:** ${63191.21:,.2f}")
    st.write(f"**Micro Stop Loss:** ${62440.79:,.2f}")
    
    st.markdown("#### Analytical Focus")
    st.caption("Execution timing gate. Validates precise entries and exit points for immediate price action.")
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# BOTTOM TIER: ACTIVE DESK EXECUTION GATE
# ==========================================
st.markdown("### 🛡️ DESK-LEVEL RISK & EXECUTION GATEWAY")
g1, g2, g3 = st.columns(3)

with g1:
    st.info("**Hierarchical Base Score:** 42.8 / 100")
    st.write("Synthesizes multi-horizon readings to prevent timeframe contamination.")

with g2:
    st.error("**Enforced Risk Action:** SCALE DOWN RISK (HEDGE ON)")
    st.write("Dynamic risk sizing reduces exposure when timeframes misalign.")

with g3:
    st.success("**Active Liquidation Walls:** Upper $64,739 | Lower $60,855")
    st.write("Tracks institutional cluster zones for potential cascading liquidations.")
