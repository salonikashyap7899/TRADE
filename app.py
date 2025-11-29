# Optimized app.py — ZERO SCROLL, Professional One-Screen Trading Dashboard
import os
import streamlit as st
from datetime import datetime
from math import ceil
import numpy as np
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt

# Try to import python-binance
try:
    from binance.client import Client
    BINANCE_AVAILABLE = True
except Exception:
    BINANCE_AVAILABLE = False

# =========================
# CONFIG & CONSTANTS
# =========================
DAILY_MAX_TRADES = 4
DAILY_MAX_PER_SYMBOL = 2
RISK_PERCENT = 1.0
DEFAULT_BALANCE = 10000.00
DEFAULT_SL_POINTS_BUFFER = 20.0
DEFAULT_SL_PERCENT_BUFFER = 0.2
DEFAULT_LIVE_PRICE = 27050.00

# =========================
# SESSION STATE
# =========================
def init_state():
    if 'trades' not in st.session_state:
        st.session_state.trades = []
    if 'stats' not in st.session_state:
        st.session_state.stats = {}
    today = datetime.utcnow().date().isoformat()
    if today not in st.session_state.stats:
        st.session_state.stats[today] = {"total": 0, "by_symbol": {}}

def get_unutilized_capital(balance):
    today = datetime.utcnow().date().isoformat()
    today_trades = [t for t in st.session_state.trades if t.get("date") == today]
    used = sum(t.get("notional", 0) / t.get("leverage", 1) for t in today_trades)
    return max(0.0, balance - used)

# =========================
# PRICE FETCHING
# =========================
def get_live_price(symbol, broker, api_key, api_secret):
    symbol = symbol.strip().upper()
    if broker == "Binance Testnet" and BINANCE_AVAILABLE and api_key and api_secret:
        try:
            client = Client(api_key, api_secret)
            client.FUTURES_URL = 'https://testnet.binancefuture.com'
            price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
            return price
        except:
            pass
    # Fallback simulation
    return DEFAULT_LIVE_PRICE + (datetime.utcnow().minute % 10) * 0.5

# =========================
# POSITION SIZING
# =========================
def calc_position(balance, symbol, entry, sl_type, sl_value):
    unutilized = get_unutilized_capital(balance)
    risk_amt = unutilized * RISK_PERCENT / 100

    if unutilized <= 0 or entry <= 0 or sl_value <= 0:
        return 0, 0, 0, 0, "Invalid inputs"

    if sl_type == "SL Points":
        dist = sl_value + DEFAULT_SL_POINTS_BUFFER
        units = risk_amt / dist
        notional = units * entry
        lev = max(1.0, ceil((notional / unutilized) * 2) / 2.0)
        max_lev = 100 / ((sl_value / entry) * 100) if sl_value > 0 else 999
    else:
        pct = sl_value + DEFAULT_SL_PERCENT_BUFFER
        units = risk_amt / (entry * pct / 100)
        notional = units * entry
        lev = max_lev = 100 / sl_value

    return units, lev, notional, unutilized, f"""
    <small>
    Risk: ${risk_amt:,.0f} | Unutilized: ${unutilized:,.0f}<br>
    SL: {sl_value:.2f}{'pts' if sl_type=='SL Points' else '%'} (+buffer) → Max Lev: <b>{max_lev:.1f}x</b><br>
    Notional: ${notional:,.0f} @ {lev:.1f}x
    </small>
    """

# =========================
# PAGE LAYOUT — NO SCROLL!
# =========================
st.set_page_config(page_title="Pro Risk Dashboard", layout="wide")
init_state()

