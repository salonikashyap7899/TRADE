# Revised app.py — order-execution top-level UI + Binance Testnet price fetching
import os
import streamlit as st
from datetime import datetime
from math import ceil
import numpy as np
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt

# Try to import python-binance (optional). If missing, app will fall back to simulated price.
try:
    from binance.client import Client
    BINANCE_AVAILABLE = True
except Exception:
    BINANCE_AVAILABLE = False

# -------------------------
# Configuration / Constants
# -------------------------
DAILY_MAX_TRADES = 4
DAILY_MAX_PER_SYMBOL = 2
RISK_PERCENT = 1.0
DEFAULT_BALANCE = 10000.00
DEFAULT_SL_POINTS_BUFFER = 20.0
DEFAULT_SL_PERCENT_BUFFER = 0.2
DEFAULT_LIVE_PRICE = 27_050.00  # fallback simulation

# -------------------------
# Session State Utilities
# -------------------------
def initialize_session_state():
    if 'trades' not in st.session_state:
        st.session_state.trades = []
    if 'stats' not in st.session_state:
        st.session_state.stats = {}
    today = datetime.utcnow().date().isoformat()
    if today not in st.session_state.stats:
        st.session_state.stats[today] = {"total": 0, "by_symbol": {}}

def calculate_unutilized_capital(balance):
    today = datetime.utcnow().date().isoformat()
    today_trades = [t for t in st.session_state.trades if t.get("date") == today]
    used_capital = sum(t.get("notional", 0) / t.get("leverage", 1) for t in today_trades)
    unutilized_capital = balance - used_capital
    return max(0.0, unutilized_capital)

# -------------------------
# Broker / Market Helpers
# -------------------------
def init_binance_client(api_key, api_secret, testnet=True):
    """
    Initialize a python-binance Client for testnet (futures) if possible.
    This is optional: the app will not crash if python-binance isn't installed.
    """
    if not BINANCE_AVAILABLE:
        return None, "python-binance library not installed."
    if not api_key or not api_secret:
        return None, "No API keys provided."
    try:
        client = Client(api_key, api_secret)
        if testnet:
            # Make sure testnet endpoints are used for futures (this is commonly used pattern)
            # Note: python-binance's futures testnet handling varies depending on version.
            # You can also set environment variables or explicitly set FUTURES_URL if needed.
            client.FUTURES_URL = 'https://testnet.binancefuture.com'
        return client, None
    except Exception as e:
        return None, f"Failed to initialize Binance Client: {e}"

def fetch_live_price(symbol, broker, api_key, api_secret):
    """
    Fetch live price from the selected broker. Currently supports:
      - 'Binance Testnet' via python-binance (futures_symbol_ticker)
      - 'Simulation' fallback
      - Other brokers are placeholders
    """
    symbol = symbol.strip().upper()
    # Choose broker
    if broker == "Binance Testnet":
        client, err = init_binance_client(api_key, api_secret, testnet=True)
        if client is None:
            st.warning("Binance client unavailable (missing library or keys). Using simulated price.")
            return simulated_price()
        try:
            # Use futures (USDT-M) price endpoint
            ticker = client.futures_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            return price
        except Exception as e:
            st.warning(f"Failed to fetch Binance price for {symbol}. Using simulated price. ({e})")
            return simulated_price()
    elif broker == "Simulation":
        return simulated_price()
    else:
        # Placeholder for Delta/Meta or others — return simulated price until implemented
        st.info(f"{broker} integration is not yet implemented. Using simulated price.")
        return simulated_price()

def simulated_price():
    offset = (datetime.utcnow().minute % 10) * 0.5
    return DEFAULT_LIVE_PRICE + offset

