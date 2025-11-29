# REVISED app.py - Crypto Exchange Style UI with Risk Control Logic
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
DEFAULT_LIVE_PRICE = 90_620.00  # Updated to match the high-value Bitcoin price in the image

# -------------------------
# Session State Utilities (Kept from original app.py)
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
# Broker / Market Helpers (Kept from original app.py)
# -------------------------
def init_binance_client(api_key, api_secret, testnet=True):
    # ... (same logic as original app.py) ...
    if not BINANCE_AVAILABLE:
        return None, "python-binance library not installed."
    if not api_key or not api_secret:
        return None, "No API keys provided."
    try:
        client = Client(api_key, api_secret)
        if testnet:
            client.FUTURES_URL = 'https://testnet.binancefuture.com'
        return client, None
    except Exception as e:
        return None, f"Failed to initialize Binance Client: {e}"

def fetch_live_price(symbol, broker, api_key, api_secret):
    symbol = symbol.strip().upper()
    if broker == "Binance Testnet":
        client, err = init_binance_client(api_key, api_secret, testnet=True)
        if client is None:
            # st.warning("Binance client unavailable (missing library or keys). Using simulated price.") # Suppress warning for clean UI
            return simulated_price()
        try:
            ticker = client.futures_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            return price
        except Exception:
            # st.warning(f"Failed to fetch Binance price for {symbol}. Using simulated price. ({e})") # Suppress warning for clean UI
            return simulated_price()
    else:
        return simulated_price()

def simulated_price():
    offset = (datetime.utcnow().minute % 10) * 0.5
    return DEFAULT_LIVE_PRICE + offset

# -------------------------
# Position Sizing Logic (Kept from original app.py)
# -------------------------
def calculate_position_sizing(balance, symbol, entry, sl_type, sl_value):
    unutilized_capital = calculate_unutilized_capital(balance)
    risk_amount = (unutilized_capital * RISK_PERCENT) / 100.0

    units = 0.0
    leverage = 1.0
    distance = 0.0
    max_leverage = 0.0
    notional = 0.0
    # ... (same logic as original app.py) ...
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

    info_text = f"RISK AMOUNT: ${risk_amount:,.2f} ({RISK_PERCENT:.2f}%)<br>"
    info_text += f"SL Distance: {distance:.8f} points<br>"
    info_text += f"Position Notional: ${notional:,.2f}<br>"
    info_text += f"MAX LEVERAGE: <span style='color: #ff4d4d; font-weight: bold;'>{max_leverage:.2f}x</span><br>"
    info_text += f"<br>DAILY LIMIT: {total}/{DAILY_MAX_TRADES} trades used. Symbol ({symbol}) limit: {sym_count}/{DAILY_MAX_PER_SYMBOL} used."
    return units, leverage, notional, unutilized_capital, max_leverage, info_text

# -------------------------
# Broker Order Placement (Kept from original app.py)
# -------------------------
def place_broker_order(symbol, side, entry, sl, units, leverage, order_type, tp_list, broker, api_key, api_secret):
    # ... (same logic as original app.py) ...
    if broker == "Binance Testnet":
        if not BINANCE_AVAILABLE:
            return "SIMULATION: python-binance not installed; real order not placed."
        client, err = init_binance_client(api_key, api_secret, testnet=True)
        if client is None:
            return f"SIMULATION: Binance client couldn't be initialized ({err}). No real order placed."

        try:
            order_side = 'BUY' if side == 'LONG' else 'SELL'
            quantity = float(units)
            order = client.futures_create_order(
                symbol=symbol,
                side=order_side,
                type='MARKET',
                quantity=quantity
            )
            return f"REAL TRADE (Testnet): Order response id: {order.get('orderId', 'N/A')}"
        except Exception as e:
            return f"BROKER ERROR: Failed to place order on Binance Testnet. ({e})"
    else:
        return "SIMULATION: Broker integration not implemented. Order not placed."

# -------------------------
# Chart Utilities (Kept from original app.py)
# -------------------------
def generate_simulated_data():
    dates = pd.date_range(start='2025-01-01', periods=80, freq='H')
    base_price = DEFAULT_LIVE_PRICE - 100.00
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
        title='BTCUSDT Price Action (Simulated)',
        ylabel='Price (USD)',
        returnfig=True,
        figratio=(10, 6)
    )
    plt.close(fig)
    return fig

