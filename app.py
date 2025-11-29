# app.py
import streamlit as st
from datetime import datetime
from math import ceil
import pandas as pd
import numpy as np

# ---------- CONFIG ----------
DEFAULT_BALANCE = 10000.00
DEFAULT_SL_POINTS_BUFFER = 20.0
DEFAULT_SL_PERCENT_BUFFER = 0.2
RISK_PERCENT = 1.0  # 1% risk of unutilised capital

DAILY_MAX_TRADES = 4
DAILY_MAX_PER_SYMBOL = 2

# ---------- SESSION INIT ----------
def init_state():
    if 'trades' not in st.session_state:
        st.session_state.trades = []
    today = datetime.utcnow().date().isoformat()
    if 'stats' not in st.session_state:
        st.session_state.stats = {today: {"total": 0, "by_symbol": {}}}
init_state()

# ---------- SIMULATED BROKER / HELPERS ----------
def fetch_balance_from_broker(api_key, api_secret):
    """
    Placeholder: fetch user balance from broker using keys.
    If keys are empty, return DEFAULT_BALANCE.
    """
    if not api_key or not api_secret:
        return DEFAULT_BALANCE
    # Real integration: call broker/testnet API to get balance
    # For now simulate slightly varying balance
    return DEFAULT_BALANCE + (datetime.utcnow().minute % 10) * 10

def calculate_unutilized_capital(balance):
    # For simplicity we consider margin used = sum(notional/leverage)
    used = 0.0
    for t in st.session_state.trades:
        used += (t.get("notional", 0) / max(1.0, t.get("leverage", 1.0)))
    unutil = max(0.0, balance - used)
    return unutil

# ---------- CORE CALC ----------
def calculate_sizing(balance, entry_price, sl_type, sl_value):
    """
    Returns: units, leverage_suggested, notional, unutilized, max_leverage
    """
    unutil = calculate_unutilized_capital(balance)
    risk_amount = (unutil * RISK_PERCENT) / 100.0  # 1% of unutilized capital

    if unutil <= 0 or entry_price <= 0 or sl_value <= 0:
        return 0.0, 1.0, 0.0, unutil, 0.0

    if sl_type == "SL Points":
        distance = sl_value
        denom = distance + DEFAULT_SL_POINTS_BUFFER
        if denom <= 0:
            return 0.0, 1.0, 0.0, unutil, 0.0
        units = risk_amount / denom
        notional = units * entry_price
        leverage = max(1.0, notional / unutil if unutil > 0 else 1.0)
        leverage = ceil(leverage * 2) / 2.0
        # approximate sl% from points for showing max leverage
        sl_percent = (distance / entry_price) * 100.0 if entry_price > 0 else 0.0
        max_leverage = 100.0 / sl_percent if sl_percent > 0 else 0.0
        return units, leverage, notional, unutil, max_leverage

    else:  # SL % Movement
        sl_percent = sl_value  # e.g., 0.5 meaning 0.5%
        eff_percent = sl_percent + DEFAULT_SL_PERCENT_BUFFER
        eff_price_distance = (eff_percent / 100.0) * entry_price
        if eff_price_distance <= 0:
            return 0.0, 1.0, 0.0, unutil, 0.0
        units = risk_amount / eff_price_distance
        notional = units * entry_price
        max_leverage = 100.0 / sl_percent if sl_percent > 0 else 0.0
        leverage = max(1.0, max_leverage)
        return units, leverage, notional, unutil, max_leverage

# ---------- ORDER EXECUTION ----------
def place_order(symbol, side, order_type, entry, sl, tp_list, units, leverage, api_key, api_secret):
    """Simulated broker order placement. Real API requires keys and implementation."""
    # Real implementation: send order to broker, handle success/fail responses
    now = datetime.utcnow()
    trade = {
        "id": int(now.timestamp() * 1000),
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M:%S"),
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "entry": entry,
        "stop_loss": sl,
        "units": units,
        "leverage": leverage,
        "notional": units * entry,
        "tps": tp_list
    }
    st.session_state.trades.insert(0, trade)  # newest first
    # update stats
    today = datetime.utcnow().date().isoformat()
    s = st.session_state.stats.setdefault(today, {"total": 0, "by_symbol": {}})
    s["total"] = s.get("total", 0) + 1
    s["by_symbol"][symbol] = s["by_symbol"].get(symbol, 0) + 1
    return "OK"

# ---------- UI - SINGLE SCREEN HORIZONTAL LAYOUT ----------
st.set_page_config(layout="wide", page_title="Exchange Order Panel - Compact")