# -------------------------
# Position Sizing Logic
# -------------------------
def calculate_position_sizing(balance, symbol, entry, sl_type, sl_value):
    unutilized_capital = calculate_unutilized_capital(balance)
    risk_amount = (unutilized_capital * RISK_PERCENT) / 100.0

    units = 0.0
    leverage = 1.0
    distance = 0.0
    max_leverage = 0.0
    notional = 0.0

    if unutilized_capital <= 0 or entry <= 0 or sl_value <= 0:
        return 0, 0, 0, 0, 0, "⚠️ INPUT ERROR: Check Balance/Trades, Entry Price, or SL distance/percentage."

    if sl_type == "SL Points":
        distance = sl_value
        effective_sl_distance = distance + DEFAULT_SL_POINTS_BUFFER
        if effective_sl_distance > 0:
            units = risk_amount / effective_sl_distance
            sl_percent_movement = (distance / entry) * 100.0
            notional = units * entry
            leverage = notional / unutilized_capital
            if leverage < 1:
                leverage = 1.0
            leverage = ceil(leverage * 2) / 2.0
            max_leverage = 100.0 / sl_percent_movement if sl_percent_movement > 0 else 0.0
    else:  # SL % Movement
        sl_value_percent = sl_value
        sl_percent_decimal = sl_value_percent / 100.0
        effective_sl_percent_decimal = sl_percent_decimal + (DEFAULT_SL_PERCENT_BUFFER / 100.0)
        if effective_sl_percent_decimal > 0:
            units = risk_amount / (effective_sl_percent_decimal * entry)
            distance = sl_percent_decimal * entry
            max_leverage = 100.0 / sl_value_percent
            leverage = max_leverage
            notional = units * entry

    today = datetime.utcnow().date().isoformat()
    stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
    total = stats.get("total", 0)
    sym_count = stats.get("by_symbol", {}).get(symbol, 0)

    info_text = f"UNUTILIZED CAPITAL: ${unutilized_capital:,.2f}<br>"
    info_text += f"RISK AMOUNT: ${risk_amount:,.2f} ({RISK_PERCENT:.2f}%)<br><br>"

    if sl_type == "SL Points":
        sl_percent_movement = (distance / entry) * 100.0
        info_text += f"SL Distance: {distance:.8f} points<br>"
        info_text += f"SL % Movement: {sl_percent_movement:.4f}%<br>"
        info_text += f"SL Points (w/ Buffer): {distance + DEFAULT_SL_POINTS_BUFFER:.8f}<br>"
        info_text += f"MAX LEVERAGE:<span style='color: #ff4d4d; font-weight: bold;'>{max_leverage:.2f}x</span><br>"
        info_text += f"Position Notional: ${notional:,.2f}<br>"
    else:
        info_text += f"SL Distance: {distance:.8f} points<br>"
        info_text += f"SL % (w/ Buffer): {sl_value + DEFAULT_SL_PERCENT_BUFFER:.2f}%<br>"
        info_text += f"MAX LEVERAGE: <span style='color: #ff4d4d; font-weight: bold;'>{max_leverage:.2f}x</span><br>"
        info_text += f"Position Notional: ${notional:,.2f}<br>"

    info_text += f"<br>DAILY LIMIT: {total}/{DAILY_MAX_TRADES} trades used. Symbol ({symbol}) limit: {sym_count}/{DAILY_MAX_PER_SYMBOL} used."
    return units, leverage, notional, unutilized_capital, max_leverage, info_text

# -------------------------
# Broker Order Placement (placeholder)
# -------------------------
def place_broker_order(symbol, side, entry, sl, units, leverage, order_type, tp_list, broker, api_key, api_secret):
    """
    Attempt to place an order with the selected broker. For now we implement a Binance Testnet example.
    Returns a human-readable status string.
    """
    if broker == "Binance Testnet":
        if not BINANCE_AVAILABLE:
            return "SIMULATION: python-binance not installed; real order not placed."
        client, err = init_binance_client(api_key, api_secret, testnet=True)
        if client is None:
            return f"SIMULATION: Binance client couldn't be initialized ({err}). No real order placed."

        try:
            order_side = 'BUY' if side == 'LONG' else 'SELL'
            quantity = float(units)
            # For safety, we place a MARKET order example (testnet); in production you'd handle quantity rounding, margins, etc.
            order = client.futures_create_order(
                symbol=symbol,
                side=order_side,
                type='MARKET',
                quantity=quantity
            )
            # NOTE: placing SL/TP and advanced conditional orders requires more API calls (and careful param handling)
            return f"REAL TRADE (Testnet): Order response id: {order.get('orderId', 'N/A')}"
        except Exception as e:
            return f"BROKER ERROR: Failed to place order on Binance Testnet. ({e})"
    else:
        # Placeholder: other broker integrations should be implemented similarly.
        return "SIMULATION: Broker integration not implemented. Order not placed."

