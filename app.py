
import streamlit as st
from datetime import datetime
from math import ceil
import pandas as pd

# ----------------- CONFIG -----------------
DEFAULT_BALANCE = 10000.00
DEFAULT_SL_POINTS_BUFFER = 20.0
DEFAULT_SL_PERCENT_BUFFER = 0.2
RISK_PERCENT = 1.0  # percent of unutilised capital to risk

DAILY_MAX_TRADES = 999  # keep high for flexibility, adjust as needed
DAILY_MAX_PER_SYMBOL = 999

SYMBOLS_DEFAULT = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

# ----------------- SESSION INIT -----------------
def init_state():
    if 'trades' not in st.session_state:
        st.session_state.trades = []
    today = datetime.utcnow().date().isoformat()
    if 'stats' not in st.session_state:
        st.session_state.stats = {today: {"total": 0, "by_symbol": {}}}
init_state()

# ----------------- BROKER / HELPERS -----------------
def fetch_balance_from_broker(api_key, api_secret):
    """
    Placeholder for fetching real balance via broker API.
    If keys aren't provided, returns DEFAULT_BALANCE.
    """
    if not api_key or not api_secret:
        return DEFAULT_BALANCE
    # Replace with real API call to exchange/testnet
    # Simulated variation to show dynamic values
    now = datetime.utcnow()
    simulated = DEFAULT_BALANCE + ((now.minute % 10) * 5)
    return simulated

def calculate_unutilized_capital(balance):
    used = 0.0
    for t in st.session_state.trades:
        used += (t.get("notional", 0) / max(1.0, t.get("leverage", 1.0)))
    unutil = max(0.0, balance - used)
    return unutil

# ----------------- POSITION SIZING -----------------
def calculate_sizing(balance, entry_price, sl_mode, sl_value):
    """
    Returns tuple: (units, suggested_leverage, notional, unutilized_capital, max_leverage)
    sl_mode: "SL Points" or "SL % Movement"
    sl_value: numeric value (points or percent)
    """
    unutil = calculate_unutilized_capital(balance)
    risk_amount = (unutil * RISK_PERCENT) / 100.0  # 1% of unutilized capital

    # safety
    if unutil <= 0 or entry_price <= 0 or sl_value <= 0:
        return 0.0, 1.0, 0.0, unutil, 0.0

    if sl_mode == "SL Points":
        distance = sl_value
        denom = distance + DEFAULT_SL_POINTS_BUFFER
        if denom <= 0:
            return 0.0, 1.0, 0.0, unutil, 0.0
        units = risk_amount / denom
        notional = units * entry_price
        suggested_lev = max(1.0, notional / unutil if unutil > 0 else 1.0)
        suggested_lev = ceil(suggested_lev * 2) / 2.0
        # approximate sl% for max leverage display
        sl_percent = (distance / entry_price) * 100.0 if entry_price > 0 else 0.0
        max_lev = 100.0 / sl_percent if sl_percent > 0 else 0.0
        return units, suggested_lev, notional, unutil, max_lev
    else:
        # SL % Movement
        sl_percent = sl_value
        eff_percent = sl_percent + DEFAULT_SL_PERCENT_BUFFER
        eff_price_distance = (eff_percent / 100.0) * entry_price
        if eff_price_distance <= 0:
            return 0.0, 1.0, 0.0, unutil, 0.0
        units = risk_amount / eff_price_distance
        notional = units * entry_price
        max_lev = 100.0 / sl_percent if sl_percent > 0 else 0.0
        suggested_lev = max(1.0, max_lev)
        return units, suggested_lev, notional, unutil, max_lev

# ----------------- ORDER PLACEMENT SIM -----------------
def place_order(symbol, side, order_type, entry, sl_value, sl_mode, tps, units, leverage, api_key, api_secret):
    """
    Simulated order: logs to session_state.trades
    """
    now = datetime.utcnow()
    trade = {
        "id": int(now.timestamp() * 1000),
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M:%S"),
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "entry": entry,
        "sl_value": sl_value,
        "sl_mode": sl_mode,
        "units": units,
        "leverage": leverage,
        "notional": units * entry,
        "tps": tps
    }
    # prepend so newest at top
    st.session_state.trades.insert(0, trade)

    # update stats
    today = datetime.utcnow().date().isoformat()
    s = st.session_state.stats.setdefault(today, {"total": 0, "by_symbol": {}})
    s["total"] = s.get("total", 0) + 1
    s["by_symbol"][symbol] = s["by_symbol"].get(symbol, 0) + 1
    return True

