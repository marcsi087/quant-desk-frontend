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
data_quality = telemetry.get("data_quality", {})

plumbing = telemetry.get("macro_plumbing", {
    "dxy": {"value": "104.20", "delta": "+0.00"}, "us10y": {"value": "4.250%", "delta": "+0.000"},
    "vix": {"value": "14.50", "delta": "+0.00"}, "sp500": {"value": "5,200", "delta": "+0"}
})
insights = telemetry.get("insights", {})

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
        st.caption("Tests each raw input against real forward returns, independently — now 14 features: the original 8 (RSI, VWAP divergence, funding, DXY, yields, VIX, S&P) plus order-flow imbalance, 3/7/14-day momentum, and volatility regime, added to give Swing and Macro's own horizons a fairer test. Read-only: never changes the live formulas by itself.")
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

        st.markdown("<hr style='border:1px solid #333; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("**💥 Magnitude Research (Squeeze Risk Test)**")
        st.caption("Different question than Factor Research: does extreme funding (or extreme VIX, momentum, order flow, or elevated volatility) predict a BIGGER subsequent move, regardless of direction? This is the actual hypothesis behind the Squeeze Risk banner — never tested until now. Read-only, same non-overlap correction as Factor Research.")
        mag_months = st.number_input("Months of history", min_value=1, max_value=36, value=24, step=1, key="mag_months")
        if st.button("Run Magnitude Research"):
            with st.spinner("Testing whether extremity predicts move size — this can take a minute..."):
                try:
                    mag_resp = requests.post(f"{API_URL}/research/run-magnitude", params={"months": int(mag_months)}, timeout=180)
                    mag_result = mag_resp.json() if mag_resp.status_code == 200 else {"status": "error", "error": f"HTTP {mag_resp.status_code}"}
                except Exception as e:
                    mag_result = {"status": "error", "error": str(e)}
            if mag_result.get("status") == "completed":
                st.session_state["last_magnitude_report"] = mag_result
                st.success(f"Analyzed {mag_result.get('rows_analyzed', 0)} hourly data points.")
            elif mag_result.get("status") == "already_running":
                st.warning("Magnitude research is already running — check back shortly.")
            else:
                st.error(f"Magnitude research failed: {mag_result.get('error', 'unknown error')}")

        st.markdown("<hr style='border:1px solid #333; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("**⚖️ Calibrate Formula**")
        st.caption("Fits actual regression coefficients for a short, evidence-backed feature list against real forward returns — only pass features that already showed 'robust: true' in Factor Research above. Read-only: shows you the fitted numbers, doesn't rewrite any formula by itself.")
        cal_horizon = st.selectbox("Horizon", ["4h", "2d", "14d"], key="cal_horizon")
        cal_features = st.text_input("Features (comma-separated)", value="vix_pct,spx_pct", key="cal_features")
        cal_months = st.number_input("Months of history", min_value=1, max_value=36, value=24, step=1, key="cal_months")
        if st.button("Run Calibration"):
            with st.spinner("Fitting regression on the non-overlapping sample — this can take a minute..."):
                try:
                    cal_resp = requests.post(
                        f"{API_URL}/research/calibrate",
                        params={"months": int(cal_months), "horizon": cal_horizon, "features": cal_features},
                        timeout=180,
                    )
                    cal_result = cal_resp.json() if cal_resp.status_code == 200 else {"status": "error", "error": f"HTTP {cal_resp.status_code}"}
                except Exception as e:
                    cal_result = {"status": "error", "error": str(e)}
            if cal_result.get("status") == "completed":
                st.session_state["last_calibration"] = cal_result
                fit = cal_result.get("fit_non_overlapping", {})
                if "error" in fit:
                    st.warning(f"Fit didn't converge: {fit['error']}")
                else:
                    st.success(f"Fitted on n={fit.get('n')} non-overlapping windows, R²={fit.get('r_squared')}")
            elif cal_result.get("status") == "already_running":
                st.warning("A calibration is already running — check back shortly.")
            else:
                st.error(f"Calibration failed: {cal_result.get('error', 'unknown error')}")

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

if FUNDING_RATE < -0.0005 and "+" in ny_cvd_raw:
    status_card(f"⚠️ <b>Short Squeeze Risk</b> · Avg Perp Funding: {FUNDING_RATE_PCT:.4f}% · Negative funding (crowded shorts) paired with confirmed aggressive buying above \\${upper_wall:,.0f}.", "bullish")
elif FUNDING_RATE_PCT > 0.10:
    status_card(f"⚠️ <b>Long Deleveraging Risk</b> · Avg Perp Funding: {FUNDING_RATE_PCT:.4f}% · High perp premium; late longs susceptible to liquidation.", "bearish")
elif LIVE_SPOT_PRICE < ta.get("vwap", LIVE_SPOT_PRICE) and "+" in ny_cvd_raw:
    status_card(f"⚠️ <b>Absorption / Squeeze Risk</b> · Avg Perp Funding: {FUNDING_RATE_PCT:.4f}% · Buyers absorbed below VWAP (\\${ta.get('vwap', 0):,.2f}). Liquidity wall at \\${upper_wall:,.0f}.", "neutral")
else:
    status_card(f"ℹ️ <b>Market Structure Normal</b> · Avg Perp Funding: {FUNDING_RATE_PCT:.4f}%.", "info")
st.caption("Tested via Magnitude Research: funding extremity did NOT robustly predict bigger 4h moves (r=+0.056, not consistent across periods). The mechanism above is real finance but unconfirmed at this horizon — treat this banner as descriptive, not as a validated guardrail. See the Volatility Guardrail below for what actually tested robust.")

# --- VOLATILITY GUARDRAIL — built from what Magnitude Research actually
# validated at 4h (Micro's horizon), not from an assumption. ATR (r=+0.270)
# and VIX extremity (r=+0.181) both robustly predicted bigger subsequent
# moves on n=4,313 independent windows -- the strongest, most trustworthy
# result in that whole test. This is a magnitude warning, not a direction
# call: it says "expect a bigger swing," not "expect it to go up or down."
atr_pct_val = ta.get("atr_pct", 0.01)
vix_pct_val = plumbing.get("vix", {}).get("pct_change", 0.0) if isinstance(plumbing.get("vix"), dict) else 0.0
atr_elevated = atr_pct_val > 0.015
vix_elevated = abs(vix_pct_val) > 3.0

if atr_elevated and vix_elevated:
    status_card(f"🌪️ <b>High Volatility Regime</b> · 1H ATR: {atr_pct_val*100:.2f}% · VIX move: {vix_pct_val:+.2f}% · Both signals elevated together — validated to predict bigger 4h moves (ATR r=+0.270, VIX r=+0.181, robust on n=4,313). Expect wider swings in either direction; size and stops accordingly, not just directional bias.", "conflict")
elif atr_elevated:
    status_card(f"⚠️ <b>Elevated Recent Volatility</b> · 1H ATR: {atr_pct_val*100:.2f}% · The single strongest validated 4h magnitude predictor we've tested (r=+0.270, robust, n=4,313). Bigger-than-usual moves are more likely in either direction over the next few hours.", "neutral")
elif vix_elevated:
    status_card(f"⚠️ <b>Elevated VIX Movement</b> · VIX move: {vix_pct_val:+.2f}% · Validated 4h magnitude predictor (r=+0.181, robust, n=4,313). Bigger-than-usual BTC moves are more likely in either direction over the next few hours.", "neutral")
else:
    status_card(f"✅ <b>Normal Volatility Regime</b> · 1H ATR: {atr_pct_val*100:.2f}% · VIX move: {vix_pct_val:+.2f}% · Neither validated magnitude signal is elevated right now.", "info")

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
- **Network Activity**: real, live Bitcoin network data (mempool backlog, fee pressure) — a proxy for on-chain demand, not exchange-specific buying/selling flow (that requires a paid data provider this app doesn't currently use).
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

# ==========================================
# PRICE CHART — the one thing every trading dashboard should lead with,
# which this one didn't have until now
# ==========================================
price_chart_data = telemetry.get("price_chart", [])
if price_chart_data:
    render_header("📈 BTC/USD — Last 8 Days (1H)")
    with st.container(border=True):
        times = [datetime.fromtimestamp(p["t"], tz=timezone.utc) for p in price_chart_data]
        opens = [p["o"] for p in price_chart_data]
        highs = [p["h"] for p in price_chart_data]
        lows = [p["l"] for p in price_chart_data]
        closes = [p["c"] for p in price_chart_data]

        fig_price = go.Figure(data=go.Candlestick(
            x=times, open=opens, high=highs, low=lows, close=closes,
            increasing_line_color="#00E676", decreasing_line_color="#FF3366",
            increasing_fillcolor="#00E676", decreasing_fillcolor="#FF3366",
            name="BTC/USD",
        ))
        vwap_val = ta.get("vwap", LIVE_SPOT_PRICE)
        fig_price.add_hline(y=vwap_val, line_dash="dot", line_color="#00FFCC", line_width=1.5,
                             annotation_text=f"Session VWAP ${vwap_val:,.0f}", annotation_font=dict(color="#00FFCC", size=11))
        fig_price.add_hline(y=upper_wall, line_dash="dot", line_color="#FF3366", line_width=1,
                             annotation_text="Upper Wall", annotation_font=dict(color="#FF3366", size=10), opacity=0.6)
        fig_price.add_hline(y=lower_wall, line_dash="dot", line_color="#00E676", line_width=1,
                             annotation_text="Lower Wall", annotation_font=dict(color="#00E676", size=10), opacity=0.6)
        fig_price.update_layout(
            height=420, margin=dict(l=10, r=10, t=10, b=10), template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, tickfont=dict(color="#8892B0"), rangeslider=dict(visible=False), automargin=True),
            yaxis=dict(title=dict(text="Price ($)", font=dict(color="#8892B0")), tickformat="$,.0f",
                       showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#8892B0"), automargin=True),
            showlegend=False,
        )
        st.plotly_chart(fig_price, use_container_width=True)
        st.caption("Real hourly candles from Binance, same fetch that powers 7-Day Momentum on the Confluence Board below. VWAP and liquidity walls are the same live levels referenced throughout this page — this is where they actually are relative to price.")

# ==========================================
# MICRO SIGNAL — the one tier with a validated, calibrated edge
# ==========================================
render_header("🎯 Micro Signal (1-4 HRS) — The Actionable Timeframe")
with st.container(border=True):
    st.caption("Calibrated regression on VIX + S&P 500 (real fit, n=4,313 non-overlapping windows, R²=0.023) — RSI and VWAP divergence were tested and dropped after showing no significant edge at this horizon. Note: R²=0.023 is a small, real, repeatable statistical tilt, not a strong individual prediction — see Track Record for what an edge this size looks like in realized win rates, and treat it as one input, not a certainty.")
    micro_dir = insights.get('rationales', {}).get('micro_directive', '⏳ NEUTRAL / CHOP')
    if "🟢" in micro_dir: bias_badge(micro_dir, "bullish")
    elif "🔴" in micro_dir: bias_badge(micro_dir, "bearish")
    else: bias_badge(micro_dir, "neutral")
    st.metric("Micro Score", f"{micro_score} / 100")
    micro_rat = insights.get('rationales', {}).get('micro', 'Awaiting live data...')
    st.caption(f"**Rationale:** {micro_rat}")

st.caption("Macro and Swing moved to the Confluence Board below — we tested composite scores for both against ~2 years of real data and found no reliable edge, so a bias badge and price-target table for them would have been presenting more confidence than the evidence supports.")

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
                    non_overlap = feat_data.get("non_overlapping", {})
                    r = full.get("r")
                    r_no = non_overlap.get("r")
                    robust = feat_data.get("robust")
                    robust_naive = feat_data.get("robust_naive")
                    no_n = non_overlap.get("n")
                    r_no_str = f"{r_no:+.3f}" if r_no is not None else "N/A"
                    if r is None:
                        bias_badge(feat_name, "neutral")
                    elif robust:
                        bias_badge(f"{feat_name}: r={r_no:+.3f} ✓ robust (n={no_n} independent)", "bullish" if r_no > 0 else "bearish")
                    elif robust_naive:
                        bias_badge(f"{feat_name}: r={r:+.3f} full-period (fails non-overlap: r={r_no_str} at n={no_n})", "neutral")
                    elif full.get("significant"):
                        bias_badge(f"{feat_name}: r={r:+.3f} (not consistent across periods)", "neutral")
                    else:
                        bias_badge(f"{feat_name}: r={r:+.3f} (no signal)", "neutral")

# --- Magnitude Research result (squeeze-risk hypothesis test) ---
magnitude_report = st.session_state.get("last_magnitude_report")
if magnitude_report and magnitude_report.get("report"):
    render_header("💥 Magnitude Research — Does Extremity Predict Move Size?")
    st.caption(magnitude_report.get("note", ""))

    funding_4h = magnitude_report["report"].get("4h", {}).get("funding_rate_abs")
    if funding_4h:
        r = funding_4h.get("full_period", {}).get("r")
        robust = funding_4h.get("robust")
        no_n = funding_4h.get("non_overlapping", {}).get("n")
        if r is not None:
            if robust:
                status_card(f"✅ <b>Squeeze Risk banner is empirically supported</b> — extreme funding at the 4h horizon (Micro's timeframe) robustly predicts bigger moves: r={r:+.3f}, n={no_n} independent windows.", "bullish")
            else:
                status_card(f"⚠️ <b>Squeeze Risk banner is NOT yet empirically confirmed</b> — extreme funding at 4h shows r={r:+.3f} but does not clear the corrected robustness bar (n={no_n} independent windows). The banner's underlying mechanism is real finance, but this specific claim hasn't been validated the way Micro's actual score was.", "neutral")

    oi_quality = magnitude_report.get("oi_data_quality", {})
    if oi_quality:
        oi_kind = "bullish" if oi_quality.get("tested") else "neutral"
        oi_icon = "📊" if oi_quality.get("tested") else "ℹ️"
        status_card(f"{oi_icon} <b>Open Interest coverage:</b> {oi_quality.get('note', '')}", oi_kind)

    for horizon_label, features in magnitude_report["report"].items():
        with st.container(border=True):
            st.markdown(f"**{horizon_label} — extremity vs. move size**")
            mag_cols = st.columns(len(features))
            for i, (feat_name, feat_data) in enumerate(features.items()):
                with mag_cols[i % len(mag_cols)]:
                    full = feat_data.get("full_period", {})
                    non_overlap = feat_data.get("non_overlapping", {})
                    r = full.get("r")
                    r_no = non_overlap.get("r")
                    robust = feat_data.get("robust")
                    robust_naive = feat_data.get("robust_naive")
                    no_n = non_overlap.get("n")
                    r_no_str = f"{r_no:+.3f}" if r_no is not None else "N/A"
                    if r is None:
                        bias_badge(feat_name, "neutral")
                    elif robust:
                        bias_badge(f"{feat_name}: r={r_no:+.3f} ✓ robust (n={no_n})", "bullish")
                    elif robust_naive:
                        bias_badge(f"{feat_name}: r={r:+.3f} full-period (fails non-overlap: r={r_no_str} at n={no_n})", "neutral")
                    elif full.get("significant"):
                        bias_badge(f"{feat_name}: r={r:+.3f} (not consistent)", "neutral")
                    else:
                        bias_badge(f"{feat_name}: r={r:+.3f} (no signal)", "neutral")

# --- Calibration result (only shown after a run this session) ---
calibration = st.session_state.get("last_calibration")
if calibration and calibration.get("fit_non_overlapping"):
    render_header("⚖️ Calibrated Formula")
    fit_no = calibration["fit_non_overlapping"]
    fit_ov = calibration.get("fit_overlapping", {})
    if "error" in fit_no:
        st.warning(f"Fit didn't converge: {fit_no['error']}")
    else:
        st.caption(calibration.get("note", ""))
        with st.container(border=True):
            st.markdown(f"**{calibration.get('horizon')} forward return — fitted on n={fit_no['n']} non-overlapping windows, R²={fit_no['r_squared']}**")
            formula_parts = [f"{fit_no['intercept']:+.4f}"]
            for feat, coef in fit_no["coefficients"].items():
                formula_parts.append(f"{coef:+.4f}×{feat}")
            st.code("forward_return ≈ " + " ".join(formula_parts))
            if "coefficients" in fit_ov:
                st.caption("For comparison, the (less trustworthy) overlapping-sample fit: " + ", ".join(f"{k}={v:+.4f}" for k, v in fit_ov["coefficients"].items()) + f", intercept={fit_ov.get('intercept', 0):+.4f}")

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
    st.markdown("**⛓️ Network Activity**")
    net_data = telemetry.get("network_activity", {})
    with st.container(border=True):
        nc1, nc2, nc3 = st.columns(3)
        with nc1: st.metric("Fastest Fee", f"{net_data.get('fastest_fee_satvb', 'N/A')} sat/vB", help="Real, live data from mempool.space. Fee needed for next-block confirmation -- a rough proxy for how much on-chain demand is competing for block space right now.")
        with nc2: st.metric("Mempool Backlog", f"{net_data.get('mempool_tx_count', 'N/A'):,}" if isinstance(net_data.get('mempool_tx_count'), int) else "N/A", help="Unconfirmed transactions waiting in the mempool. A growing backlog means more on-chain activity than the network can immediately clear.")
        with nc3: st.metric("Congestion", net_data.get("congestion_label", "N/A"))
        st.caption("This replaced the app's old \"On-Chain Exchange Flows\" section, which was never real data — it was a formula derived from trading volume and price change, not from the blockchain. This is real, live network data instead. It's a narrower signal (network congestion, not exchange-specific netflow) because genuine labeled-address exchange flow data requires a paid provider (Glassnode, CryptoQuant, etc.) with no free equivalent.")

# ==========================================
# CONFLUENCE BOARD — live context for Swing/Macro thinking, not a score
# ==========================================
confluence = telemetry.get("confluence_board")
if confluence:
    render_header("🧭 Confluence Board — Swing & Macro Context")
    st.caption("Six real, live inputs relevant to a multi-day-to-multi-week view of Bitcoin — each shown with its own honest lean and explanation. This is deliberately NOT a single composite score: we tested that approach for Swing and Macro against ~2 years of real data and found no reliable edge (see Track Record and Factor Research). This organizes real information for your own judgment instead.")

    SCENARIO_KIND_MAP = {
        "strong_bullish": "bullish", "strong_bearish": "bearish",
        "moderate_bullish": "bullish", "moderate_bearish": "bearish",
        "split": "conflict", "quiet": "neutral",
    }
    LEAN_BADGE_KIND = {"bullish": "bullish", "bearish": "bearish", "neutral": "neutral"}

    factor_cols = st.columns(3)
    for i, factor in enumerate(confluence.get("factors", [])):
        with factor_cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{factor['label']}**")
                bias_badge(f"{factor['value_str']} · {factor['lean'].title()}", LEAN_BADGE_KIND.get(factor['lean'], "neutral"))
                st.caption(factor["explanation"])

    st.markdown("<br>", unsafe_allow_html=True)
    b, r, n = confluence.get("bullish_count", 0), confluence.get("bearish_count", 0), confluence.get("neutral_count", 0)
    scenario_kind = SCENARIO_KIND_MAP.get(confluence.get("scenario"), "info")
    status_card(
        f"{confluence.get('scenario_icon', '')} <b>{confluence.get('scenario_label', '')}</b> — "
        f"{b} bullish · {r} bearish · {n} neutral<br>{confluence.get('scenario_summary', '')}",
        scenario_kind,
    )
    st.markdown(confluence.get("scenario_explanation", ""))
    st.caption(confluence.get("disclaimer", ""))
