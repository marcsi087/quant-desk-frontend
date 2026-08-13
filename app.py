import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION ---
API_URL = "https://quant-desk-backend-rata.onrender.com/api/v1"
HEATMAP_HISTORY_LEN_FALLBACK = 30  # mirrors backend's HEATMAP_HISTORY_LEN; used only if a payload predates this field
st.set_page_config(page_title="Micro Edge Terminal", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

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
#   - bias_badge: small inline chip, for per-item bias tags
#   - status_card: dark card with a colored left border, for section-level
#     summaries -- restrained compared to a full bright alert fill, but
#     still color-coded for a quick scan.
def bias_badge(text, kind):
    st.markdown(f'<span class="bias-badge bias-{kind}">{text}</span>', unsafe_allow_html=True)

def status_card(html, kind="info"):
    st.markdown(f'<div class="status-card {kind}">{html}</div>', unsafe_allow_html=True)

def render_header(title):
    st.markdown(f"<h4 style='color: #E0E0E0; border-bottom: 1px solid #333; padding-bottom: 10px; margin-top: 40px; margin-bottom: 25px; text-transform: uppercase; letter-spacing: 1px;'>{title}</h4>", unsafe_allow_html=True)

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
        st.metric("DXY Index", dxy.get("value", "104.20"), dxy.get("delta", "-0.15"), delta_color="inverse", help="US Dollar strength. Historically a mild headwind for crypto when rising. See Macro Conditions below for the full picture.")
        st.metric("S&P 500", sp500.get("value", "5,200"), sp500.get("delta", "+45"), delta_color="normal", help="Global equity correlation. Historically a mild tailwind for crypto when rising. See Macro Conditions below for the full picture.")
    with pl2:
        st.metric("US 10Y Yield", us10y.get("value", "4.25%"), us10y.get("delta", "+0.02"), delta_color="inverse", help="Risk-free rate. Historically a mild headwind for crypto when rising. See Macro Conditions below for the full picture.")
        st.metric("VIX", vix.get("value", "14.50"), vix.get("delta", "-0.50"), delta_color="inverse", help="Market fear gauge. The one cross-asset input with a validated, tested link to Bitcoin's 4h moves -- see the Micro Signal card for the actual evidence.")

    st.caption("Live reference values, shown for context -- not inputs to any trading bias except where the Micro Signal card explicitly says so.")
    st.markdown("<hr style='border:1px solid #333; margin: 20px 0;'>", unsafe_allow_html=True)
    st.markdown("<h5 style='color:#8892B0; margin-bottom:10px;'>💼 Trade Tracker</h5>", unsafe_allow_html=True)
    st.caption("A simple PnL calculator for a trade you're already in -- not tied to any signal on this page. Useful for any position, on any timeframe.")

    track_trade = st.toggle("Track a position", value=False)
    if track_trade:
        with st.expander("Position", expanded=True):
            trade_label = st.text_input("Label (optional)", value="", placeholder="e.g. BTC long", key="trade_label")
            trade_side = st.radio("Side", ["Long", "Short"], horizontal=True, key="trade_side")
            trade_entry = st.number_input("Entry Price ($)", value=float(round(LIVE_SPOT_PRICE)), step=10.0, key="trade_entry")
            trade_collat = st.number_input("Collateral ($)", value=1000.00, step=100.0, key="trade_collat")
            trade_lev = st.slider("Leverage", min_value=1.0, max_value=50.0, value=5.0, step=0.5, key="trade_lev")
            if trade_entry > 0:
                if trade_side == "Long":
                    trade_roi = ((LIVE_SPOT_PRICE - trade_entry) / trade_entry) * trade_lev * 100
                else:
                    trade_roi = ((trade_entry - LIVE_SPOT_PRICE) / trade_entry) * trade_lev * 100
                trade_pnl = (trade_roi / 100) * trade_collat
                pnl_color = "#00E676" if trade_pnl >= 0 else "#FF3366"
                pnl_sign = "+" if trade_pnl >= 0 else ""
                label_prefix = f"{trade_label} — " if trade_label else ""
                st.markdown(f"<p style='margin-bottom:2px; color:#8892B0;'>{label_prefix}Live PnL:</p><h4 style='color:{pnl_color}; margin-top:0;'>{pnl_sign}&#36;{trade_pnl:,.2f} ({pnl_sign}{trade_roi:,.2f}%)</h4>", unsafe_allow_html=True)

# --- HEADER & DATA QUALITY BANNER ---
header_col1, header_col2 = st.columns([5, 1])
with header_col1:
    st.markdown("<h2 style='margin-bottom:0;'>⚡ MICRO EDGE TERMINAL</h2>", unsafe_allow_html=True)
    st.caption("A validated 1-4H Bitcoin signal, backed by real statistical testing — plus live macro context for the bigger picture.")
with header_col2:
    with st.popover("⚙️ Settings"):
        st.markdown("**API Connection**")
        if st.button("🔄 Force Sync"):
            get_telemetry.clear()
            st.rerun()

        st.markdown("<hr style='border:1px solid #333; margin: 12px 0;'>", unsafe_allow_html=True)
        st.caption("Everything below is the research toolkit that validated the Micro Signal, and that keeps testing whether Swing or Macro timeframes ever earn one too. Read-only unless noted -- nothing here silently changes the live formula.")

        st.markdown("**📈 Bootstrap Track Record**")
        st.caption("Seeds Micro's evidence base from real historical BTC price data instead of waiting on live traffic. Every backtested row is tagged separately from live-observed data.")
        bt_months = st.number_input("Months of history", min_value=1, max_value=90, value=24, step=1, key="bt_months")
        if st.button("Run Historical Backtest"):
            with st.spinner("Fetching historical data and reconstructing scores — this can take a minute..."):
                try:
                    bt_resp = requests.post(f"{API_URL}/backtest/run", params={"months": int(bt_months)}, timeout=600)
                    bt_result = bt_resp.json() if bt_resp.status_code == 200 else {"status": "error", "error": f"HTTP {bt_resp.status_code}"}
                except Exception as e:
                    bt_result = {"status": "error", "error": str(e)}
            if bt_result.get("status") == "completed":
                cleared_note = f" (replaced {bt_result['cleared_stale']} stale rows from a prior run)" if bt_result.get("cleared_stale") else ""
                st.success(f"Inserted {bt_result.get('inserted', 0)} backtested rows from {bt_result.get('kline_count', 0)} hourly candles{cleared_note}.")
                get_telemetry.clear()
            elif bt_result.get("status") == "already_running":
                st.warning("A backtest is already running — check back shortly.")
            else:
                st.error(f"Backtest failed: {bt_result.get('error', 'unknown error')}")

        st.markdown("<hr style='border:1px solid #333; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("**🔬 Factor Research**")
        st.caption("Tests each raw input against real forward returns, independently — 16 features (RSI, VWAP divergence, funding, DXY, yields, VIX, S&P, order-flow imbalance, 3/7/14-day momentum, volatility regime, MACD histogram, MA crossover) across 4h/2d/14d. Read-only: never changes the live formula by itself.")
        st.caption("Window goes up to 90 months (Binance BTCUSDT perpetuals have traded since ~2019). Longer windows take proportionally longer to fetch and use more memory -- if a very long run doesn't come back, try a shorter window before assuming something's broken.")
        fr_months = st.number_input("Months of history", min_value=1, max_value=90, value=24, step=1, key="fr_months")
        if st.button("Run Factor Research"):
            with st.spinner("Reconstructing feature history and testing correlations — this can take a minute..."):
                try:
                    fr_resp = requests.post(f"{API_URL}/research/run", params={"months": int(fr_months)}, timeout=600)
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
        st.markdown("**📏 Magnitude Research**")
        st.caption("A different question than Factor Research above: does a feature predict a BIGGER move regardless of direction? Includes near_session_transition — tests whether magnitude clusters around the Asia/London/NY session boundaries the dashboard already tracks.")
        mag_months = st.number_input("Months of history", min_value=1, max_value=90, value=24, step=1, key="mag_months")
        if st.button("Run Magnitude Research"):
            with st.spinner("Reconstructing feature history and testing magnitude correlations — this can take a minute..."):
                try:
                    mag_resp = requests.post(f"{API_URL}/research/run-magnitude", params={"months": int(mag_months)}, timeout=600)
                    mag_result = mag_resp.json() if mag_resp.status_code == 200 else {"status": "error", "error": f"HTTP {mag_resp.status_code}"}
                except Exception as e:
                    mag_result = {"status": "error", "error": str(e)}
            if mag_result.get("status") == "completed" and "error" in mag_result:
                st.error(f"Magnitude research couldn't run: {mag_result['error']}")
            elif mag_result.get("status") == "completed":
                session_feat = mag_result.get("report", {}).get("4h", {}).get("near_session_transition", {})
                non_overlap = session_feat.get("non_overlapping", {})
                if non_overlap.get("significant"):
                    st.success(f"Session-transition timing: r={non_overlap.get('r')} at 4h, n={non_overlap.get('n')} — robust: {session_feat.get('robust')}. Analyzed {mag_result.get('rows_analyzed', 0)} points overall.")
                else:
                    st.info(f"Session-transition timing: r={non_overlap.get('r')} at 4h, not significant at this sample size. Analyzed {mag_result.get('rows_analyzed', 0)} points overall.")
            elif mag_result.get("status") == "already_running":
                st.warning("Magnitude research is already running — check back shortly.")
            else:
                st.error(f"Magnitude research failed: {mag_result.get('error', 'unknown error')}")

        st.markdown("<hr style='border:1px solid #333; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("**⚖️ Calibrate Formula**")
        st.caption("Fits actual regression coefficients for a short, evidence-backed feature list against real forward returns — only pass features that already showed 'robust: true' in Factor Research above. Read-only: shows you the fitted numbers, doesn't rewrite any formula by itself.")
        cal_horizon = st.selectbox("Horizon", ["4h", "2d", "14d"], key="cal_horizon")
        cal_features = st.text_input("Features (comma-separated)", value="vix_pct,spx_pct", key="cal_features")
        cal_months = st.number_input("Months of history", min_value=1, max_value=90, value=24, step=1, key="cal_months")
        if st.button("Run Calibration"):
            with st.spinner("Fitting regression on the non-overlapping sample — this can take a minute..."):
                try:
                    cal_resp = requests.post(
                        f"{API_URL}/research/calibrate",
                        params={"months": int(cal_months), "horizon": cal_horizon, "features": cal_features},
                        timeout=600,
                    )
                    cal_result = cal_resp.json() if cal_resp.status_code == 200 else {"status": "error", "error": f"HTTP {cal_resp.status_code}"}
                except Exception as e:
                    cal_result = {"status": "error", "error": str(e)}
            if cal_result.get("status") == "completed" and "error" in cal_result:
                st.error(f"Calibration couldn't run: {cal_result['error']}")
            elif cal_result.get("status") == "completed":
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

        st.markdown("<hr style='border:1px solid #333; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("**🔬 Out-of-Sample Test**")
        st.caption("A stronger, different check than Calibrate Formula above: fits ONLY on the earlier portion of the window, then tests that frozen formula on the later portion it never saw. Calibrate Formula checks whether a coefficient looks similar when refit on more blended data (replication); this checks whether the formula actually predicts anything on genuinely unseen data (prediction). Out-of-sample R² can come back negative — that's a real result, not an error.")
        oos_horizon = st.selectbox("Horizon", ["4h", "2d", "14d"], key="oos_horizon")
        oos_features = st.text_input("Features (comma-separated)", value="vix_pct,spx_pct", key="oos_features")
        oos_months = st.number_input("Months of history", min_value=1, max_value=90, value=48, step=1, key="oos_months")
        oos_train_frac = st.slider("Train fraction (earlier portion used for fitting)", min_value=0.3, max_value=0.9, value=0.7, step=0.05, key="oos_train_frac")
        if st.button("Run Out-of-Sample Test"):
            with st.spinner("Fitting on the early portion, then testing on the later, unseen portion — this can take a minute..."):
                try:
                    oos_resp = requests.post(
                        f"{API_URL}/research/calibrate-oos",
                        params={"months": int(oos_months), "horizon": oos_horizon, "features": oos_features, "train_frac": oos_train_frac},
                        timeout=600,
                    )
                    oos_result = oos_resp.json() if oos_resp.status_code == 200 else {"status": "error", "error": f"HTTP {oos_resp.status_code}"}
                except Exception as e:
                    oos_result = {"status": "error", "error": str(e)}
            if oos_result.get("status") == "completed" and "error" in oos_result:
                st.error(f"Out-of-sample test couldn't run: {oos_result['error']}")
            elif oos_result.get("status") == "completed":
                st.session_state["last_oos_result"] = oos_result
                oos_data = oos_result.get("out_of_sample_result", {})
                if "error" in oos_data:
                    st.warning(f"Couldn't evaluate held-out set: {oos_data['error']}")
                else:
                    r2 = oos_data.get("out_of_sample_r_squared")
                    st.success(f"Trained on {oos_result.get('train_window_size')} windows, tested on {oos_result.get('test_window_size')} unseen windows — out-of-sample R²={r2}")
            elif oos_result.get("status") == "already_running":
                st.warning("An out-of-sample test is already running — check back shortly.")
            else:
                st.error(f"Out-of-sample test failed: {oos_result.get('error', 'unknown error')}")

        st.markdown("<hr style='border:1px solid #333; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("**🎯 Direction × Magnitude Joint Study**")
        st.caption("Tests whether Micro's real win rate genuinely differs between elevated and normal Volatility Guardrail regimes — the direct evidence for or against combining direction and magnitude into one metric, tested empirically rather than assumed from intuition.")
        joint_months = st.number_input("Months of history", min_value=1, max_value=90, value=24, step=1, key="joint_months")
        if st.button("Run Joint Study"):
            with st.spinner("Reconstructing direction and magnitude jointly across history — this can take a minute..."):
                try:
                    joint_resp = requests.post(f"{API_URL}/research/run-joint-study", params={"months": int(joint_months)}, timeout=600)
                    joint_result = joint_resp.json() if joint_resp.status_code == 200 else {"status": "error", "error": f"HTTP {joint_resp.status_code}"}
                except Exception as e:
                    joint_result = {"status": "error", "error": str(e)}
            if joint_result.get("status") == "completed" and "error" in joint_result:
                st.error(f"Joint study couldn't run: {joint_result['error']}")
            elif joint_result.get("status") == "completed":
                bull_test = joint_result.get("bullish_elevated_vs_normal", {})
                bear_test = joint_result.get("bearish_elevated_vs_normal", {})
                bull_status, bear_status = bull_test.get("status"), bear_test.get("status")
                if bull_status == "elevated_regime_stronger" or bear_status == "elevated_regime_stronger":
                    st.success(f"Real evidence found — Bullish: {bull_status} (z={bull_test.get('z_score')}), Bearish: {bear_status} (z={bear_test.get('z_score')})")
                elif bull_status == "insufficient_data" and bear_status == "insufficient_data":
                    st.warning("Not enough elevated-regime samples yet at this window length — try a longer history.")
                else:
                    st.info(f"No significant difference found — Bullish: {bull_status} (z={bull_test.get('z_score')}), Bearish: {bear_status} (z={bear_test.get('z_score')}). Honest null result, not an error.")
            elif joint_result.get("status") == "already_running":
                st.warning("A joint study is already running — check back shortly.")
            else:
                st.error(f"Joint study failed: {joint_result.get('error', 'unknown error')}")

        st.markdown("<hr style='border:1px solid #333; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("**🌊 CVD Absorption vs Momentum**")
        st.caption("Tests two signatures of heavy one-sided order flow: momentum (flow that moved price roughly proportionally) vs absorption (heavy flow, price barely moved — a large passive counterparty likely absorbed it). Does momentum tend to continue while absorption tends to reverse?")
        cvd_months = st.number_input("Months of history", min_value=1, max_value=90, value=24, step=1, key="cvd_months")
        if st.button("Run CVD Study"):
            with st.spinner("Reconstructing order flow and price action jointly across history — this can take a minute..."):
                try:
                    cvd_resp = requests.post(f"{API_URL}/research/run-cvd-study", params={"months": int(cvd_months)}, timeout=600)
                    cvd_result = cvd_resp.json() if cvd_resp.status_code == 200 else {"status": "error", "error": f"HTTP {cvd_resp.status_code}"}
                except Exception as e:
                    cvd_result = {"status": "error", "error": str(e)}
            if cvd_result.get("status") == "completed" and "error" in cvd_result:
                st.error(f"CVD study couldn't run: {cvd_result['error']}")
            elif cvd_result.get("status") == "completed":
                sig = cvd_result.get("momentum_vs_absorption", {})
                status = sig.get("status")
                mom, abso = cvd_result.get("momentum", {}), cvd_result.get("absorption", {})
                if status in ("momentum_continues_more", "absorption_continues_more"):
                    st.success(f"Real evidence found — {status} (z={sig.get('z_score')}). Momentum continuation: {mom.get('continuation_rate_pct')}% (n={mom.get('n')}), Absorption continuation: {abso.get('continuation_rate_pct')}% (n={abso.get('n')})")
                elif status == "insufficient_data":
                    st.warning("Not enough heavy-flow samples yet at this window length — try a longer history.")
                else:
                    st.info(f"No significant difference found (z={sig.get('z_score')}). Honest null result, not an error.")
            elif cvd_result.get("status") == "already_running":
                st.warning("A CVD study is already running — check back shortly.")
            else:
                st.error(f"CVD study failed: {cvd_result.get('error', 'unknown error')}")

        st.markdown("<hr style='border:1px solid #333; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("**⚡ Minute-Resolution Spike & Reversion**")
        st.caption("A different data RESOLUTION than every other tool above, not a new combination of the same hourly features -- tests whether a large, fast (5-min) price move tends to partially reverse in the following 15 minutes. Deliberately capped at a much smaller window than the hourly tools (1-minute data is ~60x denser per day) and tested against an empirical shuffle-test baseline, not a naive 50/50 -- a naive baseline was tried first and produced false positives on pure noise.")
        spike_days = st.number_input("Days of history", min_value=1, max_value=90, value=30, step=1, key="spike_days")
        if st.button("Run Spike & Reversion Study"):
            with st.spinner("Fetching minute-level data and running the shuffle-test baseline — this can take a minute or two..."):
                try:
                    spike_resp = requests.post(f"{API_URL}/research/run-spike-study", params={"days": int(spike_days)}, timeout=600)
                    spike_result = spike_resp.json() if spike_resp.status_code == 200 else {"status": "error", "error": f"HTTP {spike_resp.status_code}"}
                except Exception as e:
                    spike_result = {"status": "error", "error": str(e)}
            if spike_result.get("status") == "completed" and "error" in spike_result:
                st.error(f"Spike study couldn't run: {spike_result['error']}")
            elif spike_result.get("status") == "completed":
                sig = spike_result.get("significance", {})
                status = sig.get("status")
                observed = spike_result.get("observed_reversion_rate_pct")
                null_mean = spike_result.get("null_distribution_mean_pct")
                n_events = spike_result.get("total_events")
                if status in ("spikes_revert_more_than_baseline", "spikes_revert_less_than_baseline"):
                    st.success(f"Real evidence found — {status} (z={sig.get('z_score')}). Observed reversion: {observed}% vs shuffle-test baseline: {null_mean}% (n={n_events} events, {spike_result.get('n_shuffles')} shuffles)")
                elif status == "insufficient_data" or "error" in spike_result:
                    st.warning("Not enough spike events or shuffle data at this window length — try more days.")
                else:
                    st.info(f"No significant difference found — observed {observed}% vs baseline {null_mean}% (z={sig.get('z_score')}). Honest null result, not an error.")
            elif spike_result.get("status") == "already_running":
                st.warning("A spike study is already running — check back shortly.")
            else:
                st.error(f"Spike study failed: {spike_result.get('error', 'unknown error')}")

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

# ==========================================
# MARKET OVERVIEW — leads the page: the basic live numbers before anything
# else, so there's context before the signal.
# ==========================================
render_header("📊 Live Market Overview")
deltas = telemetry.get("deltas", {})
with st.container(border=True):
    ov_r1c1, ov_r1c2, ov_r1c3, ov_r1c4 = st.columns(4)
    spot_delta = deltas.get("spot_pct_24h")
    ov_r1c1.metric("Live Spot", f"${LIVE_SPOT_PRICE:,.2f}",
                    delta=f"{spot_delta:+.2f}% (24h)" if spot_delta is not None else None)
    rsi_delta = deltas.get("rsi_1h")
    ov_r1c2.metric("RSI(14, Wilder)", f"{ta.get('rsi', 50.0):.1f}",
                    delta=f"{rsi_delta:+.1f} (1h)" if rsi_delta is not None else None,
                    help="Momentum on a 0–100 scale. See the Glossary below for how to read it.")
    vwap_delta = deltas.get("vwap_1h_pct")
    ov_r1c3.metric("Session VWAP (UTC)", f"${ta.get('vwap', LIVE_SPOT_PRICE):,.2f}",
                    delta=f"{vwap_delta:+.3f}% (1h)" if vwap_delta is not None else None,
                    help="Volume-weighted average price since 00:00 UTC. Price above this line is generally read as buyers in control.")
    oi_delta = deltas.get("oi_1h_pct")
    ov_r1c4.metric("Open Interest", OPEN_INTEREST,
                    delta=f"{oi_delta:+.2f}% (1h)" if oi_delta is not None else None,
                    help="Total outstanding futures contracts. Rising OI with a price move suggests new money entering the trend.")

# --- Wall/CVD reference values, used by Volatility Guardrail, the price
# chart, and the heatmap further down. ---
hm_data = telemetry.get("orderbook_heatmap", {})
upper_wall = hm_data.get("upper_wall", 65411) if hm_data else 65411
lower_wall = hm_data.get("lower_wall", 61582) if hm_data else 61582
ny_cvd_raw = telemetry.get("session_cvd", {}).get("new_york", {}).get("cvd", "")

# ==========================================
# MICRO SIGNAL — the headline of this tool. The one tier with a validated,
# calibrated, out-of-sample-tested edge (see Settings -> Out-of-Sample
# Test for the actual proof). Carries its own evidence -- significance
# test, per-bucket win rates, sample sizes -- so it's a complete,
# self-contained case for why this specific number should be trusted at
# all, not just a score with no receipts.
# ==========================================
render_header("🎯 Micro Signal (1-4 HRS)")
with st.container(border=True):
    st.caption("Calibrated regression on VIX + S&P 500 (real fit, n=4,313 non-overlapping windows, R²=0.023, confirmed via independent out-of-sample testing) — RSI and VWAP divergence were tested and dropped after showing no significant edge at this horizon. R²=0.023 is a small, real, repeatable statistical tilt, not a strong individual prediction — the evidence below shows what an edge this size looks like in realized outcomes.")
    micro_dir = insights.get('rationales', {}).get('micro_directive', '⏳ NEUTRAL / CHOP')
    if "🟢" in micro_dir: bias_badge(micro_dir, "bullish")
    elif "🔴" in micro_dir: bias_badge(micro_dir, "bearish")
    else: bias_badge(micro_dir, "neutral")
    st.metric("Micro Score", f"{micro_score} / 100")
    micro_rat = insights.get('rationales', {}).get('micro', 'Awaiting live data...')
    st.caption(f"**Rationale:** {micro_rat}")

    st.markdown("<hr style='border:0.5px solid #333; margin: 16px 0;'>", unsafe_allow_html=True)
    st.markdown("**📊 Evidence — Does This Signal Actually Work?**")

    micro_evidence = telemetry.get("micro_evidence", {})
    sig = micro_evidence.get("significance", {})
    sig_status = sig.get("status")
    min_n = telemetry.get("micro_sizing_guide", {}).get("min_sample_size", 20)

    if sig_status in (None, "insufficient_data"):
        # Not enough logged history yet to compute real significance --
        # sig_status only leaves "insufficient_data" when at least one of
        # the bullish/bearish buckets still lacks enough sample, which
        # means the bucket grid below would ALSO be mostly placeholders.
        # This instance's score_history resets on every redeploy (Render's
        # free-tier disk is ephemeral), so this state is common right after
        # shipping changes. One honest, actionable line beats a grid of
        # "still collecting" placeholders across four separate UI elements,
        # which reads as broken rather than as a tool honestly waiting on data.
        status_card(
            "⏳ <b>Evidence is still accumulating for this instance</b> — likely because recent updates reset "
            "the tracking history (Render's free-tier disk wipes on redeploy). Run a historical backtest from "
            "Settings to populate this instantly from real past data, or check back once more live activity "
            "has logged.", "info",
        )
    else:
        if sig_status == "significant_edge":
            bias_badge(f"✓ Validated edge (z={sig.get('z_score')})", "bullish")
        elif sig_status == "inverted_edge":
            bias_badge(f"⚠ Inverted (z={sig.get('z_score')}) — check formula", "conflict")
        else:
            bias_badge(f"No confirmed edge yet (z={sig.get('z_score')})", "neutral")

        buckets = micro_evidence.get("buckets", {})
        ev_cols = st.columns(3)
        for i, (bucket_key, bucket_label) in enumerate([("bullish", "When Bullish"), ("bearish", "When Bearish"), ("neutral", "When Neutral")]):
            with ev_cols[i]:
                b = buckets.get(bucket_key, {})
                n = b.get("n", 0)
                live_n, bt_n = b.get("live_n", 0), b.get("backtest_n", 0)
                src_note = f"{live_n} live, {bt_n} backtest" if bt_n else f"{live_n} live"
                if not b.get("sufficient_sample"):
                    st.caption(f"**{bucket_label}**\n\nn={n} ({src_note}) — still collecting (need {min_n})")
                else:
                    avg_r = b.get("avg_return_pct")
                    pct_pos = b.get("pct_positive")
                    sign = "+" if avg_r is not None and avg_r >= 0 else ""
                    st.caption(f"**{bucket_label}**\n\navg {sign}{avg_r}% · {pct_pos}% positive · n={n} ({src_note})")

        if sig_status == "inverted_edge":
            status_card(
                "⚠️ <b>Statistically significant INVERTED relationship</b> — the bias label and the actual "
                "historical outcome point opposite directions. Treat the badge above with extra caution until "
                "the formula is revisited.", "conflict",
            )

    st.markdown("<hr style='border:0.5px solid #333; margin: 16px 0;'>", unsafe_allow_html=True)
    sizing = telemetry.get("micro_sizing_guide", {})
    sz_col1, sz_col2 = st.columns(2)
    if sizing.get("available"):
        kelly_display = f"{sizing['quarter_kelly_pct']:.2f}%"
        sizing_help = (
            f"Based on {sizing['sample_size']} historical Micro-{sizing.get('current_bucket', 'neutral').title()} "
            f"readings on this instance: {sizing['win_rate_pct']:.0f}% ended positive, avg win +{sizing['avg_win_pct']:.2f}%, "
            f"avg loss -{sizing['avg_loss_pct']:.2f}%. Quarter-Kelly of that edge is shown. Still a small, "
            f"instance-specific sample, not a professionally validated figure -- not investment advice."
        )
    else:
        n = sizing.get("sample_size", 0)
        kelly_display = f"Collecting ({n}/{min_n})"
        sizing_help = f"Not enough history yet for Micro-{sizing.get('current_bucket', 'neutral').title()} readings to estimate a real edge ({n} of {min_n} needed). Run a historical backtest from Settings to bootstrap this quickly, or check back once more live readings like this one have accumulated."
    sz_col1.metric("Sizing Guide*", kelly_display, help=sizing_help)
    st.caption("*Quarter-Kelly sizing grounded in this instance's own empirical Micro track record (real observed win rate and avg win/loss) — not a formula-derived guess. Still a small, instance-specific sample; not investment advice.")

# ==========================================
# VOLATILITY GUARDRAIL — built from what Magnitude Research actually
# validated at 4h (Micro's horizon), not from an assumption. THREE signals
# robustly predicted bigger subsequent moves on n=2,153 independent
# windows: ATR (r=+0.263), 24h momentum extremity (r=+0.172), and VIX
# extremity (r=+0.163) -- the strongest, most trustworthy results in that
# whole test. This is a magnitude warning, not a direction call: it says
# "expect a bigger swing," not "expect it to go up or down."
# ==========================================
atr_pct_val = ta.get("atr_pct", 0.01)
vix_pct_val = plumbing.get("vix", {}).get("pct_change", 0.0) if isinstance(plumbing.get("vix"), dict) else 0.0
momentum_24h_val = telemetry.get("deltas", {}).get("spot_pct_24h") or 0.0

atr_elevated = atr_pct_val > 0.015
vix_elevated = abs(vix_pct_val) > 3.0
momentum_elevated = abs(momentum_24h_val) > 4.0
elevated_count = sum([atr_elevated, vix_elevated, momentum_elevated])

elevated_labels = []
if atr_elevated: elevated_labels.append(f"ATR {atr_pct_val*100:.2f}%")
if vix_elevated: elevated_labels.append(f"VIX {vix_pct_val:+.2f}%")
if momentum_elevated: elevated_labels.append(f"24h move {momentum_24h_val:+.2f}%")

if elevated_count >= 2:
    status_card(f"🌪️ <b>High Volatility Regime</b> · {elevated_count} of 3 validated signals elevated: {', '.join(elevated_labels)} · All three (ATR r=+0.263, 24h momentum r=+0.172, VIX r=+0.163, all robust on n=2,153) predicted bigger 4h moves. Expect wider swings in either direction; size and stops accordingly, not just directional bias.", "conflict")
elif elevated_count == 1:
    status_card(f"⚠️ <b>Elevated Volatility Signal</b> · {elevated_labels[0]} · A validated 4h magnitude predictor on its own. Bigger-than-usual moves are somewhat more likely in either direction over the next few hours.", "neutral")
else:
    status_card(f"✅ <b>Normal Volatility Regime</b> · 1H ATR: {atr_pct_val*100:.2f}% · VIX move: {vix_pct_val:+.2f}% · 24h move: {momentum_24h_val:+.2f}% · None of the three validated magnitude signals are elevated right now.", "info")

# ==========================================
# PRICE CHART
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
        st.caption("Real hourly candles from Binance. VWAP and liquidity walls are the same live levels referenced throughout this page — this is where they actually are relative to price.")

with st.expander("📖 Glossary — What These Terms Mean"):
    st.markdown("""
- **RSI (Relative Strength Index)**: measures how fast and how far price has moved recently, on a 0–100 scale. Above ~70 is often called "overbought," below ~30 "oversold" — but in a strong trend it can stay extreme for a while, so it's a momentum gauge, not a timing signal on its own.
- **VWAP (Volume-Weighted Average Price)**: the average price paid so far this session, weighted by how much volume traded at each price. Traders use it as a reference line — price above VWAP is generally read as buyers in control, below as sellers in control.
- **Funding Rate**: a periodic payment between long and short perpetual-futures traders that keeps the futures price tethered to spot. Persistently positive funding means longs are paying shorts (crowded long positioning); negative means the reverse.
- **Open Interest (OI)**: the total number of outstanding futures/options contracts that haven't been closed. Rising OI alongside a price move suggests new money entering the trend; falling OI suggests positions closing out.
- **CVD (Cumulative Volume Delta)**: running total of aggressive buy volume minus aggressive sell volume. Positive CVD means market buy orders are outweighing market sells.
- **Liquidity Heatmap / Order Book Walls**: visualizes where large buy or sell orders are sitting in the order book. Thick clusters ("walls") are levels the market has to absorb to keep moving through.
- **Implied Volatility (IV) Skew**: how options-market-priced volatility differs across strike prices for a given expiry. A steep skew toward downside strikes usually reflects more hedging demand against a drop.
- **Network Activity**: real, live Bitcoin network data (mempool backlog, fee pressure) — a proxy for on-chain demand, not exchange-specific buying/selling flow (that requires a paid data provider this app doesn't currently use).
- **Out-of-Sample Testing**: fitting a formula on only part of the historical data, then checking whether it actually predicts the remaining part it never saw. The strongest check this tool has for telling a real relationship apart from one that just happened to fit its own training data.
""")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# CONFLUENCE BOARD — at-a-glance market conditions for beginners, not a
# trading directive. Micro (4h, above) remains the only VALIDATED,
# calibrated trading-bias source on this dashboard -- this board is a
# different thing: it organizes real, live macro/market inputs with an
# honest lean per factor and an aggregate read, so someone can see
# "conditions look broadly supportive/mixed/unsupportive right now"
# without either (a) reading six raw numbers and guessing what they mean
# together, or (b) being told what to do about it.
# ==========================================
confluence = telemetry.get("confluence_board")
if confluence:
    render_header("🧭 Confluence Board — Conditions at a Glance")
    st.caption("Six real, live inputs to Bitcoin's broader backdrop, each with an honest lean — this is NOT a trading signal for Swing/Macro timeframes. We tested composite scores like this against ~2 years of real data and found no reliable directional edge (see Factor Research in Settings). Micro (above) is the only tier with a validated, tested edge right now. Think of this as 'here's the weather,' not 'here's the trade.'")

    b, r, n = confluence.get("bullish_count", 0), confluence.get("bearish_count", 0), confluence.get("neutral_count", 0)
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=[b], y=[""], orientation="h", marker_color="#00E676", name="Bullish",
                              text=f"{b} Bullish" if b else "", textposition="inside", insidetextanchor="middle",
                              textfont=dict(color="#0A0E17", size=13)))
    fig_bar.add_trace(go.Bar(x=[n], y=[""], orientation="h", marker_color="#8892B0", name="Neutral",
                              text=f"{n} Neutral" if n else "", textposition="inside", insidetextanchor="middle",
                              textfont=dict(color="#0A0E17", size=13)))
    fig_bar.add_trace(go.Bar(x=[r], y=[""], orientation="h", marker_color="#FF3366", name="Bearish",
                              text=f"{r} Bearish" if r else "", textposition="inside", insidetextanchor="middle",
                              textfont=dict(color="#0A0E17", size=13)))
    fig_bar.update_layout(
        barmode="stack", height=70, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
        xaxis=dict(visible=False, range=[0, b + n + r]), yaxis=dict(visible=False),
    )
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    scenario_kind_map = {
        "strong_bullish": "bullish", "strong_bearish": "bearish",
        "moderate_bullish": "bullish", "moderate_bearish": "bearish",
        "split": "conflict", "quiet": "neutral",
    }
    scenario_kind = scenario_kind_map.get(confluence.get("scenario"), "info")
    status_card(
        f"{confluence.get('scenario_icon', '')} <b>{confluence.get('scenario_label', '')}</b><br>{confluence.get('scenario_summary', '')}",
        scenario_kind,
    )
    with st.expander("Read the full explanation of this pattern"):
        st.markdown(confluence.get("scenario_explanation", ""))

    lean_badge_kind = {"bullish": "bullish", "bearish": "bearish", "neutral": "neutral"}
    factor_cols = st.columns(3)
    for i, factor in enumerate(confluence.get("factors", [])):
        with factor_cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{factor['label']}**")
                bias_badge(f"{factor['value_str']} · {factor['lean'].title()}", lean_badge_kind.get(factor['lean'], "neutral"))
                st.caption(factor["explanation"])

    st.caption(confluence.get("disclaimer", ""))

# ==========================================
# ECONOMIC CALENDAR — real, publicly-scheduled CPI and FOMC dates, with
# generic educational context. Same honesty rule as the rest of Confluence
# Board: dates and release mechanics are facts, "how markets have tended
# to react" is general historical framing, NOT a claim we've specifically
# tested for BTC.
# ==========================================
econ_cal = telemetry.get("economic_calendar")
if econ_cal:
    render_header("📅 Economic Calendar — CPI & FOMC")
    st.caption("Real, publicly-scheduled dates from the Federal Reserve and Bureau of Labor Statistics — not a prediction of what the reports will say, and not a trading signal. See the note below.")

    cal_col1, cal_col2 = st.columns(2)
    with cal_col1:
        with st.container(border=True):
            st.markdown("**📊 Next CPI Release**")
            next_cpi = econ_cal.get("next_cpi", {})
            if next_cpi.get("date"):
                st.metric("Date", next_cpi["date"], help=f"Releases at {next_cpi.get('time_et', '8:30 AM ET')}")
                days = next_cpi.get("days_until")
                if days == 0:
                    st.caption("📍 That's today.")
                elif days is not None:
                    st.caption(f"{days} day{'s' if days != 1 else ''} away.")
            else:
                st.warning(next_cpi.get("note", "No upcoming date on file."))
            st.caption(econ_cal.get("cpi_education", ""))

    with cal_col2:
        with st.container(border=True):
            st.markdown("**🏛️ Next FOMC Meeting**")
            next_fomc = econ_cal.get("next_fomc", {})
            if next_fomc.get("date"):
                dot_plot_note = " (includes the dot plot)" if next_fomc.get("has_dot_plot") else ""
                st.metric("Statement Date", next_fomc["date"] + dot_plot_note, help=next_fomc.get("time_et", ""))
                days = next_fomc.get("days_until")
                if days == 0:
                    st.caption("📍 That's today.")
                elif days is not None:
                    st.caption(f"{days} day{'s' if days != 1 else ''} away.")
            else:
                st.warning(next_fomc.get("note", "No upcoming date on file."))
            st.caption(econ_cal.get("fomc_education", ""))

    st.caption(f"Dates last verified {econ_cal.get('last_verified', 'N/A')} against federalreserve.gov and bls.gov. " + econ_cal.get("disclaimer", ""))

# ==========================================
# TELEMETRY & LIQUIDITY — supporting real market data
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

                teal_colorscale = [
                    [0.0, "#0A0E17"],
                    [0.20, "#0F2A3D"],
                    [0.45, "#0E7490"],
                    [0.70, "#00C2CC"],
                    [0.88, "#26FFDE"],
                    [1.0, "#F0FFFC"],
                ]

                tick_idx = list(range(0, len(time_steps), 5)) if time_steps else []
                tick_vals = [time_steps[i] for i in tick_idx]

                fig_heatmap = go.Figure(data=go.Heatmap(
                    z=z_array, x=time_steps if time_steps else None, y=prices if prices else None,
                    colorscale=teal_colorscale, showscale=True, zmin=0.0, zmax=z_max,
                    zsmooth=False,
                    hovertemplate="Price: $%{y:,.0f}<br>Depth: %{z:.2f}<br>%{x}<extra></extra>",
                    colorbar=dict(title=dict(text="Depth", font=dict(color="#8892B0")), thickness=12, len=0.8, tickfont=dict(color="#8892B0")),
                    xgap=1, ygap=1,
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