# ----------------- UI CSS (Mode 3 - Ultra Professional) -----------------
st.set_page_config(layout="wide", page_title="Pro Order Panel")
st.markdown("""
<style>
/* overall page */
html, body, .reportview-container, .main, .block-container {
  height: 100vh;
  margin: 0;
  padding: 8px 12px 8px 12px;
  background-color: #0b0f14;
  color: #e6eef6;
  overflow: hidden; /* remove global scrollbar */
}

/* left panel card */
.left-card {
  background: linear-gradient(180deg, #0f1519 0%, #0b0f14 100%);
  border: 1px solid rgba(255,255,255,0.03);
  padding: 14px;
  border-radius: 8px;
  height: calc(100vh - 24px);
  box-sizing: border-box;
}

/* right panel scrollable */
.right-log {
  height: calc(100vh - 24px);
  overflow-y: auto;
  padding-left: 12px;
  box-sizing: border-box;
}

/* inputs compact */
[data-testid="stNumberInput"] > div { padding: 6px 8px !important; }
.stButton>button { padding: 8px 12px; border-radius:6px; font-weight:700; background-color:#ff4d4d; color:white; }
.stRadio > div, .stRadio label { font-weight:600; color:#dbe9ff; }

/* minimal labels: hide Streamlit default label space */
.css-1y4p8pa { margin-bottom: 6px; }  /* general control container tweak */

/* small muted text */
.small-muted { color: #93a3b8; font-size:13px; }

/* compact rows */
.row { display:flex; gap:10px; align-items:center; }

/* minimal divider */
.sep { height:1px; background:rgba(255,255,255,0.03); margin:8px 0; border-radius:2px; }

/* table header style */
.table-header { color:#98b4e3; font-weight:700; margin-bottom:8px; }

/* reduce padding for dataframe */
.stFrame { padding:0; margin:0; }

/* responsive tweaks */
@media (max-width: 1100px) {
  .left-card { height: auto; }
}
</style>
""", unsafe_allow_html=True)

# ----------------- TOP BAR (symbols + keys + balance) -----------------
top_cols = st.columns([1.5, 1, 1, 1])
with top_cols[0]:
    symbols = SYMBOLS_DEFAULT.copy()
    # quick symbol toggle horizontally
    symbol = st.radio("", symbols, index=0, horizontal=True)
with top_cols[1]:
    api_key = st.text_input("", value="", placeholder="API Key (optional)", type="password")
with top_cols[2]:
    api_secret = st.text_input("", value="", placeholder="Secret (optional)", type="password")
with top_cols[3]:
    balance = fetch_balance_from_broker(api_key, api_secret)
    st.markdown(f"<div class='small-muted'>Balance</div><div style='font-weight:800;'>${balance:,.2f}</div>", unsafe_allow_html=True)

st.markdown("")  # small spacer

# ----------------- MAIN PANELS -----------------
left_col, right_col = st.columns([1.1, 0.9])

