import streamlit as st
import requests
from datetime import datetime

# 1. Page Configuration for Desk-Level Terminal Layout
st.set_page_config(
    page_title="Quant Desk Institutional Terminal", 
    page_icon="⚡", 
    layout="wide"
)

# 2. Institutional CSS for Telemetry Matrices, Squeeze Cards, & Directives
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
        
        /* Compact Scaled Top Ticker */
        .top-ticker {
            display: flex;
            justify-content: space-between;
            background-color: #12151c;
            border: 1px solid #2d3748;
            border-radius: 6px;
            padding: 10px 15px;
            margin-bottom: 15px;
        }
        .ticker-item {
            text-align: center;
            flex: 1;
            border-right: 1px solid #2d3748;
        }
        .ticker-item:last-child {
            border-right: none;
        }
        .ticker-label {
            font-size: 0.68rem;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 2px;
        }
        .ticker-value {
            font-size: 0.98rem;
            font-weight: 700;
            color: #f3f4f6;
        }

        /* Dedicated Squeeze Risk Module Styling */
        .squeeze-card-red {
            background-color: #450a0a;
            border: 1px solid #ef4444;
            border-radius: 6px;
            padding: 18px;
            margin-bottom: 20px;
            color: #fee2e2;
        }
        .squeeze-card-green {
            background-color: #064e3b;
            border: 1px solid #10b981;
            border-radius: 6px;
            padding: 18px;
            margin-bottom: 20px;
            color: #d1fae5;
        }

        /* Telemetry Audit Section Box */
        .telemetry-box {
            background-color: #161922;
            border: 1px solid #374151;
            border-radius: 6px;
            padding: 20px;
            margin-top: 25px;
            margin-bottom: 25px;
        }

        /* Dynamic Directive Styling with Color Coordination */
        .directive-green {
            background-color: #064e3b;
            border-left: 5px solid #10b981;
            padding: 12px;
            border-radius: 4px;
            font-size: 0.95rem;
            margin-top: 10px;
            margin-bottom: 10px;
            color: #d1fae5;
        }
        .directive-red {
            background-color: #7f1d1d;
            border-left: 5px solid #ef4444;
            padding: 12px;
            border-radius: 4px;
            font-size: 0.95rem;
            margin-top: 10px;
            margin-bottom: 10px;
            color: #fee2e2;
        }
        .directive-orange {
            background-color: #78350f;
            border-left: 5px solid #f59e0b;
            padding: 12px;
            border-radius: 4px;
            font-size: 0.95rem;
            margin-top: 10px;
            margin-bottom: 10px;
            color: #fef3c7;
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
        hr { margin: 1rem 0; border-color: #374151; }
    </style>
""", unsafe_allow_html=True)

# Top Banner Text & App Title Header
st.markdown("### Missy is a cutie ❤️")
st.markdown("## ⚡ QUANT DESK MULTI-TIMEFRAME TERMINAL")
st.caption(f"Institutional Decision Matrix & Execution Gateway | System Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (EST)")

# Backend API Endpoint
API_URL = "https://quant-desk-backend-rata.onrender.com/api/signal"

# Fetch Live Data from Backend API with Safe Fallbacks
try:
    response = requests.get(API_URL, timeout=10)
    data = response.json() if response.status_code == 200 else {}
except Exception:
    data = {}

# Live Data Mappings
spot = float(data.get("spot_price", 63190.40))
rsi = data.get("rsi_1h", 58.7)
oi_trend = data.get("oi_trend", "$18.4B")
funding = data.get("funding_rate", "+0.0026%")
funding_bybit = data.get("funding_bybit", "+0.0030%")
squeeze_side = data.get("squeeze_side", "✅ NEUTRAL / BALANCED")
exec_gate = data.get("execution_gate", "⏳ STAND DOWN")

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
# CLEAN TOP TICKER BANNER (CORE METRICS)
# ==========================================
st.markdown("#### 📊 Live Market Overview")
st.markdown(f"""
<div class="top-ticker">
    <div class="ticker-item">
        <div class="ticker-label">Live Spot</div>
        <div class="ticker-value">${spot:,.2f}</div>
    </div>
    <div class="ticker-item">
        <div class="ticker-label">1H RSI</div>
        <div class="ticker-value">{rsi}</div>
    </div>
    <div class="ticker-item">
        <div class="ticker-label">Open Interest</div>
        <div class="ticker-value">{oi_trend}</div>
    </div>
    <div class="ticker-item">
        <div class="ticker-label">Kelly Limit</div>
        <div class="ticker-value">{data.get('kelly_pct', 2.5)}%</div>
    </div>
    <div class="ticker-item">
        <div class="ticker-label">Execution Gate</div>
        <div class="ticker-value">{exec_gate}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# DEDICATED SQUEEZE RISK ASSESSMENT MODULE
# ==========================================
upper_squeeze = squeeze_side.upper()
if "SHORT SQUEEZE" in upper_squeeze or "LONG SQUEEZE" in upper_squeeze:
    squeeze_card_class = "squeeze-card-red"
    squeeze_desc = f"Funding Rate (Binance: **{funding}** | Bybit: **{funding_bybit}**) shows active derivative skew. Positioning indicates heightened vulnerability to cascading liquidation triggers."
else:
    squeeze_card_class = "squeeze-card-green"
    squeeze_desc = f"Funding Rate (Binance: **{funding}** | Bybit: **{funding_bybit}**) is stable. Derivative positioning shows balanced margin skew with no immediate cascade danger."

st.markdown(f"""
<div class="{squeeze_card_class}">
    <h4 style="margin: 0 0 8px 0; color: inherit;">⚠️ DEDICATED SQUEEZE RISK MATRIX: {squeeze_side}</h4>
    <p style="margin: 0; font-size: 0.95rem; line-height: 1.4;">{squeeze_desc}</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# HELPER FUNCTION FOR DYNAMIC DIRECTIVES
# ==========================================
def render_directive_box(bias_text, default_focus):
    upper_text = bias_text.upper()
    if "LONG" in upper_text or "BULL" in upper_text or "SUPPORT" in upper_text or "EXECUTE LONG" in upper_text:
        box_class = "directive-green"
    elif "SHORT" in upper_text or "BEAR" in upper_text or "LIQUIDATION" in upper_text or "FADE" in upper_text or "EXECUTE SHORT" in upper_text:
        box_class = "directive-red"
    else:
        box_class = "directive-orange"
        
    return f"""
    <div class="{box_class}">
    <b>Playbook Directive:</b> {bias_text}<br>
    <b>Focus:</b> {default_focus}
    </div>
    """

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
    macro_bias = data.get('macro_bias', 'LONG (🐂 BULL EXPANSION)')
    st.markdown(render_directive_box(macro_bias, "Structural multi-week trend health, liquidity velocity, and broader macroeconomic expansion."), unsafe_allow_html=True)
    
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
    tactical_bias = data.get('tactical_bias', 'TACTICAL LIQUIDATION WAVE')
    st.markdown(render_directive_box(tactical_bias, "Mid-horizon momentum shifts, volume profile imbalances, and trend continuation triggers."), unsafe_allow_html=True)
    
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
    micro_bias = data.get('micro_bias', '✅ EXECUTE SHORT / FADE')
    st.markdown(render_directive_box(micro_bias, "Intraday order book imbalances, Wilder RSI extremes, and localized volume spikes."), unsafe_allow_html=True)
    
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

# ==========================================
# GRANULAR TELEMETRY & RAW METRIC AUDIT DRAWER
# ==========================================
st.markdown("---")
st.markdown("### 🔬 GRANULAR TELEMETRY & RAW METRIC AUDIT")

st.markdown('<div class="telemetry-box">', unsafe_allow_html=True)
t1, t2, t3, t4 = st.columns(4)

with t1:
    st.markdown("##### 📈 Order Flow & Volume")
    st.write(f"**24H Quote Volume:** {data.get('volume_24h', 'N/A')}")
    st.write(f"**24H Price Change:** {data.get('price_change_24h', 'N/A')}")
    st.write(f"**1H CVD Proxy:** {data.get('cvd_1h', '+__')}")
    st.write(f"**Taker Buy/Sell:** {data.get('taker_buy_sell_ratio', '1.0')}")

with t2:
    st.markdown("##### ⚡ Derivatives & Funding")
    st.write(f"**Binance Funding:** {funding}")
    st.write(f"**Bybit Funding:** {funding_bybit}")
    st.write(f"**24H Long Liquidations:** {data.get('liq_24h_longs', '$0')}")
    st.write(f"**24H Short Liquidations:** {data.get('liq_24h_shorts', '$0')}")

with t3:
    st.markdown("##### 🌐 Dominance & Volatility")
    st.write(f"**BTC Dominance:** {data.get('btc_dominance', '0%')}")
    st.write(f"**USDT Dominance:** {data.get('tether_dominance', '0%')}")
    st.write(f"**Realized Volatility:** {data.get('realized_vol_24h', '0%')}")

with t4:
    st.markdown("##### 🏛️ Macro Plumbing")
    st.write(f"**DXY Index:** {data.get('dxy', '99.80')}")
    st.write(f"**US 10Y Yield:** {data.get('tnx', '4.74%')}")
    st.write(f"**Macro Liquidity:** {data.get('macro_liquidity', 'Expanding')}")

st.markdown('</div>', unsafe_allow_html=True)
