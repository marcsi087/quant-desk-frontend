import streamlit as st
import requests
import pandas as pd

# 1. Page Configuration for a Wide Desk Layout
st.set_page_config(
    page_title="Quant Desk Command Center", 
    page_icon="⚡", 
    layout="wide"
)

# Custom Styling for Institutional Feel
st.markdown("""
    <style>
        .metric-card {
            background-color: #1e2530;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #2d3748;
        }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Quant Desk Institutional Execution Terminal")
st.markdown("Advanced Algorithmic Tracking • Macro & Swing Multi-Timeframe Matrix")

# Backend API Endpoint
API_URL = "https://quant-desk-backend-rata.onrender.com/api/signal"

# Sidebar Controls
with st.sidebar:
    st.header("Control Panel")
    if st.button("🔄 Refresh Market Data", use_container_width=True):
        st.rerun()
    st.markdown("---")
    st.info("System Status: **ONLINE**\n\nData Feed: **Live (Render API)**")

# Fetch Data from Backend
try:
    response = requests.get(API_URL, timeout=10)
    data = response.json()
    
    if "error" not in data:
        
        # --- TOP LEVEL HEADER METRICS ---
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric(label="BTC Spot Price", value=f"${data['spot_price']:,.2f}")
        with c2:
            st.metric(label="1-Hour RSI", value=f"{data['rsi_1h']}")
        with c3:
            st.metric(label="Open Interest", value=data['oi_trend'])
        with c4:
            st.metric(label="Kelly Risk Size", value=f"{data['kelly_pct']}%")
        with c5:
            st.metric(label="System Timestamp", value=data['timestamp'].split()[1])

        st.markdown("---")

        # --- MULTI-TAB WORKSPACE ---
        tab_exec, tab_matrix, tab_details = st.tabs([
            "🎯 Execution Gate", 
            "📊 Macro & Swing Matrix", 
            "⚙️ Deep Metrics & Diagnostics"
        ])

        # TAB 1: EXECUTION GATE
        with tab_exec:
            st.subheader("Core Execution Manifesto & Gate")
            gate_status = data['execution_gate']
            
            if "EXECUTE" in gate_status:
                st.success(f"### {gate_status}")
            elif "ABORT" in gate_status:
                st.error(f"### {gate_status}")
            else:
                st.warning(f"### {gate_status}")
                
            st.markdown("#### Primary Decision Matrix Summary")
            col_a, col_b = st.columns(2)
            with col_a:
                st.info(f"**Tactical Score (0-100):** {data['tactical_score']}")
            with col_b:
                st.info(f"**Short-Term Flow (STF) Score:** {data['stf_score']}")

        # TAB 2: MACRO & SWING MATRIX
        with tab_matrix:
            st.subheader("Timeframe Separation Analysis")
            st.markdown("Isolating macro structural bias from tactical swing parameters.")
            
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.markdown("### 🌐 Macro Regime")
                st.metric(label="Macro Score Filter", value=data['macro_score'])
                st.write("Evaluates structural trend health, broader liquidity indicators, and multi-week momentum.")
                
            with m_col2:
                st.markdown("### 📈 Tactical Swing Setup")
                st.metric(label="Tactical Engine Rating", value=data['tactical_score'])
                st.write("Evaluates localized volume profile shifts, short-term moving average crosses, and RSI extremes.")

        # TAB 3: DEEP METRICS
        with tab_details:
            st.subheader("Raw Terminal Data Feed")
            st.json(data)

    else:
        st.error(f"Backend API Error: {data['error']}")

except Exception as e:
    st.error(f"Could not connect to backend engine: {e}")
