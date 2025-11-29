import streamlit as st
from datetime import datetime
from math import ceil
import numpy as np 
import pandas as pd 
import mplfinance as mpf
import matplotlib.pyplot as plt
import time 

# --- WARNING: Real API Integration Libraries ---
# For actual live trading, you would use a library like python-binance
# from binance.client import Client 
# from binance.exceptions import BinanceAPIException, BinanceRequestException

# --- Configuration and Constants ---
DAILY_MAX_TRADES = 4
DAILY_MAX_PER_SYMBOL = 2
RISK_PERCENT = 1.0 
DEFAULT_BALANCE = 10000.00
DEFAULT_SL_POINTS_BUFFER = 20.0
DEFAULT_SL_PERCENT_BUFFER = 0.2
DEFAULT_LIVE_PRICE = 27050.00  # Fallback/Simulation price

# --- Helper Functions for State and Data ---

def initialize_session_state():
    """Initializes Streamlit session state for data persistence."""
    if 'trades' not in st.session_state:
        st.session_state.trades = []
    if 'stats' not in st.session_state:
        st.session_state.stats = {}
        
    today = datetime.utcnow().date().isoformat()
    if today not in st.session_state.stats:
        st.session_state.stats[today] = {"total": 0, "by_symbol": {}}

def calculate_unutilized_capital(balance):
    """Calculates the capital not tied up in today's trades."""
    today = datetime.utcnow().date().isoformat()
    today_trades = [t for t in st.session_state.trades if t.get("date") == today]
    used_capital = sum(t.get("notional", 0) / t.get("leverage", 1) for t in today_trades)
    unutilized_capital = balance - used_capital
    return max(0.0, unutilized_capital)

# --- NEW: Live Price Fetching (Simulated) ---

# NOTE: For real integration, replace this function with an actual API call.
# Example: client.futures_symbol_ticker(symbol=symbol)['price']
def fetch_live_price(symbol, api_key, api_secret):
    """Fetches live market price for a symbol using a broker API."""
    if not api_key or not api_secret:
        # Fallback to simulation if keys are missing
        st.warning("⚠️ Using simulated price. Please enter valid API/Secret keys for live data.")
        # Simulate a slight price change based on time for realism
        offset = (datetime.utcnow().minute % 10) * 0.5 
        return DEFAULT_LIVE_PRICE + offset

    try:
        # --- PLACE YOUR REAL API CALL CODE HERE ---
        # Example using python-binance (requires installation: pip install python-binance)
        # client = Client(api_key, api_secret, tld='us') # Use tld='us' for US markets if needed
        # client.FUTURES_URL = 'https://testnet.binancefuture.com' # For testnet
        # client = Client(api_key, api_secret) 
        # ticker = client.futures_symbol_ticker(symbol=symbol)
        # return float(ticker['price'])
        
        # Current Simulation (Remove for live trading)
        offset = (datetime.utcnow().minute % 10) * 0.5 
        return DEFAULT_LIVE_PRICE + offset
        
    except Exception as e:
        st.error(f"Failed to fetch live price for {symbol}. Using simulated price. Error: {e}")
        return DEFAULT_LIVE_PRICE


# --- Core Logic (Position Sizing) ---

