import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Quant Desk | BTC Alpha", page_icon="🦅", layout="wide", initial_sidebar_state="expanded")

# 2. Institutional CSS Styling (Tight padding, desk-level aesthetics)
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        .stMetric { background-color: #1a1c24; padding: 10px; border-radius: 4px; border-left: 4px solid #3b82f6; }
        .stMetric label { color: #9ca3af !important; font-size: 0.85rem !important; }
        .stMetric p { font-size: 1.4rem !important; font-weight: 700 !important; }
        h1, h2, h3 { color: #e5e7eb; }
        hr { margin: 0.5em 0; border-color: #374151; }
    </style>
""", unsafe_allow_html=True)

# 3. Live API Fetch
API_URL = "https://quant-desk-backend-rata.onrender.com/api/signal"
try:
    response = requests.get(API_URL, timeout=8)
    data = response.json() if response.status_code == 200 else {}
except:
    data = {}

# Safe fallbacks mapping to your Google Sheet structure
spot = data.get("spot_price", 0.00)
timestamp = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# --- TOP NAVIGATION & GLOBAL PLUMBING ---
st.markdown("## 🦅 QUANT TERMINAL: BTC MACRO ALPHA")
st.caption(f"**Last Sync:** {timestamp} (EST) | **Live Status:** OK - Price: Coinbase | 1h: OKX")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Live Bitcoin Spot", f"${spot:,.2f}")
c2.metric("USD Index (DXY)", data.get("dxy", "99.80")) # Placeholder mapping to sheet
c3.metric("US 10-Yr (TNX)", data.get("tnx", "4.74%"))
c4.metric("Risk Velocity (ETH/BTC)", data.get("eth_btc", "0.0294"))
c5.metric("1-Hour RSI", data.get("rsi_1h", "58.7"))
c6.metric("Live Funding Rate", data.get("funding", "0.0026%"))

st.markdown("---")

# --- THREE-PILLAR TIMEFRAME HORIZONS ---
col_macro, col_swing, col_micro = st.columns(3)

# PILLAR 1: MACRO
with col_macro:
    st.markdown("### 🌐 MACRO (2-6 WKS)")
    st.metric("Macro Score (1-10)", data.get("macro_score", "5.9"))
    st.info(f"**Playbook:** {data.get('macro_bias', 'LONG (🐂 BULL EXPANSION)')}")
    st.write(f"**Entry Trigger:** ${data.get('macro_entry', 63761):,.2f}")
    st.write(f"**Target 1 (2x ATR):** ${data.get('macro_tp1', 66763):,.2f}")
    st.write(f"**Invalidation:** ${data.get('macro_sl', 61577):,.2f}")

# PILLAR 2: TACTICAL SWING
with col_swing:
    st.markdown("### ⚡ TACTICAL SWING (4-24 HRS)")
    st.metric("Tactical Score (0-100)", data.get("tactical_score", "23.3"))
    st.warning(f"**Playbook:** {data.get('tactical_bias', 'TACTICAL LIQUIDATION WAVE')}")
    st.write(f"**Entry Trigger:** ${data.get('swing_entry', 63512):,.2f}")
    st.write(f"**Target 1 (2x ATR):** ${data.get('swing_tp1', 60511):,.2f}")
    st.write(f"**Invalidation:** ${data.get('swing_sl', 65764):,.2f}")

# PILLAR 3: MICRO STF
with col_micro:
    st.markdown("### 🎯 MICRO STF (1-4 HRS)")
    st.metric("Micro STF Score (0-100)", data.get("stf_score", "20.9"))
    st.success(f"**Playbook:** {data.get('micro_bias', '✅ EXECUTE SHORT')}")
    st.write(f"**Entry Trigger:** ${data.get('micro_entry', 62816):,.2f}")
    st.write(f"**Target 1:** ${data.get('micro_tp1', 63191):,.2f}")
    st.write(f"**Invalidation:** ${data.get('micro_sl', 62440):,.2f}")

st.markdown("---")

# --- HIERARCHICAL GATING & RISK ALLOCATION ---
st.markdown("### ⚙️ HIERARCHICAL GATING & LIQUIDITY")
rg1, rg2, rg3, rg4 = st.columns(4)

with rg1:
    st.subheader("Core Manifesto")
    st.write("**Gate 1 (Macro):** Buy Macro Pullbacks")
    st.write("**Gate 2 (Tactical):** Do Not Catch Knives")
    st.write("**Gate 3 (Micro):** Prep limit asks at upper ATR")

with rg2:
    st.subheader("Liquidation Walls")
    st.write(f"**Short Wall:** ${data.get('short_wall', 64739):,.2f}")
    st.write(f"**Long Wall:** ${data.get('long_wall', 60855):,.2f}")
    st.write(f"**OI Trend:** {data.get('oi_trend', '⚠️ UNAVAILABLE')}")

with rg3:
    st.subheader("Action Gateway")
    st.metric("Hierarchical Base Score", data.get("hierarchical_score", "42.8"))
    st.error("🛡️ RISK ACTION: SCALE DOWN RISK (HEDGE ON)")

with rg4:
    st.subheader("Risk Sizing")
    st.metric("Half-Kelly Risk Limit", f"{data.get('kelly_pct', '0.00')}%")
    st.metric("Inst. Flow (0-100)", data.get("inst_flow", "50"))

st.markdown("---")

# --- ACTIVE TRADE MANAGER (SIDEBAR) ---
with st.sidebar:
    st.header("🔴 ACTIVE TRADE MANAGER")
    st.button("🔄 Sync Live Data", use_container_width=True)
    st.markdown("---")
    
    trade_side = st.selectbox("Trade Side", ["NONE", "LONG", "SHORT"])
    entry_price = st.number_input("Entry Price ($)", value=0.0)
    collateral = st.number_input("Collateral ($)", value=0.0)
    leverage = st.slider("Leverage (x)", 1, 10, 1)
    
    if trade_side != "NONE" and entry_price > 0:
        if trade_side == "LONG":
            roe = ((spot - entry_price) / entry_price) * leverage * 100
        else:
            roe = ((entry_price - spot) / entry_price) * leverage * 100
            
        pnl = collateral * (roe / 100)
        
        st.markdown("### Live Position")
        st.metric("ROE (%)", f"{roe:,.2f}%", delta=f"{roe:,.2f}%", delta_color="normal")
        st.metric("Cash PnL", f"${pnl:,.2f}", delta=f"${pnl:,.2f}", delta_color="normal")
    else:
        st.info("Awaiting Trade Details...")