with left_col:
    st.markdown("<div class='left-card'>", unsafe_allow_html=True)

    # Row 1: side + order type
    r1 = st.columns([1,1])
    with r1[0]:
        side = st.radio("", ["LONG", "SHORT"], index=0, horizontal=True)
    with r1[1]:
        order_type = st.radio("", ["MARKET", "LIMIT", "STOP"], index=0, horizontal=True)

    # Row 2: Entry, compact
    st.markdown("<div class='sep'></div>", unsafe_allow_html=True)
    entry = st.number_input("", min_value=0.0000001, value=1000.0, format="%.8f", key="entry_main", help="Entry price")

    # Row 3: Sizing method + SL method toggles
    r3 = st.columns([1,1])
    with r3[0]:
        sizing_method = st.radio("", ["Position Size", "Lot Size"], index=0, horizontal=True)
    with r3[1]:
        sl_method = st.radio("", ["SL Points", "SL % Movement"], index=0, horizontal=True)

    # Row 4: SL input (either points or %)
    if sl_method == "SL Points":
        sl_price = st.number_input("", min_value=0.0000001, value=entry - 5.0, format="%.8f", key="sl_price_main", help="Stop loss price")
        sl_value = abs(entry - sl_price)
    else:
        sl_percent = st.number_input("", min_value=0.01, value=0.5, format="%.2f", key="sl_percent_main", help="Stop loss percent (e.g., 0.5)")
        sl_value = sl_percent
        # derive sl_price for clarity (not shown unless needed)
        sl_price = entry * (1 - sl_percent / 100.0) if side == "LONG" else entry * (1 + sl_percent / 100.0)

    # Row 5: TPs in one compact row
    st.markdown("<div class='sep'></div>", unsafe_allow_html=True)
    tcols = st.columns([1,1,1])
    with tcols[0]:
        tp1_price = st.number_input("", min_value=0.0, value=entry * 1.005, format="%.8f", key="tp1_main")
    with tcols[1]:
        tp1_pct = st.number_input("", min_value=0, max_value=100, value=70, step=5, key="tp1_pct_main")
    with tcols[2]:
        tp2_price = st.number_input("", min_value=0.0, value=entry * 1.015, format="%.8f", key="tp2_main")

    # compute suggested sizing
    units, suggested_lev, notional, unutil, max_lev = calculate_sizing(balance, entry, sl_method, sl_value)

    # show suggested lot & suggested leverage (compact)
    st.markdown("")
    slcols = st.columns([1,1,1])
    with slcols[0]:
        st.markdown("<div class='small-muted'>Suggested Lot</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-weight:800;'>{units:,.6f}</div>", unsafe_allow_html=True)
    with slcols[1]:
        st.markdown("<div class='small-muted'>Suggested Leverage</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-weight:800;'>{suggested_lev:.2f}x</div>", unsafe_allow_html=True)
    with slcols[2]:
        st.markdown("<div class='small-muted'>Unutilized</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-weight:800;'>${unutil:,.2f}</div>", unsafe_allow_html=True)

    st.markdown("<div class='sep'></div>", unsafe_allow_html=True)

    # Position / Lot size input & Leverage input (small labels)
    pos_lot = st.number_input("Position / Lot Size", min_value=0.0, value=0.0, format="%.8f", key="poslot_main", help="0 = use suggested")
    leverage = st.number_input("Leverage", min_value=1.0, value=1.0, format="%.2f", key="leverage_main", help="Set leverage (1 means no leverage)")

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # Execute button (full width)
    if st.button("EXECUTE / PLACE ORDER"):
        # determine final units and leverage to use
        final_units = pos_lot if pos_lot > 0 else units
        final_lev = leverage if leverage >= 1.0 else suggested_lev

        # Basic validations
        today = datetime.utcnow().date().isoformat()
        stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
        if stats.get("total", 0) >= DAILY_MAX_TRADES:
            st.warning("Daily trades limit reached")
        elif stats.get("by_symbol", {}).get(symbol, 0) >= DAILY_MAX_PER_SYMBOL:
            st.warning("Symbol daily limit reached")
        else:
            margin_required = (final_units * entry) / final_lev if final_lev > 0 else final_units * entry
            if margin_required > unutil + 1e-9:
                st.warning("Insufficient unutilized capital for margin")
            else:
                # build TP list
                tps = []
                if tp1_price > 0 and tp1_pct > 0:
                    tps.append({"price": tp1_price, "pct": tp1_pct})
                if tp2_price > 0:
                    tps.append({"price": tp2_price, "pct": 100 - tp1_pct})
                ok = place_order(symbol, side, order_type, entry, sl_value, sl_method, tps, final_units, final_lev, api_key, api_secret)
                if ok:
                    st.success("Order placed")
                else:
                    st.error("Order failed")

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    st.markdown("<div class='right-log'>", unsafe_allow_html=True)
    st.markdown("<div class='table-header'>Trade Log</div>", unsafe_allow_html=True)

    if st.session_state.trades:
        df = pd.DataFrame(st.session_state.trades)
        # simplify columns for display
        df_display = df[["time", "symbol", "side", "type", "entry", "units", "leverage", "notional"]]
        df_display.columns = ["Time", "Symbol", "Side", "Type", "Entry", "Units", "Lev", "Notional"]
        st.dataframe(df_display, height=580)
    else:
        st.markdown("<div class='small-muted'>No trades placed yet.</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