# -------------------------
# Custom CSS for Binance Style
# -------------------------
BINANCE_CSS = """
<style>
/* Streamlit standard cleanup */
.stApp { background-color: #111; color: #f0f0f0; font-family: Arial, sans-serif; }
/* Hiding Streamlit's default elements for a cleaner embedded look */
header, footer { visibility: hidden; }
/* General Text Styling */
h1, h2, h3, h4, .stMarkdown { color: #f0f0f0; }
.stInfo, .stWarning { border-left: 3px solid #ffaa00; background-color: #332b1a; }
.stSuccess { border-left: 3px solid #00cc77; background-color: #1a3324; }

/* Main Trading Grid */
.trading-grid {
    display: flex;
    flex-direction: row;
    gap: 10px;
}
/* Left Column (Order Book) */
.order-book-panel {
    background-color: #1a1a1a;
    border-radius: 4px;
    padding: 10px;
    height: 90vh;
    overflow-y: auto;
}
.order-book-price-red { color: #ff4d4d; font-weight: bold; font-size: 24px; }
.order-book-price-green { color: #00cc77; font-weight: bold; font-size: 24px; }
.order-row { display: flex; justify-content: space-between; font-size: 12px; line-height: 1.5; }
.bid-row { color: #00cc77; }
.ask-row { color: #ff4d4d; }
.price-col { width: 35%; text-align: left; }
.amount-col { width: 30%; text-align: right; color: #f0f0f0; }
.total-col { width: 35%; text-align: right; color: #999; }

/* Center Column (Chart & Order Panel) */
.chart-container {
    background-color: #1a1a1a;
    border-radius: 4px;
    padding: 0;
    margin-bottom: 10px;
}
.order-panel {
    background-color: #1a1a1a;
    border-radius: 4px;
    padding: 10px;
    margin-top: 10px;
}

/* Order Panel Inputs */
.stSelectbox, .stNumberInput, .stTextInput, .stRadio > div {
    margin-bottom: 8px;
    background-color: #2b2b2b;
    border-radius: 4px;
    padding: 4px;
}
.stNumberInput input, .stTextInput input {
    background-color: #2b2b2b !important;
    color: #f0f0f0 !important;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
}
/* Order Panel Buttons (Binance-style) */
.stButton button {
    font-weight: bold;
    color: #fff !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 10px 15px !important;
}
/* Target specific buttons to apply red/green colors */
div[data-testid="stVerticalBlock"] div:nth-child(10) button { /* Targeting the first button (Long) */
    background: #00cc77 !important; 
}
div[data-testid="stVerticalBlock"] div:nth-child(11) button { /* Targeting the second button (Short) */
    background: #ff4d4d !important;
}
/* Risk Analysis Box */
.risk-analysis-box {
    border: 1px solid #00aaff;
    padding: 10px;
    border-radius: 6px;
    background: #222;
    color: #e6e6e6;
    margin-top: 10px;
    font-size: 14px;
}
.metric-box {
    background-color: #2b2b2b;
    padding: 8px;
    border-radius: 4px;
    margin-bottom: 8px;
    border-left: 3px solid #00aaff;
}
.metric-value {
    font-size: 20px;
    font-weight: bold;
    color: #f0f0f0;
}
.metric-label {
    font-size: 12px;
    color: #999;
}

/* Right Column (Trades/Movers) */
.trades-panel {
    background-color: #1a1a1a;
    border-radius: 4px;
    padding: 10px;
    height: 90vh;
    overflow-y: auto;
}
.trade-row-red { color: #ff4d4d; font-size: 12px; line-height: 1.5; }
.trade-row-green { color: #00cc77; font-size: 12px; line-height: 1.5; }
.trade-header { font-weight: bold; color: #999; font-size: 12px; margin-bottom: 5px; }
.movers-box {
    border: 1px solid #3d3d3d;
    padding: 10px;
    border-radius: 4px;
    margin-top: 10px;
}

</style>
"""

