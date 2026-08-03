import streamlit as st
import requests
import pandas as pd

# 1. Page Configuration for Institutional Terminal Layout
st.set_page_config(
    page_title="Quant Desk Institutional Terminal", 
    page_icon="⚡", 
    layout="wide"
)

# Custom Styling for Desk-Level Aesthetic
st.markdown("""
    <style>
        .main-header {
            font-size: 2rem;
            font-weight: 700;
            color: #f8fafc;
        }
        .sub-text {
            color: #94a3b8;
            font-size: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">⚡ QUANT DESK COMMAND CENTER</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-text">Institutional Multi-Timeframe Alpha, Macro Regime Filtering, & Execution Gateway</p>', unsafe_allow_html=True)

# Backend API Endpoint
API_URL = "https://quant-desk-backend-rata.onrender.com/api/signal"

# Sidebar Control Center
with st.sidebar:
    st.header("Terminal Controls")
    if st.button("🔄 Force Refresh Feed", use_container_width=True):
        st.rerun()
    st.markdown("---")
    st.markdown("### System Diagnostics")
    st.info("Backend: **Render (Live)**\n\nExecution Engine: **Operational**")
    st.markdown("---")
    st.markdown("### Risk Parameters")
    st.slider("Max Capital Allocation (%)", 1, 20, 5, key="risk_cap")

# Fetch Live Data from Backend API
try:
    response = requests.get(API_URL, timeout=10)
    data = response.json()
    
    if "error" not in data:
        
        # --- TOP ROW: PRIMARY MACRO & SPOT METRICS ---
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric(label="BTC Spot Price", value=f"${data['spot_price']:,.2f}")
        with c2:
            st.metric(label="1-Hour RSI", value=f"{data['rsi_1h']}")
        with c3:
            st.metric(label="Open Interest Trend", value=data['oi_trend'])
        with c4:
            st.metric(label="Kelly Risk Size", value=f"{data['kelly_pct']}%")
        with c5:
            st.metric(label="Sync Timestamp", value=data['timestamp'].split()[1])

        st.markdown("---")

        # --- MULTI-TAB DESK WORKSPACE ---
        tab_exec, tab_matrix, tab_macro, tab_raw = st.tabs([
            "🎯 Execution Matrix", 
            "📊 Swing Setup & Volume", 
            "🌐 Macro Regime Filter",
            "⚙️ Raw JSON Payload"
        ])

        # TAB 1: EXECUTION GATEWAY
        with tab_exec:
            st.subheader("Core Execution Manifesto & Gate")
            gate_status = data['execution_gate']
            
            if "EXECUTE" in gate_status:
                st.success(f"### 🚀 {gate_status}")
            elif "ABORT" in gate_status:
                st.error(f"### 🛑 {gate_status}")
            else:
                st.warning(f"### ⏳ {gate_status}")
                
            col_ex1, col_ex2, col_ex3 = st.columns(3)
            with col_ex1:
                st.metric("Tactical Engine Score", f"{data['tactical_score']} / 100")
            with col_ex2:
                st.metric("Short-Term Flow (STF)", f"{data['stf_score']}")
            with col_ex3:
                st.metric("Recommended Allocation", f"{data['kelly_pct']}%")
                
            st.markdown("#### Actionable Directives")
            st.markdown("""
            * **Gate Validation:** Enforces strict quantitative thresholds before deployment.
            * **Risk Rule:** Position sizing is dynamically adjusted based on volatility metrics and active open interest trends.
            """)

        # TAB 2: SWING SETUP & VOLUME
        with tab_matrix:
            st.subheader("Localized Technical & Volume Structure")
            
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                st.markdown("### Tactical Swing Parameters")
                st.write(f"**Current RSI State:** {data['rsi_1h']}")
                st.write(f"**Short-Term Momentum Score:** {data['tactical_score']}")
                st.info("Designed for multi-day swing horizons separate from macro trend filters.")
                
            with s_col2:
                st.markdown("### Volume & Open Interest Dynamics")
                st.write(f"**Open Interest (OI) Trend:** {data['oi_trend']}")
                st.info("Tracking institutional participation changes and liquidity inflows/outflows in real time.")

        # TAB 3: MACRO REGIME FILTER
        with tab_macro:
            st.subheader("Macrostructural Bias Analysis")
            
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.metric(label="Macro Score Rating", value=data['macro_score'])
                st.write("Evaluates structural market health, broader liquidity indicators, and trend direction.")
            with m_col2:
                st.markdown("### Portfolio Guardrails")
                st.success("Macro filter successfully decoupled from tactical execution triggers to prevent timeframe contamination.")

        # TAB 4: RAW PAYLOAD
        with tab_raw:
            st.subheader("Inspect Live API Response Data")
            st.json(data)

    else:
        st.error(f"Backend API Error: {data['error']}")

except Exception as e:
    st.error(f"Could not connect to the backend server engine. Error: {e}")
