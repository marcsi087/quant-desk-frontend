import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION ---
API_URL = "https://quant-desk-backend-rata.onrender.com/api/v1"
HEATMAP_HISTORY_LEN_FALLBACK = 30  # mirrors backend's HEATMAP_HISTORY_LEN; used only if a payload predates this field
st.set_page_config(page_title="Quant Desk Multi-Timeframe Terminal", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS ---
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.25rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.90rem !important; white-space: normal !important; color: #8892B0 !important; }
[data-testid="stMetricDelta"] { font-size: 0.85rem !important; }
table { width: 100%; border-collapse: collapse; }
th { color: #8892B0; font-size: 0.85rem; text-transform: uppercase; border-bottom: 1px solid #444 !important; }
td { font-size: 0.95rem; border-bottom: 1px solid #222 !important; padding: 6px 0px !important; }
.stale-badge { background-color: #3D2B00; color: #FFB020; padding: 4px 10px; border-radius: 4px; font-size: 0.8rem; }
.live-badge { background-color: #0B3D24; color: #00E676; padding: 4px 10px; border-radius: 4px; font-size: 0.8rem; }
.block-container { max-width: 1500px; margin: 0 auto; padding-left: 2.5rem; padding-right: 2.5rem; }
.bias-badge { display: inline-block; padding: 3px 12px; border-radius: 4px; font-size: 0.85rem; font-weight: 600; margin: 2px 0 10px 0; }
.bias-bullish  { background-color: #0B3D24; color: #00E676; }
.bias-bearish  { background-color: #3D0B18; color: #FF3366; }
.bias-neutral  { background-color: #3D2B00; color: #FFB020; }
.bias-conflict { background-color: #241640; color: #B794F6; }
.status-card { background-color: #10141F; border-left: 4px solid #4FC3F7; border-radius: 4px; padding: 10px 16px; margin-bottom: 10px; font-size: 0.92rem; line-height: 1.5; }
.status-card.bullish  { border-left-color: #00E676; }
.status-card.bearish  { border-left-color: #FF3366; }
.status-card.neutral  { border-left-color: #FFB020; }
.status-card.conflict { border-left-color: #B794F6; }
.status-card.info     { border-left-color: #4FC3F7; }
</style>
""", unsafe_allow_html=True)

# Two-tier visual language for bias/signal content (kept separate from native
# st.success/error/warning/info, which stay reserved for real system states
# like "backend unreachable" so those don't get visually diluted):
#   - bias_badge: small inline chip, for per-item bias tags (Decision Matrix)
#   - status_card: dark card with a colored left border, for section-level
#     summaries (squeeze risk, overall bias, guidance) -- restrained compared
#     to a full bright alert fill, but still color-coded for a quick scan.
def bias_badge(text, kind):
    st.markdown(f'<span class="bias-badge bias-{kind}">{text}</span>', unsafe_allow_html=True)

def status_card(html, kind="info"):
    st.markdown(f'<div class="status-card {kind}">{html}</div>', unsafe_allow_html=True)

st_autorefresh(interval=60000, key="data_refresh")

# --- DATA FETCHING ---
@st.cache_data(ttl=30)
def get_telemetry():
    try:
        response = requests.get(f"{API_URL}/telemetry", timeout=10)
        if response.status_code == 200:
            return response.json()
        st.session_state["_fetch_error"] = f"Backend returned status {response.status_code}"
    except Exception as e:
        st.session_state["_fetch_error"] = f"Backend unreachable: {e}"
    return {}

telemetry = get_telemetry()

@st.cache_data(ttl=300)
def get_track_record():
    try:
        r = requests.get(f"{API_URL}/track-record", timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}

# PULL LIVE TELEMETRY VARIABLES
LIVE_SPOT_PRICE = telemetry.get("spot_price", 64347.99)
FUNDING_RATE = telemetry.get("funding_rate", 0.00066)
FUNDING_RATE_PCT = FUNDING_RATE * 100
OPEN_INTEREST = telemetry.get("open_interest", "$7.02B")
ta = telemetry.get("ta", {"rsi": 50.0, "vwap": LIVE_SPOT_PRICE, "atr_pct": 0.01})
scores = telemetry.get("scores", {"macro": 5.0, "swing": 50.0, "micro": 50.0})
macro_score = scores.get("macro", 5.0)
swing_score = scores.get("swing", 50.0)
micro_score = scores.get("micro", 50.0)
setups = telemetry.get("trade_setups", {})
data_quality = telemetry.get("data_quality", {})

plumbing = telemetry.get("macro_plumbing", {
    "dxy": {"value": "104.20", "delta": "+0.00"}, "us10y": {"value": "4.250%", "delta": "+0.000"},
    "vix": {"value": "14.50", "delta": "+0.00"}, "sp500": {"value": "5,200", "delta": "+0"}
})
insights = telemetry.get("insights", {})

# --- BIAS + CONFIDENCE (educational framing: state the bias and how far it
# is from neutral, never an instruction to act) ---
def confidence_label(score, bull_thresh, bear_thresh, scale_max):
    if score >= bull_thresh:
        room = scale_max - bull_thresh
        progress = (score - bull_thresh) / room if room > 0 else 0.0
    elif score <= bear_thresh:
        room = bear_thresh
        progress = (bear_thresh - score) / room if room > 0 else 0.0
    else:
        return "Low"
    if progress < 0.33:
        return "Low"
    elif progress < 0.66:
        return "Moderate"
    return "High"

macro_conf = confidence_label(macro_score, 5.5, 4.5, 10.0)
swing_conf = confidence_label(swing_score, 52.0, 48.0, 100.0)
micro_conf = confidence_label(micro_score, 55.0, 45.0, 100.0)

macro_bull, macro_bear = macro_score >= 5.5, macro_score <= 4.5
if macro_bull and micro_score <= 45.0:
    exec_gate = "⚠️ Conflicting Bias — Macro Bullish, Micro Bearish (Diverging Timeframes)"
elif macro_bear and micro_score >= 55.0:
    exec_gate = "⚠️ Conflicting Bias — Macro Bearish, Micro Bullish (Diverging Timeframes)"
elif macro_bull and swing_score >= 52.0 and micro_score >= 50.0:
    exec_gate = f"🟢 Bullish Bias — Aligned Across Timeframes ({macro_conf} Confidence)"
elif macro_bear and swing_score <= 48.0 and micro_score <= 48.0:
    exec_gate = f"🔴 Bearish Bias — Aligned Across Timeframes ({macro_conf} Confidence)"
elif macro_bull and swing_score <= 48.0 and micro_score <= 48.0:
    exec_gate = "🟡 Bullish Macro, Bearish Near-Term (Possible Pullback)"
elif macro_bear and swing_score >= 52.0 and micro_score >= 50.0:
    exec_gate = "🟡 Bearish Macro, Bullish Near-Term (Possible Bounce)"
else:
    exec_gate = "⏳ No Clear Bias — Mixed Signals (Low Confidence)"

# --- SIZING GUIDE (now grounded in this instance's own empirical Track
# Record instead of a formula that treated an unrelated technical score as a
# win probability). See compute_sizing_guide() in the backend: it uses the
# ACTUAL win rate and average win/loss size observed historically for Swing
# readings like the current one, and openly says "not enough data yet"
# rather than showing a number nobody can act on. ---
sizing = telemetry.get("sizing_guide", {})
sizing_bucket = sizing.get("current_bucket", "neutral").title()
sizing_live_n, sizing_bt_n = sizing.get("live_n", 0), sizing.get("backtest_n", 0)
sizing_src_note = f"{sizing_live_n} live-observed, {sizing_bt_n} backtested" if sizing_bt_n else f"{sizing_live_n} live-observed"
if sizing.get("available"):
    kelly_display = f"{sizing['quarter_kelly_pct']:.2f}%"
    sizing_help = (
        f"Based on {sizing['sample_size']} historical Swing-{sizing_bucket} readings on this instance "
        f"({sizing_src_note}): {sizing['win_rate_pct']:.0f}% ended positive, avg win +{sizing['avg_win_pct']:.2f}%, "
        f"avg loss -{sizing['avg_loss_pct']:.2f}%. Quarter-Kelly of that edge is shown. Still a small, "
        f"instance-specific sample, not a professionally validated figure -- not investment advice."
    )
else:
    n = sizing.get("sample_size", 0)
    min_n = sizing.get("min_sample_size", 20)
    kelly_display = f"Collecting ({n}/{min_n})"
    sizing_help = (
        f"Not enough history yet for Swing-{sizing_bucket} readings to estimate a real edge "
        f"({n} of {min_n} needed, {sizing_src_note}). Run a historical backtest from Settings to bootstrap "
        f"this quickly, or check back once more live readings like this one have accumulated."
    )

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
        st.metric("DXY Index", dxy.get("value", "104.20"), dxy.get("delta", "-0.15"), delta_color="inverse", help="US Dollar strength. Feeds Macro Score directly now. Up is bearish for crypto.")
        st.metric("S&P 500", sp500.get("value", "5,200"), sp500.get("delta", "+45"), delta_color="normal", help="Global equity correlation. Feeds Macro Score directly now. Up is bullish for crypto.")
    with pl2:
        st.metric("US 10Y Yield", us10y.get("value", "4.25%"), us10y.get("delta", "+0.02"), delta_color="inverse", help="Risk-free rate. Feeds Macro Score directly now. Up is bearish for crypto.")
        st.metric("VIX", vix.get("value", "14.50"), vix.get("delta", "-0.50"), delta_color="inverse", help="Market fear gauge. Feeds Macro Score directly now. Up is bearish for crypto.")

    st.caption("🟢 Bullish Signal | 🔴 Bearish Signal — all four now feed the Macro Score directly.")
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

# --- HEADER & DATA QUALITY BANNER ---
header_col1, header_col2 = st.columns([5, 1])
with header_col1:
    st.markdown("<h2 style='margin-bottom:0;'>⚡ QUANT DESK TERMINAL</h2>", unsafe_allow_html=True)
    st.caption("Multi-Timeframe Bias & Signal Dashboard")
with header_col2:
    with st.popover("⚙️ Settings"):
        st.markdown("**API Connection**")
        if st.button("🔄 Force Sync"):
            get_telemetry.clear()
            st.rerun()

        st.markdown("<hr style='border:1px solid #333; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("**📈 Bootstrap Track Record**")
        st.caption("Seeds the Track Record from real historical BTC price data instead of waiting on live traffic. Every backtested row is tagged separately from live-observed data. 24 months is recommended — Macro's 14-day horizon needs a longer window to build enough non-overlapping samples per bucket.")
        bt_months = st.number_input("Months of history", min_value=1, max_value=36, value=24, step=1, key="bt_months")
        if st.button("Run Historical Backtest"):
            with st.spinner("Fetching historical data and reconstructing scores — this can take a minute..."):
                try:
                    bt_resp = requests.post(f"{API_URL}/backtest/run", params={"months": int(bt_months)}, timeout=180)
                    bt_result = bt_resp.json() if bt_resp.status_code == 200 else {"status": "error", "error": f"HTTP {bt_resp.status_code}"}
                except Exception as e:
                    bt_result = {"status": "error", "error": str(e)}
            if bt_result.get("status") == "completed":
                cleared_note = f" (replaced {bt_result['cleared_stale']} stale rows from a prior run)" if bt_result.get("cleared_stale") else ""
                st.success(f"Inserted {bt_result.get('inserted', 0)} backtested rows from {bt_result.get('kline_count', 0)} hourly candles{cleared_note}.")
                get_telemetry.clear()
                get_track_record.clear()
            elif bt_result.get("status") == "already_running":
                st.warning("A backtest is already running — check back shortly.")
            else:
                st.error(f"Backtest failed: {bt_result.get('error', 'unknown error')}")

        st.markdown("<hr style='border:1px solid #333; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("**🔬 Factor Research**")
        st.caption("Tests each raw input (RSI, VWAP divergence, funding, DXY, yields, VIX, S&P) against real forward returns, independently — this is what finds real edge instead of testing pre-bundled, hand-weighted composite scores. Read-only: never changes the live formulas by itself.")
        fr_months = st.number_input("Months of history", min_value=1, max_value=36, value=24, step=1, key="fr_months")
        if st.button("Run Factor Research"):
            with st.spinner("Reconstructing feature history and testing correlations — this can take a minute..."):
                try:
                    fr_resp = requests.post(f"{API_URL}/research/run", params={"months": int(fr_months)}, timeout=180)
                    fr_result = fr_resp.json() if fr_resp.status_code == 200 else {"status": "error", "error": f"HTTP {fr_resp.status_code}"}
                except Exception as e:
                    fr_result = {"status": "error", "error": str(e)}
            if fr_result.get("status") == "completed":
                st.session_state["last_research_report"] = fr_result
                st.success(f"Analyzed {fr_result.get('rows_analyzed', 0)} hourly data points across {len(fr_result.get('report', {}))} horizons.")
            elif fr_result.get("status") == "already_running":
                st.warning("Research is already running — check back shortly.")
            else:
                st.error(f"Research failed: {fr_result.get('error', 'unknown error')}")

if not telemetry:
    st.error(f"⚠️ Backend unreachable — no data to show. {st.session_state.get('_fetch_error', '')}")
else:
    gen_at = data_quality.get("generated_at")
    freshness = ""
    if gen_at:
        try:
            ts = datetime.fromisoformat(gen_at.replace("Z", "+00:00"))
            age_s = (datetime.now(timezone.utc) - ts).total_seconds()
            freshness = f"as of {ts.strftime('%H:%M:%S')} UTC ({age_s:.0f}s ago)"
        except Exception:
            freshness = ""

    if data_quality.get("any_fallback"):
        stale_sources = [k.replace("macro_", "").upper() for k, v in data_quality.items() if v == "fallback" and k not in ("any_fallback", "generated_at")]
        st.markdown(
            f"<span class='stale-badge'>🟡 PARTIAL FALLBACK DATA</span> &nbsp; some feeds unreachable, showing placeholder values: "
            f"**{', '.join(stale_sources)}**. Treat scores as indicative only until these recover. {freshness}",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"<span class='live-badge'>🟢 ALL FEEDS LIVE</span> &nbsp; {freshness}", unsafe_allow_html=True)

# --- DYNAMIC SQUEEZE RISK BANNER ---
hm_data = telemetry.get("orderbook_heatmap", {})
upper_wall = hm_data.get("upper_wall", 65411) if hm_data else 65411
lower_wall = hm_data.get("lower_wall", 61582) if hm_data else 61582
ny_cvd_raw = telemetry.get("session_cvd", {}).get("new_york", {}).get("cvd", "")

if FUNDING_RATE < 0:
    status_card(f"⚠️ <b>Short Squeeze Risk</b> · Avg Perp Funding: {FUNDING_RATE_PCT:.4f}% · Negative funding paired with aggressive buying above \\${upper_wall:,.0f}.", "bullish")
elif FUNDING_RATE_PCT > 0.10:
    status_card(f"⚠️ <b>Long Deleveraging Risk</b> · Avg Perp Funding: {FUNDING_RATE_PCT:.4f}% · High perp premium; late longs susceptible to liquidation.", "bearish")
elif LIVE_SPOT_PRICE < ta.get("vwap", LIVE_SPOT_PRICE) and "+" in ny_cvd_raw:
    status_card(f"⚠️ <b>Absorption / Squeeze Risk</b> · Avg Perp Funding: {FUNDING_RATE_PCT:.4f}% · Buyers absorbed below VWAP (\\${ta.get('vwap', 0):,.2f}). Liquidity wall at \\${upper_wall:,.0f}.", "neutral")
else:
    status_card(f"ℹ️ <b>Market Structure Normal</b> · Avg Perp Funding: {FUNDING_RATE_PCT:.4f}%.", "info")

def render_header(title):
    st.markdown(f"<h4 style='color: #E0E0E0; border-bottom: 1px solid #333; padding-bottom: 10px; margin-top: 40px; margin-bottom: 25px; text-transform: uppercase; letter-spacing: 1px;'>{title}</h4>", unsafe_allow_html=True)

with st.expander("📖 Glossary — What These Terms Mean"):
    st.markdown("""
- **RSI (Relative Strength Index)**: measures how fast and how far price has moved recently, on a 0–100 scale. Above ~70 is often called "overbought," below ~30 "oversold" — but in a strong trend it can stay extreme for a while, so it's a momentum gauge, not a timing signal on its own.
- **VWAP (Volume-Weighted Average Price)**: the average price paid so far this session, weighted by how much volume traded at each price. Traders use it as a reference line — price above VWAP is generally read as buyers in control, below as sellers in control.
- **Funding Rate**: a periodic payment between long and short perpetual-futures traders that keeps the futures price tethered to spot. Persistently positive funding means longs are paying shorts (crowded long positioning); negative means the reverse.
- **Open Interest (OI)**: the total number of outstanding futures/options contracts that haven't been closed. Rising OI alongside a price move suggests new money entering the trend; falling OI suggests positions closing out.
- **CVD (Cumulative Volume Delta)**: running total of aggressive buy volume minus aggressive sell volume. Positive CVD means market buy orders are outweighing market sells.
- **Liquidity Heatmap / Order Book Walls**: visualizes where large buy or sell orders are sitting in the order book. Thick clusters ("walls") are levels the market has to absorb to keep moving through.
- **Implied Volatility (IV) Skew**: how options-market-priced volatility differs across strike prices for a given expiry. A steep skew toward downside strikes usually reflects more hedging demand against a drop.
- **Volume Profile (POC / VAH / VAL)**: POC (Point of Control) is the price level with the most traded volume; VAH/VAL (Value Area High/Low) bound the range where most volume traded. These are reference levels, not predictions.
- **On-Chain Exchange Flows**: BTC moving onto or off exchanges. Net outflow is often read as accumulation (moving to cold storage); net inflow as potential selling pressure.
""")

# ==========================================
# SECTION 1: LIVE MARKET OVERVIEW
# ==========================================
render_header("📊 Live Market Overview")
deltas = telemetry.get("deltas", {})
with st.container(border=True):
    ov_r1c1, ov_r1c2, ov_r1c3 = st.columns(3)
    spot_delta = deltas.get("spot_pct_24h")
    ov_r1c1.metric("Live Spot", f"${LIVE_SPOT_PRICE:,.2f}",
                    delta=f"{spot_delta:+.2f}% (24h)" if spot_delta is not None else None)
    rsi_delta = deltas.get("rsi_1h")
    ov_r1c2.metric("RSI(14, Wilder)", f"{ta.get('rsi', 50.0):.1f}",
                    delta=f"{rsi_delta:+.1f} (1h)" if rsi_delta is not None else None,
                    help="Momentum on a 0–100 scale. See the Glossary above for how to read it.")
    vwap_delta = deltas.get("vwap_1h_pct")
    ov_r1c3.metric("Session VWAP (UTC)", f"${ta.get('vwap', LIVE_SPOT_PRICE):,.2f}",
                    delta=f"{vwap_delta:+.3f}% (1h)" if vwap_delta is not None else None,
                    help="Volume-weighted average price since 00:00 UTC. Price above this line is generally read as buyers in control.")

    ov_r2c1, ov_r2c2 = st.columns(2)
    oi_delta = deltas.get("oi_1h_pct")
    ov_r2c1.metric("Open Interest", OPEN_INTEREST,
                    delta=f"{oi_delta:+.2f}% (1h)" if oi_delta is not None else None,
                    help="Total outstanding futures contracts. Rising OI with a price move suggests new money entering the trend.")
    ov_r2c2.metric("Sizing Guide*", kelly_display, help=sizing_help)
    st.caption("*Sizing Guide is based on this instance's own Track Record (empirical win rate and avg win/loss for the current Swing bias bucket) via quarter-Kelly — not a formula-derived guess. Still a small, instance-specific sample; not investment advice.")

if "🟢" in exec_gate: status_card(f"<b>Overall Bias:</b> {exec_gate}", "bullish")
elif "🔴" in exec_gate: status_card(f"<b>Overall Bias:</b> {exec_gate}", "bearish")
elif "⚠️" in exec_gate: status_card(f"<b>Overall Bias:</b> {exec_gate}", "conflict")
elif "🟡" in exec_gate: status_card(f"<b>Overall Bias:</b> {exec_gate}", "neutral")
else: status_card(f"<b>Overall Bias:</b> {exec_gate}", "info")

# ==========================================
# SECTION 2: MULTI-TIMEFRAME MATRIX
# ==========================================
render_header("🧠 Decision Matrix")
col_macro, col_swing, col_micro = st.columns(3)

with col_macro:
    with st.container(border=True):
        st.markdown("**🌐 1. MACRO HORIZON (2-6 WKS)**")
        st.caption("Blends DXY, 10Y yield, VIX, S&P 500, plus BTC's own trend.")
        if macro_score >= 5.5: bias_badge(f"🐂 Bullish · {macro_conf} Confidence", "bullish")
        elif macro_score <= 4.5: bias_badge(f"🐻 Bearish · {macro_conf} Confidence", "bearish")
        else: bias_badge(f"Neutral / Choppy · {macro_conf} Confidence", "neutral")

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
    with st.container(border=True):
        st.markdown("**🔴 2. SWING TACTICAL (1-3 DAYS)**")
        st.caption("Blends 24h price change, VWAP divergence, and funding rate.")
        if swing_score >= 52.0: bias_badge(f"Bullish · {swing_conf} Confidence", "bullish")
        elif swing_score <= 48.0: bias_badge(f"Bearish · {swing_conf} Confidence", "bearish")
        else: bias_badge(f"Neutral / Choppy · {swing_conf} Confidence", "neutral")

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
    with st.container(border=True):
        st.markdown("**🎯 3. MICRO STF (1-4 HRS)**")
        st.caption("Blends RSI(14) momentum and VWAP divergence.")
        micro_dir = insights.get('rationales', {}).get('micro_directive', '⏳ NEUTRAL / CHOP')

        if "🟢" in micro_dir: bias_badge(micro_dir, "bullish")
        elif "🔴" in micro_dir: bias_badge(micro_dir, "bearish")
        else: bias_badge(micro_dir, "neutral")

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
# TRACK RECORD — does this signal actually work?
# ==========================================
track_record = get_track_record()

render_header("📈 Track Record — Does This Signal Actually Work?")
if not track_record or not track_record.get("tracking_since"):
    st.info("No historical data logged yet. This instance just started tracking scores against what price actually did afterward — check back once it's had time to accumulate readings.")
else:
    try:
        since_dt = datetime.fromisoformat(track_record["tracking_since"].replace("Z", "+00:00"))
        since_label = since_dt.strftime("%b %d, %Y")
    except Exception:
        since_label = track_record["tracking_since"]
    st.caption(f"Tracking since {since_label} · minimum sample size for a reading to be shown as reliable: {track_record.get('min_sample_size', 20)}")

    tr_cols = st.columns(3)
    tier_meta = [
        ("macro", "🌐 Macro", tr_cols[0]),
        ("swing", "🔴 Swing", tr_cols[1]),
        ("micro", "🎯 Micro", tr_cols[2]),
    ]
    for tier_key, tier_label, col in tier_meta:
        with col:
            with st.container(border=True):
                tier_data = track_record.get("tiers", {}).get(tier_key, {})
                horizon = tier_data.get("horizon", "")
                st.markdown(f"**{tier_label}** · {horizon} forward return")

                sig = tier_data.get("significance", {})
                sig_status = sig.get("status")
                if sig_status == "significant_edge":
                    bias_badge(f"✓ Validated edge (z={sig.get('z_score')})", "bullish")
                elif sig_status == "inverted_edge":
                    bias_badge(f"⚠ Inverted (z={sig.get('z_score')}) — check formula", "conflict")
                elif sig_status == "no_significant_edge":
                    bias_badge(f"No confirmed edge yet (z={sig.get('z_score')})", "neutral")
                else:
                    bias_badge("Insufficient data to test", "neutral")

                buckets = tier_data.get("buckets", {})
                for bucket_key, bucket_label in [("bullish", "When Bullish"), ("bearish", "When Bearish"), ("neutral", "When Neutral")]:
                    b = buckets.get(bucket_key, {})
                    n = b.get("n", 0)
                    live_n, bt_n = b.get("live_n", 0), b.get("backtest_n", 0)
                    src_note = f"{live_n} live, {bt_n} backtest" if bt_n else f"{live_n} live"
                    if not b.get("sufficient_sample"):
                        st.caption(f"{bucket_label}: n={n} ({src_note}) — still collecting (need {track_record.get('min_sample_size', 20)})")
                    else:
                        avg_r = b.get("avg_return_pct")
                        pct_pos = b.get("pct_positive")
                        sign = "+" if avg_r is not None and avg_r >= 0 else ""
                        st.write(f"{bucket_label}: avg {sign}{avg_r}% · {pct_pos}% positive · n={n} ({src_note})")
    st.caption(track_record.get("caveat", ""))

    if any(tr.get("significance", {}).get("status") == "inverted_edge" for tr in track_record.get("tiers", {}).values()):
        status_card(
            "⚠️ <b>One or more tiers show a statistically significant INVERTED relationship</b> — the bias label "
            "and the actual historical outcome point opposite directions. Treat that tier's badge with extra "
            "caution until the formula is revisited.",
            "conflict",
        )

# --- Factor Research report (only shown after a run this session) ---
research_report = st.session_state.get("last_research_report")
if research_report and research_report.get("report"):
    render_header("🔬 Factor Research — Which Inputs Actually Predict Returns")
    st.caption(research_report.get("note", ""))
    for horizon_label, features in research_report["report"].items():
        with st.container(border=True):
            st.markdown(f"**{horizon_label} forward return**")
            rf_cols = st.columns(4)
            for i, (feat_name, feat_data) in enumerate(features.items()):
                with rf_cols[i % 4]:
                    full = feat_data.get("full_period", {})
                    r, sig, robust = full.get("r"), full.get("significant"), feat_data.get("robust")
                    if r is None:
                        bias_badge(feat_name, "neutral")
                    elif robust:
                        bias_badge(f"{feat_name}: r={r:+.3f} ✓ robust", "bullish" if r > 0 else "bearish")
                    elif sig:
                        bias_badge(f"{feat_name}: r={r:+.3f} (not robust)", "neutral")
                    else:
                        bias_badge(f"{feat_name}: r={r:+.3f} (no signal)", "neutral")

# ==========================================
# SECTION 3: SIGNAL SUMMARY
# ==========================================
if insights or telemetry:
    render_header("📜 Signal Summary")

    if "🟢" in exec_gate: sig_kind = "bullish"
    elif "🔴" in exec_gate: sig_kind = "bearish"
    elif "⚠️" in exec_gate: sig_kind = "conflict"
    elif "🟡" in exec_gate: sig_kind = "neutral"
    else: sig_kind = "info"

    dynamic_thesis = insights.get('liquidity_thesis', 'Awaiting live session data.')
    safe_guidance = insights.get('institutional_guidance', 'N/A')
    status_card(f"🛡️ <b>Guidance:</b> {safe_guidance}<br>🧠 <b>Liquidity Thesis:</b> {dynamic_thesis}", sig_kind)

# ==========================================
# SECTION 4: RISK GATEWAY
# ==========================================
render_header("🛡️ Desk-Level Risk Gateway")

blended_risk = round(((macro_score * 10) + swing_score + micro_score) / 3, 1)

with st.container(border=True):
    rg1, rg2, rg3 = st.columns(3)
    rg1.metric("Risk Base Score", f"{blended_risk} / 100", help="Blended read across all three tiers (macro ×10, swing, micro, averaged). Higher = more bullish composite.")
    rg2.metric("Upper Liq Wall", f"${upper_wall:,.0f}", help="Nearest large resting sell-side liquidity cluster above spot.")
    rg3.metric("Lower Liq Wall", f"${lower_wall:,.0f}", help="Nearest large resting buy-side liquidity cluster below spot.")

# ==========================================
# SECTION 5: TELEMETRY & CHARTS
# ==========================================
render_header("🔬 Telemetry & Liquidity")
if not telemetry:
    st.caption("Telemetry unavailable while the backend is unreachable (see banner above).")
else:
    session_info = telemetry.get("session_cvd", {})
    cvd_help = "Cumulative Volume Delta: running total of aggressive buy volume minus sell volume for this session. Positive means market buys are outweighing market sells."
    with st.container(border=True):
        sc1, sc2, sc3 = st.columns(3)
        with sc1: st.metric(session_info.get("asia", {}).get("name", "Asia Open"), session_info.get("asia", {}).get("cvd", "N/A"), session_info.get("asia", {}).get("delta", ""), help=cvd_help)
        with sc2: st.metric(session_info.get("london", {}).get("name", "London Open"), session_info.get("london", {}).get("cvd", "N/A"), session_info.get("london", {}).get("delta", ""), help=cvd_help)
        with sc3: st.metric(session_info.get("new_york", {}).get("name", "NY Open"), session_info.get("new_york", {}).get("cvd", "N/A"), session_info.get("new_york", {}).get("delta", ""), help=cvd_help)
    st.caption("Known limitation: sessions are bucketed by hour-of-day across a rolling 24h window, so whichever session is currently in progress shows a partial read rather than a full prior session. Not yet fixed — flagged here rather than presented as directly comparable.")

    st.markdown("<br>", unsafe_allow_html=True)
    viz_col1, viz_col2 = st.columns([2, 1])
    CHART_HEIGHT = 480  # shared by both charts so they align edge-to-edge

    with viz_col1:
      with st.container(border=True):
        st.markdown("**🗺️ Order Book Liquidity Heatmap**")
        z_matrix = hm_data.get("z_matrix", []) if hm_data else []
        snapshots_collected = hm_data.get("snapshots_collected", HEATMAP_HISTORY_LEN_FALLBACK) if hm_data else 0
        snapshots_total = hm_data.get("snapshots_total", HEATMAP_HISTORY_LEN_FALLBACK) if hm_data else HEATMAP_HISTORY_LEN_FALLBACK
        MIN_SNAPSHOTS_TO_RENDER = 10

        if len(z_matrix) > 0 and snapshots_collected >= MIN_SNAPSHOTS_TO_RENDER:
            try:
                z_array = np.array(z_matrix, dtype=float)
                time_steps = hm_data.get("time_steps", [])
                prices = hm_data.get("prices", [])

                valid_vals = z_array[z_array > 0]
                z_max = float(np.percentile(valid_vals, 98)) if valid_vals.size > 0 else 10.0
                if z_max <= 0:
                    z_max = 10.0

                # Brand-matched teal gradient (near-black -> navy -> teal -> near-white)
                # instead of a rainbow scale, so heavier liquidity clusters read as
                # brighter/hotter without the visual noise of a multi-hue palette.
                teal_colorscale = [
                    [0.0, "#0A0E17"],
                    [0.20, "#0F2A3D"],
                    [0.45, "#0E7490"],
                    [0.70, "#00C2CC"],
                    [0.88, "#26FFDE"],
                    [1.0, "#F0FFFC"],
                ]

                # Thin the x-axis ticks so 30 snapshot labels don't crowd the axis.
                tick_idx = list(range(0, len(time_steps), 5)) if time_steps else []
                tick_vals = [time_steps[i] for i in tick_idx]

                fig_heatmap = go.Figure(data=go.Heatmap(
                    z=z_array, x=time_steps if time_steps else None, y=prices if prices else None,
                    colorscale=teal_colorscale, showscale=True, zmin=0.0, zmax=z_max,
                    zsmooth=False,  # crisp cells -- smoothing blurred zero/real-value boundaries
                    hovertemplate="Price: $%{y:,.0f}<br>Depth: %{z:.2f}<br>%{x}<extra></extra>",
                    colorbar=dict(title=dict(text="Depth", font=dict(color="#8892B0")), thickness=12, len=0.8, tickfont=dict(color="#8892B0")),
                    xgap=1, ygap=1,  # thin gaps between cells read as a grid, not a blob
                ))
                fig_heatmap.update_layout(
                    height=CHART_HEIGHT, margin=dict(l=10, r=10, t=10, b=10), template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(title=dict(text="Spot Price ($)", font=dict(color="#8892B0")), tickformat="$,.0f", showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color="#8892B0"), automargin=True),
                    xaxis=dict(title=dict(text="Snapshots (Older → Newer)", font=dict(color="#8892B0")), showgrid=False, tickfont=dict(color="#8892B0"), tickmode="array", tickvals=tick_vals, ticktext=tick_vals, automargin=True),
                )
                fig_heatmap.add_hline(y=upper_wall, line_dash="dot", line_color="#FF3366", line_width=1.5, annotation_text="Upper Wall", annotation_font=dict(color="#FF3366", size=11))
                fig_heatmap.add_hline(y=lower_wall, line_dash="dot", line_color="#00E676", line_width=1.5, annotation_text="Lower Support", annotation_font=dict(color="#00E676", size=11))
                fig_heatmap.add_hline(y=LIVE_SPOT_PRICE, line_dash="solid", line_color="#F5F5F5", line_width=1, opacity=0.55, annotation_text="Spot", annotation_font=dict(color="#F5F5F5", size=11), annotation_position="left")
                st.plotly_chart(fig_heatmap, use_container_width=True)
                st.caption("Price axis is a fixed grid that only shifts when spot trades outside it. Cells are shown unsmoothed so bucket boundaries stay accurate.")
            except Exception:
                st.info("🗺️ Heatmap rendering matrix...")
        elif len(z_matrix) > 0:
            # Grid just reset (spot moved outside its previous range) -- rather
            # than render a chart that's mostly still-empty padding (which reads
            # as broken), show an honest progress state until there's enough
            # real data for the picture to be meaningful.
            st.info(f"🗺️ Rebuilding after a price move — collecting snapshot {snapshots_collected}/{snapshots_total}. The grid resets when spot trades outside its current range.")
        else:
            st.info("🗺️ Heatmap buffer initializing... collecting rolling snapshots.")

    with viz_col2:
      with st.container(border=True):
        st.markdown("**📉 Deribit Volatility Skew**")
        vs_data = telemetry.get("volatility_skew", {})
        strike_vals = vs_data.get("strikes", [])
        iv_vals = vs_data.get("iv_surface", [])
        expiry_label = vs_data.get("expiry", "N/A")

        if len(strike_vals) > 0 and len(iv_vals) > 0:
            fig_skew = go.Figure()
            fig_skew.add_trace(go.Scatter(x=strike_vals, y=iv_vals, mode='lines', line=dict(color='rgba(0, 255, 204, 0.2)', width=8, shape='spline'), hoverinfo='skip', showlegend=False))
            fig_skew.add_trace(go.Scatter(x=strike_vals, y=iv_vals, mode='lines', line=dict(color='#00FFCC', width=3, shape='spline'), fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.08)', showlegend=False))
            fig_skew.update_layout(
                height=CHART_HEIGHT, margin=dict(l=10, r=10, t=20, b=10), template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title=dict(text="Strike Price ($)", font=dict(color="#8892B0")), showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False, tickfont=dict(color="#8892B0"), automargin=True),
                yaxis=dict(title=dict(text="Implied Volatility (%)", font=dict(color="#8892B0")), showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False, tickfont=dict(color="#8892B0"), automargin=True)
            )
            st.plotly_chart(fig_skew, use_container_width=True)
            st.caption(f"Single expiry only: {expiry_label} (no longer blended across tenors).")
        else:
            st.info("📉 Volatility Skew surface loading...")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**⛓️ On-Chain Exchange Flows**")
    oc_data = telemetry.get("onchain_flows", {})
    with st.container(border=True):
        oc1, oc2, oc3 = st.columns(3)
        with oc1: st.metric("24H Net Exchange Flow", oc_data.get("btc_netflow_24h", "N/A"), "Cold Storage Absorption", help="BTC moving onto (positive) or off (negative) exchanges. Net outflow is often read as accumulation.")
        with oc2: st.metric("24H Stablecoin Mint", oc_data.get("stablecoin_mint_24h", "N/A"), "Purchasing Power", help="New stablecoin issuance, often watched as a proxy for fresh buying power entering crypto markets.")
        with oc3: st.metric("Global Reserve Trend", oc_data.get("exchange_reserve_trend", "N/A"), help="Direction of total BTC held on exchanges. A declining trend is generally read as coins moving to longer-term holding.")

# ==========================================
# SECTION 6: QUANTITATIVE MARKET DATA & ANALYTICAL GUIDANCE
# ==========================================
if insights:
    render_header("📝 Quantitative Market Data & Guidance")
    vp_col, cat_col, guide_col = st.columns(3)

    with vp_col:
        with st.container(border=True):
            st.markdown("**📊 Volume Profile**")
            vp = insights.get("volume_profile", {})
            st.write(f"- **Point of Control (POC):** {vp.get('poc', 'N/A')}")
            st.write(f"- **Value Area High (VAH):** {vp.get('vah', 'N/A')}")
            st.write(f"- **Value Area Low (VAL):** {vp.get('val', 'N/A')}")

    with cat_col:
        with st.container(border=True):
            st.markdown("**⚠️ Upcoming Catalysts & Filters**")
            for cat in insights.get("catalysts", []):
                st.write(f"- {cat}")

    with guide_col:
        with st.container(border=True):
            st.markdown("**🧭 Signal Interpretation**")
            raw_action = insights.get("action_plan", "Scores are near neutral across timeframes right now.")
            action_plan_clean = raw_action.replace("*", "").replace("  ", " ").replace("$", "\\$")
            tone = insights.get("action_plan_tone", "info")
            kind_map = {"conflict": "conflict", "bullish": "bullish", "bearish": "bearish", "neutral": "neutral"}
            status_card(action_plan_clean, kind_map.get(tone, "info"))
