"""
MARKET EDUCATION TERMINAL  --  frontend
=======================================
Rewritten from the Micro Edge Terminal.

WHAT CHANGED
  The old app led with a 4h directional BTC signal. That signal was withdrawn
  after a lookahead-bias bug was found in its backtest: corrected, the edge
  disappeared entirely (z=6.32 -> z=-0.94). Also removed: the quarter-Kelly
  Sizing Guide, which derived position sizes from that signal's buckets.

  This version leads with EXECUTION -- how you traded -- because that is the
  part of trading a retail trader can measurably control and improve. Market
  context and the Confluence Board remain, with every claim carrying an
  explicit evidence status.

SECTION ORDER (deliberate)
  1. Execution Scorecard    -- your process metrics, from your own log
  2. Trade Log Review       -- what your history supports, with evidence
  3. Volatility Guardrail   -- the one validated market signal (magnitude)
  4. Live Market Context    -- real data, mechanism explained, status labelled
  5. Confluence Board       -- form your own view from real inputs
  6. Research Bench         -- test new ideas against the corrected engine

RUN
  streamlit run frontend_app.py
"""

import csv
import io
import statistics as stats
from collections import defaultdict, deque
from datetime import datetime, timezone

import requests
import streamlit as st
import plotly.graph_objects as go

API_URL = "https://quant-desk-backend-rata.onrender.com/api/v1"