# -------------------------
# Chart Utilities
# -------------------------
def generate_simulated_data():
    dates = pd.date_range(start='2025-01-01', periods=80, freq='H')
    base_price = 27000.00
    volatility = 50.0
    price_changes = np.random.randn(80).cumsum() * 0.1
    prices = base_price + price_changes * volatility * 10

    df = pd.DataFrame(index=dates)
    df['Close'] = prices
    df['Open'] = df['Close'].shift(1).fillna(base_price)
    df['High'] = df[['Open', 'Close']].max(axis=1) + np.random.uniform(5, 20, 80)
    df['Low'] = df[['Open', 'Close']].min(axis=1) - np.random.uniform(5, 20, 80)
    df['Volume'] = np.random.randint(5000, 15000, 80)
    return df[['Open', 'High', 'Low', 'Close', 'Volume']]

def plot_candlestick_chart(data):
    data['MA20'] = data['Close'].rolling(window=20).mean()
    mc = mpf.make_marketcolors(up='#00cc77', down='#ff4d4d', inherit=True)
    s = mpf.make_mpf_style(base_mpf_style='yahoo', marketcolors=mc, gridcolor='#222222', facecolor='#1a1a1a')
    fig, _ = mpf.plot(
        data,
        type='candle',
        style=s,
        volume=True,
        mav=(20),
        addplot=[mpf.make_addplot(data['MA20'])],
        title='BTCUSD Price Action (Simulated Data)',
        ylabel='Price (USD)',
        returnfig=True,
        figratio=(10, 6)
    )
    plt.close(fig)
    return fig