# -------------------------
# Main Streamlit App
# -------------------------
def app():
    st.set_page_config(layout="wide", page_title="Binance-Style Risk Dashboard")
    initialize_session_state()

    st.markdown(BINANCE_CSS, unsafe_allow_html=True)
    
    # Hidden API/Broker selection (since they are critical but clutter the clean UI)
    with st.container():
        st.markdown("<h4 style='color:#00cc77;'>🔑 Configuration (Hidden)</h4>", unsafe_allow_html=True)
        broker = st.selectbox("Broker:", ["Binance Testnet", "Simulation"], key="broker_select_hidden")
        api_key_ui = st.text_input("API Key:", value="", type="password", key="api_key_input_hidden")
        api_secret_ui = st.text_input("Secret Key:", value="", type="password", key="api_secret_input_hidden")
        
        env_api_key = os.getenv("BINANCE_API_KEY", "")
        env_api_secret = os.getenv("BINANCE_API_SECRET", "")
        api_key = env_api_key or api_key_ui
        api_secret = env_api_secret or api_secret_ui
        st.markdown("---")


    # --- 1. Main Trading Grid (3 Columns) ---
    left_col, center_col, right_col = st.columns([1, 2.5, 1], gap="small")

    # --- SIMULATION DATA SETUP ---
    symbol = "BTCUSDT"
    live_price = fetch_live_price(symbol, broker, api_key, api_secret)
    data = generate_simulated_data()
    
    
    # =================================================================
    # 1. LEFT COLUMN: Order Book and Price Display
    # =================================================================
    with left_col:
        st.markdown("<div class='order-book-panel'>", unsafe_allow_html=True)
        
        # Price Header
        price_color = "#ff4d4d" if live_price < DEFAULT_LIVE_PRICE else "#00cc77"
        st.markdown(f"<div style='font-size:16px; color:#f0f0f0;'>PRICE (USDT)</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:{price_color}; font-weight:bold; font-size:24px; margin-bottom:15px;'>{live_price:,.2f}</div>", unsafe_allow_html=True)
        
        # Order Book Header
        st.markdown("<div class='trade-header'>Price(USDT) | Amount(BTC) | Total</div>", unsafe_allow_html=True)
        
        # Simulated Order Book
        bids = [(live_price - i * 0.05, 0.0001 * (100 - i)) for i in range(15)]
        asks = [(live_price + i * 0.05, 0.0001 * (100 - i)) for i in range(15)]
        
        # ASKS (Red/Sell)
        for price, amount in asks:
            st.markdown(f"""
                <div class='order-row ask-row'>
                    <span class='price-col'>{price:.2f}</span>
                    <span class='amount-col'>{amount:.5f}</span>
                    <span class='total-col'>{price * amount:.2f}</span>
                </div>
            """, unsafe_allow_html=True)
            
        # Current Price Separator
        st.markdown(f"<div style='text-align:center; color:{price_color}; font-weight:bold; padding: 5px 0;'>{live_price:,.2f}</div>", unsafe_allow_html=True)

        # BIDS (Green/Buy)
        for price, amount in bids:
            st.markdown(f"""
                <div class='order-row bid-row'>
                    <span class='price-col'>{price:.2f}</span>
                    <span class='amount-col'>{amount:.5f}</span>
                    <span class='total-col'>{price * amount:.2f}</span>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)


    # =================================================================
    # 2. CENTER COLUMN: Chart and Order Panel (RISK CONTROL)
    # =================================================================
    with center_col:
        # --- Chart Area ---
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='padding:10px 15px; margin:0;'>Chart: {symbol} Perpetual</h3>", unsafe_allow_html=True)
        fig = plot_candlestick_chart(data)
        st.pyplot(fig, clear_figure=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # --- Order Panel (Risk Control UI) ---
        st.markdown("<div class='order-panel'>", unsafe_allow_html=True)
        
        # Tabs for Order Types (Simulated to look like Binance)
        col_type1, col_type2, col_type3 = st.columns([1, 1, 1.5])
        with col_type1:
            st.markdown("<div style='color:#f0f0f0; font-weight:bold; padding:5px 0; border-bottom:2px solid #ffaa00;'>Limit</div>", unsafe_allow_html=True)
        with col_type2:
            st.markdown("<div style='color:#999; padding:5px 0;'>Market</div>", unsafe_allow_html=True)
        with col_type3:
            st.markdown("<div style='color:#999; padding:5px 0;'>Stop Limit</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Order Inputs (Using your existing logic)
        side = st.selectbox("Side:", ["LONG", "SHORT"], key="side_select")
        
        # SL Method radio (placed horizontally)
        sl_type = st.radio("Stop Loss Method:", ["SL Points", "SL % Movement"], index=0, horizontal=True)

        # Inputs
        col_input1, col_input2 = st.columns(2)
        with col_input1:
            entry = st.number_input("Entry Price:", min_value=0.0000001, value=float(live_price), format="%.8f")
            
            if sl_type == "SL Points":
                sl_value_input = st.number_input("SL Points Distance:", min_value=0.0000001, value=abs(live_price * 0.004), format="%.8f")
                sl_value = sl_value_input
                if side == "LONG":
                    sl = entry - sl_value
                else:
                    sl = entry + sl_value
            else:
                sl_percent = st.number_input("Stop Loss % Movement:", min_value=0.01, value=0.5, format="%.2f")
                sl_value = sl_percent
                if side == "LONG":
                    sl = entry * (1 - sl_percent / 100.0)
                else:
                    sl = entry * (1 + sl_percent / 100.0)
            
            st.markdown(f"<div style='font-size:12px; color:#999;'>Calculated SL Price: {sl:,.8f}</div>", unsafe_allow_html=True)

        with col_input2:
            # TP Inputs (simplified for space)
            tp1_price = st.number_input("TP1 Price:", min_value=0.0, value=entry * 1.005, format="%.8f")
            tp1_percent = st.slider("TP1 % Position:", 0, 100, 70)
            remaining_percent = 100 - tp1_percent
            tp2_price = st.number_input(f"TP2 Price ({remaining_percent}%):", min_value=0.0, value=entry * 1.015, format="%.8f")
            
        # Position Sizing Logic (Risk Analysis)
        balance = st.number_input("Total Trading Balance ($):", min_value=1.00, value=DEFAULT_BALANCE, step=100.00, format="%.2f", key="balance_input")
        
        units, leverage, notional, unutilized_capital, max_leverage, info_text = calculate_position_sizing(
            balance, symbol, float(entry), sl_type, float(sl_value)
        )
        
        st.markdown("---")
        
        # Suggested Sizing Metrics
        col_met1, col_met2 = st.columns(2)
        with col_met1:
             st.markdown(f"<div class='metric-box'><div class='metric-label'>Units ({symbol})</div><div class='metric-value'>{units:,.8f}</div></div>", unsafe_allow_html=True)
        with col_met2:
             st.markdown(f"<div class='metric-box'><div class='metric-label'>Leverage (Max {max_leverage:.2f}x)</div><div class='metric-value'>{leverage:.2f}x</div></div>", unsafe_allow_html=True)

        # Risk Analysis Summary
        st.markdown(f"<div class='risk-analysis-box'>{info_text}</div>", unsafe_allow_html=True)


        # Overrides and Execution
        st.markdown("---")
        user_units = st.number_input("Override Units (0 to use suggested):", min_value=0.0, value=0.0, format="%.8f")
        user_lev = st.number_input("Override Leverage (0 to use suggested):", min_value=0.0, value=0.0, format="%.2f")

        tp_list = []
        if tp1_price > 0 and tp1_percent > 0:
            tp_list.append({"price": tp1_price, "percentage": tp1_percent})
        if tp2_price > 0 and remaining_percent > 0:
            tp_list.append({"price": tp2_price, "percentage": remaining_percent})
            
        # Execute Buttons (Use the CSS override for coloring)
        col_exec1, col_exec2 = st.columns(2)
        with col_exec1:
            if st.button(f"Buy/LONG {symbol}", use_container_width=True, key="exec_long"):
                execute_trade_action(balance, symbol, "LONG", float(entry), float(sl), units, leverage, float(user_units), float(user_lev), sl_type, float(sl_value), "LIMIT ORDER", tp_list, broker, api_key, api_secret)
        with col_exec2:
            if st.button(f"Sell/SHORT {symbol}", use_container_width=True, key="exec_short"):
                execute_trade_action(balance, symbol, "SHORT", float(entry), float(sl), units, leverage, float(user_units), float(user_lev), sl_type, float(sl_value), "LIMIT ORDER", tp_list, broker, api_key, api_secret)

        st.markdown("</div>", unsafe_allow_html=True)


    # =================================================================
    # 3. RIGHT COLUMN: Market Trades and Movers
    # =================================================================
    with right_col:
        st.markdown("<div class='trades-panel'>", unsafe_allow_html=True)

        # Market Trades Header
        st.markdown("<div style='font-size:16px; color:#f0f0f0; margin-bottom:10px;'>Market Trades</div>", unsafe_allow_html=True)
        st.markdown("<div class='trade-header'>Price(USDT) | Amount(BTC) | Time</div>", unsafe_allow_html=True)
        
        # Simulated Market Trades
        trade_count = 35
        sim_trades = []
        for i in range(trade_count):
            price_change = np.random.uniform(-0.1, 0.1)
            trade_price = live_price + price_change
            trade_amount = np.random.uniform(0.00005, 0.005)
            trade_time = (datetime.now() - pd.Timedelta(seconds=i*3)).strftime('%H:%M:%S')
            is_buy = np.random.choice([True, False], p=[0.55, 0.45]) # Slightly more buys
            
            row_class = 'trade-row-green' if is_buy else 'trade-row-red'
            
            st.markdown(f"""
                <div class='order-row {row_class}'>
                    <span class='price-col'>{trade_price:.2f}</span>
                    <span class='amount-col'>{trade_amount:.5f}</span>
                    <span class='total-col'>{trade_time}</span>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("---")
        
        # Top Movers (Simulated)
        st.markdown("<div style='font-size:16px; color:#f0f0f0; margin-bottom:10px;'>Top Movers</div>", unsafe_allow_html=True)
        st.markdown("<div class='movers-box'>", unsafe_allow_html=True)
        
        movers = [("CEI/USDT", -6.27, 2462), ("WBT/BTC", 1.89, 104), ("LINK/USDT", 4.12, 503)]
        
        for sym, change, volume in movers:
            move_color = "#00cc77" if change > 0 else "#ff4d4d"
            st.markdown(f"""
                <div style='display:flex; justify-content:space-between; margin-bottom: 5px;'>
                    <span style='color:#f0f0f0; font-weight:bold;'>{sym}</span>
                    <span style='color:{move_color}; font-weight:bold;'>{change:.2f}%</span>
                </div>
                <div style='font-size:10px; color:#999; margin-bottom:10px;'>24h Vol: {volume}M</div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


    # =================================================================
    # 4. BOTTOM BAR: Trade Log
    # =================================================================
    st.markdown("---")
    st.markdown("<div style='background-color:#1a1a1a; padding:10px; border-radius:4px;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='margin-bottom:10px;'>Open Orders & Trade Log (Bottom Bar)</h4>", unsafe_allow_html=True)
    today_trades = [t for t in st.session_state.trades if t.get("date") == datetime.utcnow().date().isoformat()]
    
    if today_trades:
        df = pd.DataFrame(today_trades)
        df = df[["time", "symbol", "side", "order_type", "entry", "units", "leverage", "notional"]]
        df.columns = ["Time (UTC)", "Symbol", "Side", "Type", "Entry Price", "Units", "Leverage", "Notional ($)"]
        st.dataframe(df, use_container_width=True, height=180)
    else:
        st.write("No trades logged today.")
        
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# Trade execution helper (unchanged logic)
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

    # Risk Over-ride Checks (Critical Risk Control Logic)
    if units_to_use > suggested_units_check + 1e-9:
        st.error(f"Override units ({units_to_use:,.8f}) exceed suggested units ({suggested_units_check:,.8f}) based on {RISK_PERCENT}% risk. Trade Blocked.")
        return
    if lev_to_use > suggested_lev_check + 1e-9:
        st.error(f"Override leverage ({lev_to_use:.2f}x) exceeds suggested leverage ({suggested_lev_check:.2f}x). Trade Blocked.")
        return

    notional_to_use = units_to_use * entry
    margin_required = notional_to_use / lev_to_use if lev_to_use > 0 else notional_to_use
    if margin_required > unutilized_capital + 1e-9:
        st.error(f"Margin required (${margin_required:,.2f}) exceeds unutilized capital (${unutilized_capital:,.2f}). Trade Blocked.")
        return

    # Broker Execution
    st.subheader("Broker Execution Status:")
    trade_status_message = place_broker_order(symbol, side, entry, sl, units_to_use, lev_to_use, order_type, tp_list, broker, api_key, api_secret)
    st.code(trade_status_message, language="text")

    # Log trade
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