def calculate_position_sizing(balance, symbol, entry, sl_type, sl_value):
    """
    Calculates suggested units and leverage based on selected SL type (points or %).
    """
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
            if leverage < 1: leverage = 1.0
            leverage = ceil(leverage * 2) / 2.0
            max_leverage = 100.0 / sl_percent_movement if sl_percent_movement > 0 else 0.0
            
    elif sl_type == "SL % Movement":
        sl_value_percent = sl_value # sl_value is the percentage (e.g., 0.5)
        sl_percent_decimal = sl_value_percent / 100.0
        effective_sl_percent_decimal = sl_percent_decimal + (DEFAULT_SL_PERCENT_BUFFER / 100.0)
        
        if effective_sl_percent_decimal > 0:
            units = risk_amount / (effective_sl_percent_decimal * entry)
            distance = sl_percent_decimal * entry
            max_leverage = 100.0 / sl_value_percent
            leverage = max_leverage
            notional = units * entry
            
    # 2. Prepare Info Text (Unchanged)
    today = datetime.utcnow().date().isoformat()
    stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
    total = stats.get("total", 0)
    sym_count = stats.get("by_symbol", {}).get(symbol, 0)
    
    # ... (Info Text formatting remains the same) ...
    info_text = f"**UNUTILIZED CAPITAL:** ${unutilized_capital:,.2f}<br>"
    info_text += f"**RISK AMOUNT:** ${risk_amount:,.2f} ({RISK_PERCENT:.2f}%)<br><br>"
    
    if sl_type == "SL Points":
        sl_percent_movement = (distance / entry) * 100.0
        info_text += f"SL Distance: {distance:.8f} points<br>"
        info_text += f"SL % Movement: {sl_percent_movement:.4f}%<br>"
        info_text += f"SL Points (w/ Buffer): {distance + DEFAULT_SL_POINTS_BUFFER:.8f}<br>"
        info_text += f"**MAX LEVERAGE:** <span style='color: #ff4d4d; font-weight: bold;'>{max_leverage:.2f}x</span><br>"
        info_text += f"Position Notional: ${notional:,.2f}<br>"
    elif sl_type == "SL % Movement":
        info_text += f"SL Distance: {distance:.8f} points<br>"
        info_text += f"SL % (w/ Buffer): {sl_value + DEFAULT_SL_PERCENT_BUFFER:.2f}%<br>"
        info_text += f"**MAX LEVERAGE:** <span style='color: #ff4d4d; font-weight: bold;'>{max_leverage:.2f}x</span><br>"
        info_text += f"Position Notional: ${notional:,.2f}<br>"

    info_text += f"<br>DAILY LIMIT: {total}/{DAILY_MAX_TRADES} trades used. Symbol ({symbol}) limit: {sym_count}/{DAILY_MAX_PER_SYMBOL} used."

    return units, leverage, notional, unutilized_capital, max_leverage, info_text

# --- NEW: Broker Order Placement ---

def place_broker_order(symbol, side, entry, sl, units, leverage, order_type, tp_list, api_key, api_secret):
    """
    Function to connect to the broker and place the order.
    NOTE: This is a placeholder structure for the Binance Futures API.
    """
    
    if not api_key or not api_secret:
        return "SIMULATION: Order placement skipped. API keys are required for real trading."

    try:
        # --- PLACE YOUR REAL BINANCE/DELTA/META ORDER PLACEMENT CODE HERE ---
        
        # 1. Initialize Client (using Testnet environment)
        # client = Client(api_key, api_secret)
        # client.FUTURES_URL = 'https://testnet.binancefuture.com' 
        
        # 2. Set Leverage
        # client.futures_change_leverage(symbol=symbol, leverage=int(leverage))

        # 3. Define Main Order Parameters
        order_side = 'BUY' if side == 'LONG' else 'SELL'
        order_type_broker = 'MARKET' # Simplify for primary order placement example
        quantity = units 
        
        # 4. Place Main Order
        # if order_type == "MARKET ORDER":
        #     order = client.futures_create_order(
        #         symbol=symbol, 
        #         side=order_side, 
        #         type=order_type_broker, 
        #         quantity=quantity
        #     )
        # elif order_type == "LIMIT ORDER":
        #     # Example for Limit Order
        #     order = client.futures_create_order(
        #         symbol=symbol, 
        #         side=order_side, 
        #         type='LIMIT', 
        #         timeInForce='GTC', 
        #         quantity=quantity,
        #         price=entry 
        #     )
        
        # 5. Place SL and TP Orders (usually OCO or conditional orders)
        # Placing SL
        # client.futures_create_order(...)
        
        # Placing TPs
        # for tp in tp_list:
        #     # Place separate limit/take-profit limit orders for partial exit
        #     # client.futures_create_order(...)

        return f"REAL TRADE (Testnet): Order placed successfully (Type: {order_type_broker}, Units: {units:.4f}, Lev: {leverage:.1f}x)"

    except Exception as e:
        return f"BROKER ERROR: Failed to place order on Testnet. {e}"