# compact CSS: hide page scrollbar but allow trade log scroll area
st.markdown("""
<style>
/* hide main page scroll but allow right panel to scroll */
html, body, .reportview-container, .main, .block-container {
  overflow: hidden;
  height: 100vh;
}
/* minimal paddings to fit all in one screen */
.block-container { padding: 8px 8px 8px 8px; }
/* compact inputs */
.css-1aumxhk { padding: 4px 6px; }
/* make right panel scrollable area */
.right-log {
  height: calc(100vh - 24px);
  overflow-y: auto;
  padding: 8px;
  border-left: 1px solid #2b2b2b;
}
.small-muted { font-size:12px; color:#888; }
.kv { font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ---------- Top bar: symbol toggle + api keys (minimal) ----------
col_top = st.columns([1, 1, 1, 1])
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]  # default set; change as required

with col_top[0]:
    symbol = st.radio("", symbols, index=0, horizontal=True)  # symbol toggle

with col_top[1]:
    # API keys (hidden inputs)
    api_key = st.text_input("", value="", placeholder="API Key (optional)", type="password", key="api_key")
with col_top[2]:
    api_secret = st.text_input("", value="", placeholder="Secret (optional)", type="password", key="api_secret")
with col_top[3]:
    # quick display of fetched balance (no extra words)
    balance = fetch_balance_from_broker(api_key, api_secret)
    st.markdown(f"<div class='kv'>Balance:</div><div class='small-muted'>${balance:,.2f}</div>", unsafe_allow_html=True)

st.markdown("")  # tiny spacer

# ---------- Main panels: left (order form) and right (log) ----------
left_col, right_col = st.columns([1.2, 0.8])

with left_col:
    # Compact order form (no labels except placeholder style)
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        side = st.radio("", ["LONG", "SHORT"], index=0, horizontal=True)
    with c2:
        order_type = st.radio("", ["MARKET", "LIMIT", "STOP"], index=0, horizontal=True)
    with c3:
        entry = st.number_input("", min_value=0.0000001, value=1000.0, format="%.8f", key="entry_input", help="Entry price")

    # sizing and SL toggles (compact)
    s1, s2, s3 = st.columns([1,1,1])
    with s1:
        sizing_method = st.radio("", ["Position Size", "Lot Size"], index=0, horizontal=True)
    with s2:
        sl_method = st.radio("", ["SL Points", "SL % Movement"], index=0, horizontal=True)
    with s3:
        if sl_method == "SL Points":
            sl_price = st.number_input("", min_value=0.0000001, value=entry - 5.0, format="%.8f", key="sl_price")
            sl_value = abs(entry - sl_price)
        else:
            sl_percent = st.number_input("", min_value=0.01, value=0.5, format="%.2f", key="sl_percent")
            sl_value = sl_percent

    # TPs row (compact)
    t1, t2 = st.columns([1,1])
    with t1:
        tp1_price = st.number_input("", min_value=0.0, value=entry * 1.005, format="%.8f", key="tp1_price")
    with t2:
        tp1_pct = st.number_input("", min_value=0, max_value=100, value=70, step=5, key="tp1_pct")

    # TP2 price small input
    tp2_price = st.number_input("", min_value=0.0, value=entry * 1.015, format="%.8f", key="tp2_price")

    # Calculate suggested sizing
    units, suggested_lev, notional, unutil, max_lev = calculate_sizing(balance, entry, sl_method, sl_value)

    # Show only suggested lot & suggested leverage (no extra words)
    st.markdown(f"<div style='display:flex;gap:12px;align-items:center;'>"
                f"<div><b>Suggested Lot</b><div class='small-muted'>{units:,.6f}</div></div>"
                f"<div><b>Leverage</b><div class='small-muted'>{suggested_lev:.2f}x</div></div>"
                f"</div>", unsafe_allow_html=True)

    # Inputs for user-supplied position/lot size and leverage (labels minimal)
    pos_lot = st.number_input("Position / Lot Size", min_value=0.0, value=0.0, format="%.8f",
                              help="0 = use suggested", key="pos_lot")
    leverage = st.number_input("Leverage", min_value=1.0, value=1.0, format="%.2f", key="leverage_input")

    # Execute button (compact)
    if st.button("EXECUTE / PLACE ORDER", type="primary"):
        # determine units/leverage to use
        use_units = pos_lot if pos_lot > 0 else units
        use_lev = leverage if leverage >= 1.0 else suggested_lev

        # basic checks
        # check daily limits
        today = datetime.utcnow().date().isoformat()
        stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
        if stats.get("total", 0) >= DAILY_MAX_TRADES:
            st.warning("Daily trades limit reached")
        elif stats.get("by_symbol", {}).get(symbol, 0) >= DAILY_MAX_PER_SYMBOL:
            st.warning("Symbol daily limit reached")
        else:
            # margin check (simplified)
            margin_required = (use_units * entry) / use_lev if use_lev > 0 else use_units * entry
            if margin_required > unutil + 1e-9:
                st.warning("Insufficient unutilized capital for margin")
            else:
                tps = []
                if tp1_price > 0 and tp1_pct > 0:
                    tps.append({"price": tp1_price, "pct": tp1_pct})
                if tp2_price > 0:
                    tps.append({"price": tp2_price, "pct": 100 - tp1_pct})
                res = place_order(symbol, side, order_type, entry, sl_price if sl_method == "SL Points" else sl_price, tps, use_units, use_lev, api_key, api_secret)
                if res == "OK":
                    st.success("Order placed")
                else:
                    st.error("Order failed")

with right_col:
    # Right panel: scrollable trade log
    st.markdown("<div class='right-log'>", unsafe_allow_html=True)
    st.markdown("<div style='display:flex;justify-content:space-between;align-items:center;'><div><b>Trade Log</b></div></div>", unsafe_allow_html=True)

    # Display trades as a dataframe (scrollable inside this area)
    if st.session_state.trades:
        df = pd.DataFrame(st.session_state.trades)
        # show minimal columns
        df_display = df[["time", "symbol", "side", "order_type", "entry", "units", "leverage", "notional"]]
        df_display.columns = ["Time", "Symbol", "Side", "Type", "Entry", "Units", "Lev", "Notional"]
        st.dataframe(df_display, height=520)
    else:
        st.markdown("<div class='small-muted'>No trades yet</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
