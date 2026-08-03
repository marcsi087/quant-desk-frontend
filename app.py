import streamlit as st
import requests

# 1. Page Configuration
st.set_page_config(
    page_title="Quant Desk Dashboard", 
    page_icon="📈", 
    layout="wide"
)

st.title("⚡ Quant Desk Live Execution Dashboard")
st.markdown("Real-time Bitcoin algorithmic tracking, macro filters, and execution gates.")

# 2. Link to your live FastAPI backend on Render
API_URL = "https://quant-desk-backend-rata.onrender.com/api/signal"

# 3. Add a manual refresh button
if st.button("🔄 Refresh Live Data"):
    st.rerun()

try:
    # Fetch data from your live backend API
    response = requests.get(API_URL, timeout=10)
    data = response.json()
    
    if "error" not in data:
        # Layout Row 1: Key Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(label="Bitcoin Spot Price", value=f"${data['spot_price']:,.2f}")
        with col2:
            st.metric(label="1-Hour RSI", value=f"{data['rsi_1h']}")
        with col3:
            st.metric(label="Open Interest Trend", value=data['oi_trend'])
        with col4:
            st.metric(label="Kelly Risk Size", value=f"{data['kelly_pct']}%")

        st.markdown("---")

        # Layout Row 2: Execution Status and Sub-Scores
        col_gate, col_scores = st.columns([2, 1])
        
        with col_gate:
            st.subheader("Current Execution Status")
            gate_status = data['execution_gate']
            if "EXECUTE" in gate_status:
                st.success(gate_status)
            elif "ABORT" in gate_status:
                st.error(gate_status)
            else:
                st.warning(gate_status)
                
        with col_scores:
            st.subheader("Sub-Scores")
            st.write(f"**Macro Score:** {data['macro_score']}")
            st.write(f"**Tactical Score:** {data['tactical_score']}")
            st.write(f"**STF Score:** {data['stf_score']}")

        st.markdown("---")
        st.caption(f"Backend Timestamp: {data['timestamp']} (Eastern)")

    else:
        st.error(f"Backend API Error: {data['error']}")

except Exception as e:
    st.error(f"Could not connect to the backend server. Error: {e}")