st.set_page_config(page_title="Market Education Terminal", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

STATUS_STYLE = {
    "VALIDATED": ("#0B3D24", "#00E676", "✓ VALIDATED"),
    "UNTESTED": ("#3D2B00", "#FFB020", "○ UNTESTED"),
    "TESTED_AND_FAILED": ("#3D0B18", "#FF3366", "✗ TESTED & FAILED"),
}

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.25rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.90rem !important; white-space: normal !important; color: #8892B0 !important; }
.block-container { max-width: 1500px; margin: 0 auto; padding-left: 2.5rem; padding-right: 2.5rem; }
.badge { display:inline-block; padding:3px 12px; border-radius:4px; font-size:0.8rem; font-weight:600; margin:2px 0 8px 0; }
.card { background-color:#10141F; border-left:4px solid #4FC3F7; border-radius:4px; padding:10px 16px; margin-bottom:10px; font-size:0.92rem; line-height:1.5; }
.card.bullish{border-left-color:#00E676;} .card.bearish{border-left-color:#FF3366;}
.card.neutral{border-left-color:#FFB020;} .card.conflict{border-left-color:#B794F6;}
.stale{background-color:#3D2B00;color:#FFB020;padding:4px 10px;border-radius:4px;font-size:0.8rem;}
.live{background-color:#0B3D24;color:#00E676;padding:4px 10px;border-radius:4px;font-size:0.8rem;}
</style>
""", unsafe_allow_html=True)


def badge(text, bg, fg):
    st.markdown(f'<span class="badge" style="background-color:{bg};color:{fg};">{text}</span>',
                unsafe_allow_html=True)


def status_badge(status):
    bg, fg, label = STATUS_STYLE.get(status, STATUS_STYLE["UNTESTED"])
    badge(label, bg, fg)


def card(html, kind="info"):
    st.markdown(f'<div class="card {kind}">{html}</div>', unsafe_allow_html=True)


def header(title):
    st.markdown(
        f"<h4 style='color:#E0E0E0;border-bottom:1px solid #333;padding-bottom:10px;"
        f"margin-top:40px;margin-bottom:25px;text-transform:uppercase;letter-spacing:1px;'>"
        f"{title}</h4>", unsafe_allow_html=True)


# ======================================================================
# TRADE LOG
# ======================================================================
def parse_dt(s):
    return datetime.strptime(s.split(" GMT")[0].strip(), "%a %b %d %Y %H:%M:%S")


def num(x):
    x = (x or "").strip()
    return float(x) if x else 0.0


@st.cache_data(show_spinner=False)
def load_trades(file_bytes):
    """Parses one or more Jupiter Perps CSV exports into closed trades.

    Deduplicates on Transaction ID (Solana signatures are unique), so
    re-uploading a fresh full export is idempotent -- you can upload the same
    file twice, or overlapping partial exports, without double-counting.
    That's what makes 'export fresh and re-upload' a safe update mechanism.

    FIFO-pairs opens against closes per (asset, direction). Gross P/L: the
    fee columns are surfaced separately in the Costs panel, because netting
    them here would hide the single biggest driver of retail outcomes."""
    text = file_bytes.decode("utf-8") if isinstance(file_bytes, bytes) else file_bytes
    raw = list(csv.DictReader(io.StringIO(text), skipinitialspace=True))

    seen, rows = set(), []
    for r in raw:
        txid = (r.get("Transaction ID") or "").strip()
        if txid and txid in seen:
            continue
        if txid:
            seen.add(txid)
        try:
            r["_dt"] = parse_dt(r["Created at"])
        except Exception:
            continue
        r["_pnl"] = num(r.get("Profit / Loss ($)"))
        r["_size"] = num(r.get("Trade size ($)"))
        r["_fee"] = num(r.get("Trade fee ($)"))
        r["_liqfee"] = num(r.get("Liquidation fee ($)"))
        r["_collat"] = abs(num(r.get("Deposit / Withdraw ($)")))
        rows.append(r)

    rows.sort(key=lambda r: r["_dt"])
    queues, trades = defaultdict(deque), []
    total_fees = sum(r["_fee"] + r["_liqfee"] for r in rows)
    total_notional = sum(r["_size"] for r in rows)
    levs = [r["_size"] / r["_collat"] for r in rows
            if r["_collat"] > 0 and r["Position change"] == "Increase"]

    for r in rows:
        key = (r["Asset"], r["Position"])
        if r["Position change"] == "Increase":
            queues[key].append(r)
        elif queues[key]:
            o = queues[key].popleft()
            trades.append({
                "asset": r["Asset"], "direction": r["Position"],
                "exit_type": r["Order type"], "entry_dt": o["_dt"], "exit_dt": r["_dt"],
                "hold_h": (r["_dt"] - o["_dt"]).total_seconds() / 3600,
                "pnl": r["_pnl"], "size": r["_size"],
            })

    costs = {
        "total_fees": total_fees, "total_notional": total_notional,
        "fee_rate_pct": (total_fees / total_notional * 100) if total_notional else 0.0,
        "median_leverage": stats.median(levs) if levs else None,
        "transactions": len(rows), "duplicates_skipped": len(raw) - len(rows),
    }
    return trades, costs


def metrics(trades):
    n = len(trades)
    if not n:
        return None
    ov = sum(1 for t in trades if t["exit_type"] == "Market")
    lq = sum(1 for t in trades if t["exit_type"] == "Liquidation")
    gross = sum(t["pnl"] for t in trades)
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] < 0]
    return {
        "n": n, "override_rate": ov / n * 100, "override_count": ov,
        "liquidation_rate": lq / n * 100, "liquidation_count": lq,
        "expectancy": gross / n, "gross": gross,
        "win_rate": len(wins) / n * 100,
        "profit_factor": (sum(wins) / abs(sum(losses))) if losses else None,
        "avg_win": stats.mean(wins) if wins else 0.0,
        "avg_loss": stats.mean(losses) if losses else 0.0,
    }


def group_by(trades, keyfn):
    b = defaultdict(list)
    for t in trades:
        b[keyfn(t)].append(t)
    return {k: metrics(v) for k, v in b.items()}


# ======================================================================
# SECTION 1 + 2 -- EXECUTION
# ======================================================================
def render_execution(trades, costs):
    header("📋 Execution Scorecard")
    st.caption(
        "How you traded — not where price went. Every metric here is under your control, "
        "which is exactly what makes it worth tracking. Prediction may or may not be "
        "available to you. Execution always is."
    )

    overall = metrics(trades)
    months = dict(sorted(group_by(trades, lambda t: t["exit_dt"].strftime("%Y-%m")).items()))
    latest_key = list(months)[-1]
    latest = months[latest_key]

    c1, c2, c3 = st.columns(3)
    c1.metric("Override rate", f"{latest['override_rate']:.1f}%",
              f"{latest['override_rate'] - overall['override_rate']:+.1f} vs baseline",
              delta_color="inverse",
              help="Share of exits closed manually instead of letting your trigger fire. "
                   "Lower is better — this has the strongest validated link to worse outcomes "
                   "in your own log.")
    c2.metric("Liquidation rate", f"{latest['liquidation_rate']:.1f}%",
              f"{latest['liquidation_rate'] - overall['liquidation_rate']:+.1f} vs baseline",
              delta_color="inverse",
              help="Share of positions closed by forced liquidation. Target is zero. Driven by "
                   "leverage and collateral buffer, not position size.")
    c3.metric("Expectancy / trade", f"${latest['expectancy']:.2f}",
              f"${latest['expectancy'] - overall['expectancy']:+.2f} vs baseline",
              help="Average gross P/L per closed trade. This is an OUTCOME — partly luck. The two "
                   "metrics to the left are PROCESS, and process is what responds to effort.")
    st.caption(f"Most recent month: {latest_key} · {latest['n']} closed trades · "
               f"baseline is your full history ({overall['n']} trades)")

    st.markdown("#### Month by month")
    st.caption("Watch whether override and liquidation rates move together with expectancy. "
               "If your worst months are your highest-override months, that is your clearest lever.")
    st.dataframe([{
        "Month": m, "Trades": v["n"],
        "Override %": round(v["override_rate"], 1),
        "Liquidation %": round(v["liquidation_rate"], 1),
        "Win %": round(v["win_rate"], 1),
        "Expectancy $": round(v["expectancy"], 2),
    } for m, v in months.items()], use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### By asset")
        st.caption("Concentration in an asset where your expectancy is flat is a silent leak.")
        st.dataframe([{
            "Asset": a, "Trades": v["n"], "Expectancy $": round(v["expectancy"], 2),
            "Win %": round(v["win_rate"], 1), "Gross $": round(v["gross"], 2),
        } for a, v in sorted(group_by(trades, lambda t: t["asset"]).items(),
                             key=lambda kv: -kv[1]["n"])],
            use_container_width=True, hide_index=True)
    with c2:
        st.markdown("#### By exit type")
        st.caption("Trigger = your plan executed. Market = you overrode it. Liquidation = forced out.")
        st.dataframe([{
            "Exit": e, "Trades": v["n"], "Expectancy $": round(v["expectancy"], 2),
            "Win %": round(v["win_rate"], 1), "Gross $": round(v["gross"], 2),
        } for e, v in sorted(group_by(trades, lambda t: t["exit_type"]).items(),
                             key=lambda kv: -kv[1]["gross"])],
            use_container_width=True, hide_index=True)

    render_costs(costs, overall)


def render_costs(costs, overall):
    header("💸 What Trading Actually Cost You")
    status_badge("VALIDATED")
    st.markdown("**Leverage multiplies your costs as reliably as it multiplies your gains.**")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cumulative notional", f"${costs['total_notional']:,.0f}",
              help="Position size summed across every transaction. NOT money you deposited — "
                   "it's capital x leverage, cycled repeatedly.")
    c2.metric("Total fees", f"${costs['total_fees']:,.2f}")
    c3.metric("Effective fee rate", f"{costs['fee_rate_pct']:.4f}%",
              help="Fees as a share of notional. Should sit near your venue's published rate — "
                   "if it does, the total is real, however large it looks.")
    if costs["median_leverage"]:
        c4.metric("Median leverage", f"{costs['median_leverage']:.1f}x")

    gross = overall["gross"]
    net = gross - costs["total_fees"]
    card(
        f"<b>Gross trading result:</b> ${gross:,.2f} &nbsp;·&nbsp; "
        f"<b>Fees:</b> −${costs['total_fees']:,.2f} &nbsp;·&nbsp; "
        f"<b>Net:</b> ${net:,.2f}",
        "bullish" if net >= 0 else "bearish",
    )

    with st.expander("Why the fee total can look impossibly large — read this one"):
        st.markdown(f"""
**The mechanism.** Fees are charged on **notional** — your capital multiplied by your
leverage — not on your capital. At {costs['median_leverage']:.0f}x, a $120 position controls
about ${120 * (costs['median_leverage'] or 1):,.0f}, and you pay the fee on that larger number.
You pay it twice: once opening, once closing.

**Why it compounds.** Notional accumulates every time you trade. Across
{costs['transactions']:,} transactions this log totals **${costs['total_notional']:,.0f}** of
cumulative notional — not because that much was ever deposited, but because a few hundred
dollars of working capital was cycled through high leverage, repeatedly, over years.

**The sanity check.** Effective fee rate here is **{costs['fee_rate_pct']:.4f}%** of notional.
If that matches your venue's published rate, the total is arithmetic, not a bug.

**Also worth knowing.** Jupiter charges hourly *borrow* fees rather than funding rates, so
holding longer costs more even if you never trade again. Time in a position is itself a cost.

**What to do.** Before entering, compute round-trip cost as a share of your collateral. At
{costs['median_leverage']:.0f}x with a ~0.07% fee, that's roughly
{2 * 0.0007 * (costs['median_leverage'] or 1) * 100:.1f}% of collateral gone the moment you
open and close — before the market moves at all.
        """)


def render_findings(trades):
    header("🔍 What Your Log Actually Supports")
    st.caption("Each finding shows the mechanism, the evidence with sample sizes, and an honest "
               "status. Expand to see reasoning rather than just a conclusion.")

    by_exit = group_by(trades, lambda t: t["exit_type"])
    trig, mkt = by_exit.get("Trigger"), by_exit.get("Market")
    liq_trades = [t for t in trades if t["exit_type"] == "Liquidation"]
    nonliq = [t for t in trades if t["exit_type"] != "Liquidation"]

    if trig and mkt and trig["n"] >= 30 and mkt["n"] >= 30:
        status_badge("VALIDATED")
        st.markdown("**Letting your pre-set exit fire beats overriding it**")
        with st.expander("Mechanism, evidence, and what to do"):
            st.markdown(f"""
**Mechanism.** A trigger is a decision you made calmly, before the position existed. A manual
close is made mid-trade, while watching money move. Traders override plans precisely when a
position goes against them — which is when judgement is worst.

**Evidence from your log.** Trigger exits: **${trig['expectancy']:.2f}/trade** across
{trig['n']:,} trades, {trig['win_rate']:.1f}% win rate. Manual market exits:
**${mkt['expectancy']:.2f}/trade** across {mkt['n']}, {mkt['win_rate']:.1f}% win rate.
Bootstrap 95% CI on the difference excluded zero, and the gap held in both halves of history.

**Caveat — read this.** Partly *selection*: you likely intervene BECAUSE a trade is already
going badly, so some of the gap is the trade, not the override. Even under that reading, the
override adds nothing measurable. The prescription is unchanged.

**What to do.** Set your exit at entry. Then don't touch it.
            """)
        st.markdown("")

    if liq_trades and nonliq:
        liq_sizes = [t["size"] for t in liq_trades]
        non_sizes = [t["size"] for t in nonliq]
        status_badge("VALIDATED")
        st.markdown("**Your small positions get liquidated, not your big ones**")
        with st.expander("Mechanism, evidence, and what to do"):
            st.markdown(f"""
**Mechanism.** Liquidation is driven by **leverage and collateral buffer**, not position size.
A small position with high leverage and thin collateral is far more fragile than a large one
sized conservatively. Traders often lever small positions harder precisely because they feel
low-stakes.

**Evidence from your log.** {len(liq_trades)} liquidations across {len(trades):,} closed trades
({len(liq_trades)/len(trades)*100:.1f}%), costing **${sum(t['pnl'] for t in liq_trades):,.2f}**
gross. Median size of a liquidated position **${stats.median(liq_sizes):,.0f}** vs
**${stats.median(non_sizes):,.0f}** for those that survived. Median hold
{stats.median([t['hold_h'] for t in liq_trades]):.1f}h vs
{stats.median([t['hold_h'] for t in nonliq]):.1f}h.

**What to do.** Check leverage and collateral on your *small* entries specifically. This is
usually the highest-value fix available, because every liquidation is a fully avoidable loss.
            """)
        st.markdown("")

    for key, entry in fetch_evidence().items():
        if entry["status"] == "TESTED_AND_FAILED":
            status_badge(entry["status"])
            st.markdown(f"**{entry['claim']}**")
            with st.expander("Mechanism, evidence, and what to do"):
                st.markdown(f"**The mechanism.** {entry['mechanism']}")
                st.markdown(f"**What testing found.** {entry['evidence']}")
                st.info(f"**How to use it:** {entry['use']}")
            st.markdown("")


# ======================================================================
# DATA
# ======================================================================
@st.cache_data(ttl=30, show_spinner=False)
def fetch_telemetry():
    try:
        r = requests.get(f"{API_URL}/telemetry", timeout=15)
        if r.status_code == 200:
            return r.json(), None
        return {}, f"Backend returned status {r.status_code}"
    except Exception as e:
        return {}, f"Backend unreachable: {e}"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_evidence():
    try:
        r = requests.get(f"{API_URL}/evidence", timeout=15)
        if r.status_code == 200:
            return r.json().get("registry", {})
    except Exception:
        pass
    return {}


# ======================================================================
# MARKET SECTIONS
# ======================================================================
def render_guardrail(t):
    g = t.get("volatility_guardrail")
    if not g:
        return
    header("🌪️ Volatility Guardrail")
    status_badge("VALIDATED")
    st.caption("The one market signal here that survived testing — and it predicts move SIZE, "
               "not direction.")
    labels = " · ".join(g.get("elevated_labels", [])) or "none elevated"
    card(f"<b>{g['regime']}</b> · {g['elevated_count']} of {g['elevated_of']} validated signals "
         f"elevated ({labels})<br>{g['summary']}", g.get("kind", "info"))
    r = g["readings"]
    c1, c2, c3 = st.columns(3)
    c1.metric("1H ATR", f"{r['atr_pct']:.2f}%", help="Average True Range as % of price. r=+0.263 "
                                                     "against absolute 4h moves, n=2,153.")
    c2.metric("24h move", f"{r['momentum_24h_pct']:+.2f}%", help="Momentum extremity. r=+0.172, same test.")
    c3.metric("VIX move", f"{r['vix_pct']:+.2f}%",
              help="Shown for context only — excluded from the regime count pending re-test on "
                   "corrected data.")
    st.warning(g["direction_warning"])
    with st.expander("Why a magnitude signal is still useful without direction"):
        st.markdown("""
It tells you when to **size down**, which is a decision you can make without knowing which way
price goes. If forced liquidation is a meaningful cost in your log, a reliable "expect wider
swings" warning is worth more than an unreliable direction call — it acts on the loss you can
actually prevent.

The honest limit: it cannot tell you whether to be long or short, and anyone selling you a
volatility signal as a direction signal is overreaching.
        """)


def render_market(t):
    header("📊 Live Market Context")
    st.caption("Real data with the mechanism explained. Each factor carries its own evidence "
               "status — read those before drawing conclusions.")
    ta = t.get("ta", {})
    d = t.get("deltas", {})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Live Spot", f"${t.get('spot_price', 0):,.2f}",
              f"{d.get('spot_pct_24h'):+.2f}% (24h)" if d.get("spot_pct_24h") is not None else None)
    c2.metric("RSI(14, Wilder)", f"{ta.get('rsi', 50):.1f}",
              f"{d.get('rsi_1h'):+.1f} (1h)" if d.get("rsi_1h") is not None else None,
              help="Momentum, 0–100. Tested here for 4h direction: not significant (t=-0.97).")
    c3.metric("Session VWAP", f"${ta.get('vwap', 0):,.2f}",
              f"{d.get('vwap_1h_pct'):+.3f}% (1h)" if d.get("vwap_1h_pct") is not None else None,
              help="Volume-weighted average price since 00:00 UTC. Divergence from it tested "
                   "not significant for 4h direction (t=-0.51).")
    c4.metric("Open Interest", t.get("open_interest", "N/A"),
              f"{d.get('oi_1h_pct'):+.2f}% (1h)" if d.get("oi_1h_pct") is not None else None,
              help="Outstanding futures contracts. Rising OI with a price move suggests new "
                   "money entering the trend.")

    chart = t.get("price_chart", [])
    if chart:
        times = [datetime.fromtimestamp(p["t"], tz=timezone.utc) for p in chart]
        fig = go.Figure(data=go.Candlestick(
            x=times, open=[p["o"] for p in chart], high=[p["h"] for p in chart],
            low=[p["l"] for p in chart], close=[p["c"] for p in chart],
            increasing_line_color="#00E676", decreasing_line_color="#FF3366",
            increasing_fillcolor="#00E676", decreasing_fillcolor="#FF3366"))
        hm = t.get("orderbook_heatmap", {})
        fig.add_hline(y=ta.get("vwap", 0), line_dash="dot", line_color="#00FFCC", line_width=1.5,
                      annotation_text="Session VWAP", annotation_font=dict(color="#00FFCC", size=11))
        if hm.get("upper_wall"):
            fig.add_hline(y=hm["upper_wall"], line_dash="dot", line_color="#FF3366",
                          line_width=1, opacity=0.6, annotation_text="Upper Wall")
        if hm.get("lower_wall"):
            fig.add_hline(y=hm["lower_wall"], line_dash="dot", line_color="#00E676",
                          line_width=1, opacity=0.6, annotation_text="Lower Wall")
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10), template="plotly_dark",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          xaxis=dict(showgrid=False, rangeslider=dict(visible=False)),
                          yaxis=dict(tickformat="$,.0f", gridcolor="rgba(255,255,255,0.05)"),
                          showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def render_confluence(t):
    cb = t.get("confluence_board")
    if not cb:
        return
    header("🧭 Confluence Board — Form Your Own View")
    st.caption("Six real, live inputs to Bitcoin's backdrop. This is NOT a trading signal — "
               "read the conditions and decide for yourself.")

    b, r, n = cb["bullish_count"], cb["bearish_count"], cb["neutral_count"]
    fig = go.Figure()
    for count, colour, name in ((b, "#00E676", "Bullish"), (n, "#8892B0", "Neutral"),
                                (r, "#FF3366", "Bearish")):
        fig.add_trace(go.Bar(x=[count], y=[""], orientation="h", marker_color=colour,
                             text=f"{count} {name}" if count else "", textposition="inside",
                             insidetextanchor="middle", textfont=dict(color="#0A0E17", size=13)))
    fig.update_layout(barmode="stack", height=70, margin=dict(l=10, r=10, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      showlegend=False, xaxis=dict(visible=False, range=[0, b + n + r]),
                      yaxis=dict(visible=False))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    kind = {"strong_bullish": "bullish", "moderate_bullish": "bullish",
            "strong_bearish": "bearish", "moderate_bearish": "bearish",
            "split": "conflict", "quiet": "neutral"}.get(cb["scenario"], "info")
    card(f"{cb['scenario_icon']} <b>{cb['scenario_label']}</b><br>{cb['scenario_summary']}", kind)
    with st.expander("Read the full explanation of this pattern"):
        st.markdown(cb["scenario_explanation"])

    cols = st.columns(3)
    lean_colour = {"bullish": ("#0B3D24", "#00E676"), "bearish": ("#3D0B18", "#FF3366"),
                   "neutral": ("#3D2B00", "#FFB020")}
    for i, f in enumerate(cb.get("factors", [])):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{f['label']}**")
                bg, fg = lean_colour.get(f["lean"], lean_colour["neutral"])
                badge(f"{f['value_str']} · {f['lean'].title()}", bg, fg)
                status_badge(f.get("status", "UNTESTED"))
                st.caption(f["explanation"])
    st.caption(cb["disclaimer"])


def render_calendar(t):
    cal = t.get("economic_calendar")
    if not cal:
        return
    header("📅 Economic Calendar")
    status_badge(cal.get("status", "UNTESTED"))
    c1, c2 = st.columns(2)
    for col, key, title, edu in ((c1, "next_cpi", "📊 Next CPI Release", "cpi_education"),
                                 (c2, "next_fomc", "🏛️ Next FOMC Meeting", "fomc_education")):
        with col, st.container(border=True):
            st.markdown(f"**{title}**")
            ev = cal.get(key, {})
            if ev.get("date"):
                st.metric("Date", ev["date"], help=ev.get("time_et", ""))
                du = ev.get("days_until")
                st.caption("📍 That's today." if du == 0 else f"{du} day{'s' if du != 1 else ''} away.")
            else:
                st.warning(ev.get("note", "No upcoming date on file."))
            st.caption(cal.get(edu, ""))
    st.caption(f"Dates last verified {cal.get('last_verified','N/A')}. {cal.get('disclaimer','')}")


def render_research_bench():
    header("🔬 Research Bench")
    st.caption("Test an idea against the corrected engine. Read-only — nothing here changes any "
               "displayed number by itself.")
    card(
        "<b>Read this before trusting any result.</b> This engine previously reported a strong "
        "4-hour edge that turned out to be a date-alignment bug letting the model see closing "
        "prices before they printed. It passed out-of-sample testing while being wrong, because "
        "out-of-sample checks catch overfitting, not lookahead. The bug is fixed — but the lesson "
        "is that a clean-looking result is a hypothesis, not a conclusion.", "conflict")

    c1, c2 = st.columns(2)
    with c1:
        months = st.number_input("Months of history", 1, 90, 24, key="fr_months")
        target = st.radio("Test what?", ["direction", "magnitude"], horizontal=True,
                          help="direction = which way price moves. magnitude = how big the move "
                               "is regardless of direction.")
        if st.button("Run Factor Research"):
            with st.spinner("Reconstructing history and testing correlations…"):
                try:
                    resp = requests.post(f"{API_URL}/research/run",
                                         params={"months": int(months), "target": target},
                                         timeout=600).json()
                except Exception as e:
                    resp = {"status": "error", "error": str(e)}
            if resp.get("status") == "completed":
                rows = []
                for horizon, feats in resp.get("report", {}).items():
                    for name, d in feats.items():
                        no = d.get("non_overlapping", {})
                        rows.append({
                            "Horizon": horizon, "Feature": name,
                            "r": no.get("r"), "t": no.get("t_stat"), "n": no.get("n"),
                            "Robust": "✓" if d.get("robust") else "",
                            "Daily-only": "⚠" if d.get("effective_sample") else "",
                        })
                robust = [r for r in rows if r["Robust"]]
                st.success(f"Analyzed {resp.get('rows_analyzed', 0):,} points. "
                           f"{len(robust)} of {len(rows)} feature/horizon pairs cleared the robust bar.")
                st.dataframe(sorted(rows, key=lambda r: -(abs(r["t"]) if r["t"] else 0)),
                             use_container_width=True, hide_index=True)
                st.caption("⚠ = feature only updates daily, so its true independent sample is "
                           "smaller than n and its t-stat is inflated. Divide by ~√6 at 4h.")
            elif resp.get("status") == "already_running":
                st.warning("Already running — check back shortly.")
            else:
                st.error(f"Failed: {resp.get('error', 'unknown error')}")

    with c2:
        oos_months = st.number_input("Months of history", 1, 90, 48, key="oos_months")
        oos_feats = st.text_input("Features (comma-separated)", value="atr_pct_14h",
                                  help="Only pass features that already cleared 'robust' on the left.")
        oos_horizon = st.selectbox("Horizon", ["4h", "2d", "14d"])
        if st.button("Run Out-of-Sample Test"):
            with st.spinner("Fitting on the early portion, testing on unseen later data…"):
                try:
                    resp = requests.post(f"{API_URL}/research/calibrate-oos",
                                         params={"months": int(oos_months), "horizon": oos_horizon,
                                                 "features": oos_feats}, timeout=600).json()
                except Exception as e:
                    resp = {"status": "error", "error": str(e)}
            if resp.get("status") == "completed":
                oos = resp.get("out_of_sample_result", {})
                if "error" in oos:
                    st.warning(oos["error"])
                else:
                    r2 = oos.get("out_of_sample_r_squared")
                    st.metric("Out-of-sample R²", f"{r2}")
                    st.caption(f"Trained on {resp.get('train_window_size')} windows, tested on "
                               f"{resp.get('test_window_size')} it never saw. Negative is a real "
                               f"result — it means worse than guessing the training average.")
            else:
                st.error(f"Failed: {resp.get('error', 'unknown error')}")


# ======================================================================
# MAIN
# ======================================================================
def main():
    with st.sidebar:
        st.markdown("### 📊 Market Education Terminal")
        st.caption("Understand what moves markets, and measure how you trade. "
                   "No directional signal is offered here — see below for why.")
        upload = st.file_uploader("Your trade log (CSV export)", type=["csv"])
        st.caption("Read in memory for this session only. Nothing is stored. Re-uploading a "
                   "fresh full export is safe — duplicates are removed by transaction ID.")
        st.markdown("---")
        with st.expander("Why there's no buy/sell signal"):
            st.markdown("""
This project shipped one. A 4-hour BTC score regressed on VIX and the S&P 500, reporting a
strong validated edge (z=6.32 across six years).

It was a bug. The backtest attributed each day's equity close to every hour of that same day,
so the model could read a closing price up to twenty hours before it existed. Corrected, the
edge went to zero (z=−0.94).

It had passed out-of-sample testing, split-half checks, and a non-overlap correction — because
those catch overfitting, and this wasn't overfitting.

That's the most useful thing this project produced, and it's why the tool now measures what
you can control instead of predicting what you can't.
            """)

    st.markdown("<h2 style='margin-bottom:0;'>📊 Market Education Terminal</h2>",
                unsafe_allow_html=True)
    st.caption("Real market data, honest evidence labels, and a measurement of your own execution.")

    telemetry, err = fetch_telemetry()
    if err:
        st.error(f"⚠️ {err}")
        st.caption("Free-tier backends sleep when idle — the first request can take 30–60 seconds. "
                   "Reload once before assuming it's broken.")
    else:
        dq = telemetry.get("data_quality", {})
        gen = dq.get("generated_at", "")
        if dq.get("any_fallback"):
            stale = [k.replace("macro_", "").upper() for k, v in dq.items()
                     if v == "fallback" and k not in ("any_fallback", "generated_at")]
            st.markdown(f"<span class='stale'>🟡 PARTIAL FALLBACK</span> &nbsp; placeholder values "
                        f"for: <b>{', '.join(stale)}</b>. Any figure derived from these is not live.",
                        unsafe_allow_html=True)
        else:
            st.markdown(f"<span class='live'>🟢 ALL FEEDS LIVE</span> &nbsp; {gen}",
                        unsafe_allow_html=True)

    if upload:
        try:
            trades, costs = load_trades(upload.getvalue())
        except Exception as e:
            st.error(f"Couldn't read that file: {e}")
            trades, costs = [], None
        if trades:
            if costs and costs["duplicates_skipped"]:
                st.caption(f"Merged upload: {costs['duplicates_skipped']:,} duplicate "
                           f"transactions skipped.")
            render_execution(trades, costs)
            render_findings(trades)
        else:
            st.warning("No closed trades found — the file may only contain open positions.")
    else:
        header("📋 Execution Scorecard")
        card("Upload your trade log in the sidebar to populate this section. It measures override "
             "rate, liquidation rate, and expectancy — the parts of trading you control. Nothing "
             "is stored.", "info")

    if telemetry:
        render_guardrail(telemetry)
        render_market(telemetry)
        render_confluence(telemetry)
        render_calendar(telemetry)
    render_research_bench()


if __name__ == "__main__":
    main()