# -------------------------
# Main Streamlit App
# -------------------------
def app():
    st.set_page_config(layout="wide", page_title="Professional Risk Manager")
    initialize_session_state()

    # Header
    st.markdown("<h1 style='text-align:center;color:#00cc77;'>RISK CONTROL DASHBOARD</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # API/Broker selection at top (keys not stored in code)
    st.subheader("🔑 Broker & API Configuration")
    broker = st.selectbox("Broker:", ["Binance Testnet", "Delta Exchange (placeholder)", "Meta (placeholder)", "Simulation"])
    col1, col2 = st.columns(2)
    with col1:
        # For security, do not provide defaults here in code. Users should paste keys in UI or set env vars.
        api_key_ui = st.text_input("API Key (paste here or leave empty):", value="", type="password", key="api_key_input")
    with col2:
        api_secret_ui = st.text_input("Secret Key (paste here or leave empty):", value="", type="password", key="api_secret_input")

    # If environment variables exist, prefer them (optional)
    env_api_key = os.getenv("BINANCE_API_KEY", "")
    env_api_secret = os.getenv("BINANCE_API_SECRET", "")
    if env_api_key and env_api_secret and (not api_key_ui and not api_secret_ui):
        api_key = env_api_key
        api_secret = env_api_secret
        st.info("Using API keys from environment variables.")
    else:
        api_key = api_key_ui
        api_secret = api_secret_ui

    st.markdown("---")

    # TOP: Entire order execution area — two columns so nothing critical is off-screen
    st.subheader("🎯 Order Entry & Position Sizing (Top — no scrolling required for execution)")
    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        symbol = st.text_input("Symbol:", value="BTCUSDT").strip().upper()
        live_price = fetch_live_price(symbol, broker, api_key, api_secret)
        st.markdown(f"""
            <div style='border:2px solid #00cc77;padding:8px;border-radius:6px;background:#111;'>
                <div style='color:#bbb;font-size:13px;'>CURRENT {symbol} PRICE</div>
                <div style='color:#00cc77;font-weight:700;font-size:26px;margin-top:6px;'>{live_price:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)

        side = st.selectbox("Side:", ["LONG", "SHORT"])
        order_type = st.selectbox("Order Type:", ["MARKET ORDER", "LIMIT ORDER", "STOP LIMIT ORDER", "STOP MARKET ORDER"])

        # SL Method radio
        sl_type = st.radio("Stop Loss Method:", ["SL Points", "SL % Movement"], index=0)

        # Entry and SL inputs (entry defaults to live price to reduce scrolling)
        entry = st.number_input("Entry Price (defaults to live):", min_value=0.0000001, value=float(live_price), format="%.8f")
        if sl_type == "SL Points":
            sl_price = st.number_input("Stop Loss (price):", min_value=0.0000001, value=max(0.0000001, entry * 0.996), format="%.8f")
            sl_value = abs(entry - sl_price)
            sl = sl_price
        else:
            sl_percent = st.number_input("Stop Loss % Movement:", min_value=0.01, value=0.5, format="%.2f")
            sl_value = sl_percent
            if side == "LONG":
                sl = entry * (1 - sl_percent / 100.0)
            else:
                sl = entry * (1 + sl_percent / 100.0)

    with right_col:
        # Balance and sizing options
        balance = st.number_input("Total Balance ($):", min_value=1.00, value=DEFAULT_BALANCE, step=100.00, format="%.2f")
        units_type = st.radio("Sizing Method:", ["Position Size / Units", "Lot Size / Units"], index=0)
        # Take profit split UI
        st.markdown("#### Take Profits (TP)")
        tp1_price = st.number_input("TP1 Price:", min_value=0.0, value=entry * 1.005, format="%.8f")
        tp1_percent = st.number_input("TP1 % of Position:", min_value=0, max_value=100, value=70, step=5)
        remaining_percent = 100 - tp1_percent
        tp2_price = st.number_input("TP2 Price (remaining):", min_value=0.0, value=entry * 1.015, format="%.8f")
        st.info(f"TP2 will exit the remaining {remaining_percent}%.")

        # Suggested sizing & risk summary (calculated live)
        units, leverage, notional, unutilized_capital, max_leverage, info_text = calculate_position_sizing(
            balance, symbol, float(entry), sl_type, float(sl_value)
        )
        st.markdown("#### Suggested Position (1% Risk)")
        st.metric("Suggested Units", f"{units:,.8f}")
        st.metric("Suggested Leverage", f"{leverage:.2f}x")
        st.markdown("#### Risk Analysis")
        st.markdown(f"<div style='border:1px solid #00aaff;padding:10px;border-radius:6px;background:#222;color:#e6e6e6;'>{info_text}</div>", unsafe_allow_html=True)

        # Overrides and execute button are placed right here so the user never needs to scroll
        st.markdown("---")
        st.subheader("Manual Overrides & Execution")
        user_units = st.number_input("Override Units (0 to use suggested):", min_value=0.0, value=0.0, format="%.8f")
        user_lev = st.number_input("Override Leverage (0 to use suggested):", min_value=0.0, value=0.0, format="%.2f")

        tp_list = []
        if tp1_price > 0 and tp1_percent > 0:
            tp_list.append({"price": tp1_price, "percentage": tp1_percent})
        if tp2_price > 0 and remaining_percent > 0:
            tp_list.append({"price": tp2_price, "percentage": remaining_percent})

        if st.button("EXECUTE TRADE (PLACE ORDER)", use_container_width=True, key="execute_top"):
            execute_trade_action(
                balance, symbol, side, float(entry), float(sl), units, leverage,
                float(user_units), float(user_lev), sl_type, float(sl_value), order_type,
                tp_list, broker, api_key, api_secret
            )

    # -------------------------
    # Today's log (below top execution area)
    # -------------------------
    st.markdown("---")
    st.subheader("TODAY'S TRADE LOG")
    today_trades = [t for t in st.session_state.trades if t.get("date") == datetime.utcnow().date().isoformat()]
    if today_trades:
        df = pd.DataFrame(today_trades)
        df = df[["time", "symbol", "side", "order_type", "entry", "units", "leverage", "notional", "take_profits"]]
        df.columns = ["Time", "Symbol", "Side", "Order Type", "Entry Price", "Units", "Leverage", "Notional ($)", "TPs"]
        df['TPs'] = df['TPs'].apply(lambda x: ' / '.join([f"TP{i+1}: ${tp['price']:,.2f} ({tp['percentage']}%)" for i, tp in enumerate(x)]))
        st.dataframe(df, use_container_width=True)
    else:
        st.write("No trades logged today.")

    # -------------------------
    # Visual analysis moved to collapsible area (so not blocking execution UI)
    # -------------------------
    st.markdown("---")
    with st.expander("📊 Visual Analysis (charts) — open when needed", expanded=False):
        st.subheader("Visual Analysis (Simulated Data)")
        data = generate_simulated_data()
        fig = plot_candlestick_chart(data)
        st.pyplot(fig)

# -------------------------
# Trade execution helper (unchanged logic; logs and places broker order)
# -------------------------
def execute_trade_action(balance, symbol, side, entry, sl, suggested_units, suggested_lev, user_units, user_lev, sl_type, sl_value, order_type, tp_list, broker, api_key, api_secret):
    today = datetime.utcnow().date().isoformat()
    stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
    total = stats.get("total", 0)
    sym_count = stats.get("by_symbol", {}).get(symbol, 0)

    if total >= DAILY_MAX_TRADES:
        st.error(f"Daily max trades reached ({DAILY_MAX_TRADES}).")
        return
    if sym_count >= DAILY_MAX_PER_SYMBOL:
        st.error(f"Daily max trades reached for {symbol} ({DAILY_MAX_PER_SYMBOL}).")
        return

    units_to_use = user_units if user_units > 0 else suggested_units
    lev_to_use = user_lev if user_lev > 0 else suggested_lev

    suggested_units_check, suggested_lev_check, _, unutilized_capital, _, _ = calculate_position_sizing(balance, symbol, entry, sl_type, sl_value)

    if units_to_use > suggested_units_check + 1e-9:
        st.warning(f"Override units ({units_to_use:,.8f}) exceed suggested units ({suggested_units_check:,.8f}) based on {RISK_PERCENT}% risk. Trade Blocked.")
        return
    if lev_to_use > suggested_lev_check + 1e-9:
        st.warning(f"Override leverage ({lev_to_use:.2f}x) exceeds suggested leverage ({suggested_lev_check:.2f}x). Trade Blocked.")
        return

    notional_to_use = units_to_use * entry
    margin_required = notional_to_use / lev_to_use if lev_to_use > 0 else notional_to_use
    if margin_required > unutilized_capital + 1e-9:
        st.warning(f"Margin required (${margin_required:,.2f}) exceeds unutilized capital (${unutilized_capital:,.2f}). Trade Blocked.")
        return

    st.subheader("Broker Execution Status:")
    trade_status_message = place_broker_order(symbol, side, entry, sl, units_to_use, lev_to_use, order_type, tp_list, broker, api_key, api_secret)
    st.code(trade_status_message, language="text")

    # Log trade (simulation or real)
    now = datetime.utcnow()
    trade = {
        "id": int(now.timestamp() * 1000),
        "date": today,
        "time": now.strftime('%H:%M:%S UTC'),
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "entry": entry,
        "stop_loss": sl,
        "units": units_to_use,
        "notional": notional_to_use,
        "leverage": lev_to_use,
        "take_profits": tp_list
    }
    st.session_state.trades.append(trade)

    s = st.session_state.stats.setdefault(today, {"total": 0, "by_symbol": {}})
    s["total"] = s.get("total", 0) + 1
    s["by_symbol"][trade["symbol"]] = s["by_symbol"].get(trade["symbol"], 0) + 1
    st.success(f"✅ Trade Logged! Units: {units_to_use:,.8f} | Leverage: {lev_to_use:.2f}x | Order: {order_type}")

if __name__ == '__main__':
    app()