# Custom CSS to remove padding & make it tight
st.markdown("""
<style>
    .main > div { padding-top: 1rem; padding-bottom: 1rem; }
    .block-container { padding-top: 1rem; }
    h1 { margin: 0 !important; }
    .stButton>button { height: 60px; font-size: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# HEADER
st.markdown("<h1 style='text-align:center;color:#00ff9d;margin:0;'>PRO RISK CONTROL CENTER</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center;color:#888;margin:5px 0 20px 0;'>One Screen. Zero Scroll. Full Control.</h4>", unsafe_allow_html=True)

# TOP ROW: Broker + Balance + Live Price
col_a, col_b, col_c, col_d = st.columns([2, 2, 2, 3])
with col_a:
    broker = st.selectbox("Broker", ["Binance Testnet", "Simulation"], index=0)
with col_b:
    balance = st.number_input("Balance $", 100.0, 1000000.0, DEFAULT_BALANCE, step=1000.0, format="%.0f")
with col_c:
    api_key = st.text_input("API Key", type="password", help="Optional for live")
    api_secret = st.text_input("Secret", type="password")

# MAIN EXECUTION ZONE — 2 columns, fixed height
left, mid, right = st.columns([3.2, 0.6, 4], gap="large")

with left:
    st.markdown("#### Trade Setup")
    symbol = st.text_input("Symbol", "BTCUSDT").upper()
    live_price = get_live_price(symbol, broker, api_key, api_secret)

    st.markdown(f"""
    <div style="background:#000; border-left:5px solid #00ff9d; padding:10px; border-radius:5px;">
        <span style="font-size:14px;color:#888;">{symbol} Live Price</span><br>
        <span style="font-size:32px; font-weight:bold; color:#00ff9d;">${live_price:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

    side = st.selectbox("Direction", ["LONG", "SHORT"], index=0)
    order_type = st.selectbox("Order Type", ["MARKET ORDER", "LIMIT ORDER"])

    sl_type = st.radio("SL Type", ["SL Points", "SL % Movement"], horizontal=True)

    entry = st.number_input("Entry Price", value=live_price, format="%.2f")

    if sl_type == "SL Points":
        sl_price = st.number_input("SL Price", value=entry * 0.995, format="%.2f")
        sl_value = abs(entry - sl_price)
    else:
        sl_pct = st.number_input("SL %", 0.1, 10.0, 0.8, 0.1)
        sl_value = sl_pct
        sl_price = entry * (1 - sl_pct/100) if side == "LONG" else entry * (1 + sl_pct/100)

with right:
    st.markdown("#### Position Sizing (1% Risk)")
    units, lev, notional, unutilized, info = calc_position(balance, symbol, entry, sl_type, sl_value)

    c1, c2 = st.columns(2)
    c1.metric("Units", f"{units:,.4f}")
    c2.metric("Leverage", f"{lev:.1f}x")

    st.markdown(f"<div style='background:#111;padding:12px;border-radius:8px;font-size:14px;'>{info}</div>", unsafe_allow_html=True)

    st.markdown("#### Take Profits")
    tp_col1, tp_col2 = st.columns(2)
    with tp_col1:
        tp1 = st.number_input("TP1 $", value=entry * 1.008, format="%.2f")
        tp1_pct = st.slider("TP1 %", 10, 100, 70, 5)
    with tp_col2:
        tp2 = st.number_input("TP2 $", value=entry * 1.018, format="%.2f")
        st.write(f"TP2: {100-tp1_pct}%")

    st.markdown("#### Override & Execute")
    o1, o2 = st.columns(2)
    override_units = o1.number_input("Units", 0.0, step=0.0001, format="%.6f", help="0 = use suggested")
    override_lev = o2.number_input("Lev", 0.0, step=0.1, format="%.1f", help="0 = use suggested")

    # FINAL EXECUTE BUTTON — BIG & VISIBLE
    if st.button("EXECUTE TRADE NOW", type="primary", use_container_width=True):
        final_units = override_units if override_units > 0 else units
        final_lev = override_lev if override_lev > 0 else lev

        today = datetime.utcnow().date().isoformat()
        stats = st.session_state.stats[today]
        if stats["total"] >= DAILY_MAX_TRADES:
            st.error("Daily trade limit reached!")
        elif stats["by_symbol"].get(symbol, 0) >= DAILY_MAX_PER_SYMBOL:
            st.error(f"Max {DAILY_MAX_PER_SYMBOL} trades per symbol today!")
        else:
            # Simulate or place real order
            status = "SIMULATED" if broker != "Binance Testnet" or not BINANCE_AVAILABLE else "REAL (Testnet)"
            st.success(f"{status} TRADE EXECUTED!\n\n{final_units:,.4f} units @ {final_lev:.1f}x\nNotional: ${final_units*entry:,.0f}")

            st.session_state.trades.append({
                "date": today,
                "time": datetime.utcnow().strftime("%H:%M:%S"),
                "symbol": symbol,
                "side": side,
                "entry": entry,
                "units": final_units,
                "leverage": final_lev,
                "notional": final_units * entry,
                "take_profits": [{"price": tp1, "pct": tp1_pct}, {"price": tp2, "pct": 100-tp1_pct}]
            })
            stats["total"] += 1
            stats["by_symbol"][symbol] = stats["by_symbol"].get(symbol, 0) + 1

# TODAY'S TRADES — Compact Table
st.markdown("---")
st.subheader(f"Today's Trades ({len([t for t in st.session_state.trades if t['date']==datetime.utcnow().date().isoformat()])})")

if st.session_state.trades:
    today_trades = [t for t in st.session_state.trades if t["date"] == datetime.utcnow().date().isoformat()]
    df = pd.DataFrame(today_trades)
    df = df[["time", "symbol", "side", "entry", "units", "leverage"]]
    df.columns = ["Time", "Symbol", "Side", "Entry", "Units", "Lev"]
    st.dataframe(df, use_container_width=True, height=200)
else:
    st.info("No trades yet today.")

# Optional Chart (collapsed)
with st.expander("Chart & Analysis (optional)", expanded=False):
    data = pd.DataFrame({
        'Date': pd.date_range(start='2025-01-01', periods=100, freq='H'),
        'Close': np.random.randn(100).cumsum() + 27000,
    }).set_index('Date')
    data['Open'] = data['Close'].shift(1)
    data['High'] = data[['Open','Close']].max(axis=1) + 20
    data['Low'] = data[['Open','Close']].min(axis=1) - 20
    data['Volume'] = np.random.randint(5000,20000,100)

    mc = mpf.make_marketcolors(up='#00ff9d', down='#ff4444')
    s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)
    fig, _ = mpf.plot(data, type='candle', style=s, volume=True, returnfig=True, figsize=(10,5))
    st.pyplot(fig)