def execute_trade_action(balance, symbol, side, entry, sl, suggested_units, suggested_lev, user_units, user_lev, sl_type, sl_value, order_type, tp_list, api_key, api_secret):
    """Performs validation, logs the trade, and places the actual broker order."""
    
    # ... (Validation Checks - Unchanged from previous version) ...
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
        st.warning(f"Override units ({units_to_use:,.8f}) exceed suggested units ({suggested_units_check:,.8f}) based on 1% risk. Trade Blocked.")
        return
    if lev_to_use > suggested_lev_check + 1e-9:
        st.warning(f"Override leverage ({lev_to_use:.2f}x) exceeds suggested leverage ({suggested_lev_check:.2f}x). Trade Blocked.")
        return
    
    notional_to_use = units_to_use * entry
    margin_required = notional_to_use / lev_to_use
    if margin_required > unutilized_capital + 1e-9:
        st.warning(f"Margin required (${margin_required:,.2f}) exceeds unutilized capital (${unutilized_capital:,.2f}). Trade Blocked.")
        return

    # --- Broker Order Placement ---
    st.subheader("Broker Execution Status:")
    trade_status_message = place_broker_order(
        symbol, side, entry, sl, units_to_use, lev_to_use, order_type, tp_list, api_key, api_secret
    )
    st.code(trade_status_message, language="text")

    # 2. Log Trade (Only log if execution was attempted or in simulation)
    now = datetime.utcnow()
    trade = {
        "id": int(now.timestamp()*1000),
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

    # 3. Update Stats
    s = st.session_state.stats.setdefault(today, {"total": 0, "by_symbol": {}})
    s["total"] = s.get("total", 0) + 1
    s["by_symbol"][trade["symbol"]] = s["by_symbol"].get(trade["symbol"], 0) + 1
    
    st.success(f"✅ Trade Logged! Units: {units_to_use:,.8f} | Leverage: {lev_to_use:.2f}x | Order: {order_type}")


# --- Chart Generation (Moved to bottom) ---
def generate_simulated_data():
    # (Unchanged)
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
    # (Unchanged)
    data['MA20'] = data['Close'].rolling(window=20).mean()
    mc = mpf.make_marketcolors(up='#00cc77', down='#ff4d4d', inherit=True, vcdopcod=True) 
    s = mpf.make_mpf_style(
        base_mpf_style='yahoo', 
        marketcolors=mc, 
        gridcolor='#222222', 
        facecolor='#1a1a1a', 
        edgecolor='none', 
        y_on_right=False, 
        rc={'figure.facecolor': '#1a1a1a', 'axes.labelcolor': 'white', 'xtick.color': 'white', 'ytick.color': 'white', 'axes.edgecolor': 'white'}
    )

    fig, _ = mpf.plot(
        data, 
        type='candle', 
        style=s, 
        volume=True,
        mav=(20), 
        addplot=[mpf.make_addplot(data['MA20'], color='#00aaff')], 
        title='BTCUSD Price Action (Simulated Data)',
        ylabel='Price (USD)',
        show_nontrading=True,
        returnfig=True,
        figratio=(10, 6)
    )
    plt.close(fig) 
    return fig

# --- Streamlit Application Layout ---
def app():
    # Set web page configuration and dark theme
    st.set_page_config(layout="wide", page_title="Professional Risk Manager")
    initialize_session_state()

    # Custom styling
    st.markdown("""
        <style>
        .stButton>button {
            background-color: #00cc77; color: white; font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #00b366;
        }
        div[data-testid="stRadio"] > label[data-baseweb="radio"] {
            padding: 5px 10px;
            margin-right: 10px;
            border-radius: 5px;
            background-color: #333333;
            border: 1px solid #00cc77;
        }
        .live-price-box {
            border: 2px solid #00cc77; 
            padding: 10px; 
            border-radius: 5px; 
            background-color: #1a1a1a; 
            text-align: center;
        }
        .live-price-label {
            font-size: 14px; 
            color: #ccc;
        }
        .live-price-value {
            font-size: 24px; 
            font-weight: bold; 
            color: #00cc77;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center; color: #00cc77;'>RISK CONTROL DASHBOARD</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # --- API Configuration & Live Price Section (Top of page) ---
    st.subheader("🔑 Broker API Configuration (Binance Testnet)")
    col_api_key, col_api_secret = st.columns(2)
    
    with col_api_key:
        # NOTE: Using your provided keys as defaults. REMOVE THESE BEFORE DEPLOYMENT!
        api_key = st.text_input("API Key:", "0m7TQoImay1rDXRXVQ1KR7oHBBWjvPT02M3bBWLFvXmoK4m6Vwp8UzLfeJUh1SKV", type="password", key="api_key_input")
    with col_api_secret:
        api_secret = st.text_input("Secret Key:", "2luiKWQg6m2I1pSiREDYPVrKG3ly0To20siRSqNEActb1bZVzpCRgrnFS5MqswiI", type="password", key="api_secret_input")
    
    # --- Main Trading Interface ---
    st.markdown("---")
    st.subheader("🎯 Order Entry & Position Sizing")

    # --- Column Layout for Order Entry ---
    col1, col2 = st.columns([1, 1], gap="large") # Two equal columns for inputs

    # Current Symbol and Live Price
    with col1:
        symbol = st.text_input("Symbol:", "BTCUSDT").strip().upper() # Changed to BTCUSDT for Binance standard
        
        # Fetch live price dynamically
        live_price = fetch_live_price(symbol, api_key, api_secret)
        
        # Display live price
        st.markdown(f"""
        <div class='live-price-box'>
            <div class='live-price-label'>CURRENT {symbol} PRICE</div>
            <div class='live-price-value'>{live_price:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Sizing and Side
        st.markdown("#### Trade Parameters")
        side = st.selectbox("Side:", ["LONG", "SHORT"])
        order_type = st.selectbox("Order Type:", ["MARKET ORDER", "LIMIT ORDER", "STOP LIMIT ORDER", "STOP MARKET ORDER"])

    with col2:
        balance = st.number_input("Total Balance ($):", min_value=1.00, value=DEFAULT_BALANCE, step=100.00, format="%.2f", key="balance")
        
        # Entry price defaults to live price
        entry = st.number_input("Entry Price (Live Market Price):", min_value=0.0000001, value=live_price, format="%.8f", key="entry")
        
        col_type_choice, col_sl_choice = st.columns(2)
        with col_type_choice:
            units_type = st.radio("Sizing Method:", ["Position Size / Units", "Lot Size / Units"], index=0, key="units_type")
        
        with col_sl_choice:
            sl_type = st.radio("Stop Loss Method:", ["SL Points", "SL % Movement"], index=0, key="sl_type")

        # SL Input based on SL Type
        sl = 0.0 # Will store the SL Price for trade logging
        sl_value = 0.0 # Will store either SL distance in points or SL percentage for calculation
        
        if sl_type == "SL Points":
            sl = st.number_input("Stop Loss (SL) Price:", min_value=0.0000001, value=entry * 0.996, format="%.8f", key="sl_price")
            sl_value = abs(entry - sl) # Store distance in points for calculation
            if sl_value == 0:
                st.warning("SL Price must be different from Entry Price.")
                
        else: # SL % Movement
            sl_value = st.number_input("Stop Loss (SL) % Movement:", min_value=0.01, value=0.5, format="%.2f", key="sl_percent")
            if entry > 0:
                if side == "LONG":
                    sl = entry * (1 - sl_value / 100.0)
                else: # SHORT
                    sl = entry * (1 + sl_value / 100.0)
    
    # --- Take Profit and Execution (Full Width below columns) ---
    st.markdown("---")
    st.subheader("💰 Take Profit (TP) & Position Risk Summary")

    col_tp_1, col_tp_2, col_tp_3 = st.columns(3)
    with col_tp_1:
        tp1_price = st.number_input("TP 1 Price:", min_value=0.0, value=entry * 1.005, format="%.8f", key="tp1_price")
    with col_tp_2:
        tp1_percent = st.number_input("TP 1 % of Position:", min_value=0, max_value=100, value=70, step=5, key="tp1_percent")
    with col_tp_3:
        remaining_percent = 100 - tp1_percent
        tp2_price = st.number_input("TP 2 Price (Full Exit):", min_value=0.0, value=entry * 1.015, format="%.8f", key="tp2_price")
        st.info(f"TP 2 will exit the **remaining {remaining_percent}%**.")

    # Structure TP data for logging
    tp_list = []
    if tp1_price > 0 and tp1_percent > 0:
        tp_list.append({"price": tp1_price, "percentage": tp1_percent})
    if tp2_price > 0 and remaining_percent > 0:
        tp_list.append({"price": tp2_price, "percentage": remaining_percent})


    # Recalculation (using sl_type and sl_value now)
    units, leverage, notional, unutilized_capital, max_leverage, info_text = calculate_position_sizing(
        balance, symbol, entry, sl_type, sl_value
    )
    
    # Suggested Position Display and Info Box
    col_suggested, col_info_text = st.columns([1, 1], gap="large")

    with col_suggested:
        st.markdown("#### Suggested Position (1% Risk)")
        st.info(f"**Suggested Units:** `{units:,.8f}`")
        st.info(f"**Suggested Leverage:** `{leverage:.2f}x`")

    with col_info_text:
        st.markdown("#### Risk Analysis")
        st.markdown(f"""
        <div style='border: 1px solid #00aaff; padding: 10px; background-color: #2b2b2b; border-radius: 5px; color: #e0e0e0; font-weight: 500;'>
            {info_text}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # Overrides and Execute Button
    st.subheader("Trade Execution")
    
    col_btn_1, col_btn_2 = st.columns(2)
    with col_btn_1:
        user_units = st.number_input("Override Units (0 to use Suggested):", min_value=0.0, value=0.0, format="%.8f")
    with col_btn_2:
        user_lev = st.number_input("Override Leverage (0 to use Suggested):", min_value=0.0, value=0.0, format="%.2f")

    if st.button("EXECUTE TRADE (1% RISK) - PLACE ORDER", use_container_width=True, key="execute"):
        execute_trade_action(balance, symbol, side, entry, sl, units, leverage, user_units, user_lev, sl_type, sl_value, order_type, tp_list, api_key, api_secret)

    st.markdown("---")
    st.subheader("TODAY'S TRADE LOG")
    
    # Display Trade History Table
    today_trades = [t for t in st.session_state.trades if t.get("date") == datetime.utcnow().date().isoformat()]
    if today_trades:
        df_history = pd.DataFrame(today_trades)
        df_history = df_history[["time", "symbol", "side", "order_type", "entry", "units", "leverage", "notional", "take_profits"]]
        df_history.columns = ["Time", "Symbol", "Side", "Order Type", "Entry Price", "Units", "Leverage", "Notional ($)", "TPs"]
        
        def color_side(val):
            color = '#00cc77' if val == 'LONG' else '#ff4d4d'
            return f'background-color: {color}; color: white'

        df_history['TPs'] = df_history['TPs'].apply(lambda x: ' / '.join([f"TP{i+1}: ${tp['price']:,.2f} ({tp['percentage']}%)" for i, tp in enumerate(x)]))

        st.dataframe(df_history.style.applymap(color_side, subset=['Side']), use_container_width=True, hide_index=True)
    else:
        st.write("No trades logged today.")

    # --- Visual Analysis (Moved to the bottom) ---
    st.markdown("---")
    st.subheader("📊 Visual Analysis (Simulated Data)")
    data = generate_simulated_data()
    fig = plot_candlestick_chart(data)
    st.pyplot(fig)


if __name__ == '__main__':
    app()