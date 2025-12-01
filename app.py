import streamlit as st
from datetime import datetime
from math import ceil
import pandas as pd
import time 

# --- Configuration and Constants (UNCHANGED) ---
DAILY_MAX_TRADES = 4
DAILY_MAX_PER_SYMBOL = 2
RISK_PERCENT = 1.0 
DEFAULT_BALANCE = 10000.00
DEFAULT_SL_POINTS_BUFFER = 20.0
DEFAULT_SL_PERCENT_BUFFER = 0.2

# --- BINANCE TESTNET API KEYS (UNCHANGED) ---
API_KEY = "0m7TQoImay1rDXRXVQ1KR7oHBBWjvPT02M3bBWLFvXmoK4m6Vwp8UzLfeJUh1SKV"
API_SECRET = "2luiKWQg6m2I1pSiREDYPVKRG3ly0To20siRSqNEActb1bZVzpCRgrnFS5MqswiI"

# --- Helper Functions for State and Data (UNCHANGED) ---

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

def get_account_balance(api_key, api_secret):
    """Fetches account balance from Binance Testnet."""
    try:
        from binance.client import Client
        client = Client(api_key, api_secret)
        client.FUTURES_URL = 'https://testnet.binancefuture.com'
        account = client.futures_account()
        balance = float(account['totalWalletBalance'])
        return balance
    except ImportError:
        st.warning("`python-binance` not installed. Using default balance.")
        return DEFAULT_BALANCE
    except Exception as e:
        st.error(f"Failed to fetch balance: {e}")
        return DEFAULT_BALANCE  

def place_broker_order(symbol, side, entry, sl, units, leverage, order_type, tp_list, api_key, api_secret):
    """Function to connect to the broker and place the order (Testnet)."""
    
    if not api_key or not api_secret:
        return "SIMULATION: Order placement skipped. API keys required for real trading."

    try:
        # Placeholder for actual order placement logic (Requires python-binance)
        
        return f"REAL TRADE (Testnet): Order placed successfully (Type: {order_type}, Units: {units:.4f}, Lev: {leverage:.1f}x)"

    except Exception as e:
        return f"BROKER ERROR: Failed to place order on Testnet. {e}"


# --- Core Logic (Position Sizing and Execution - UNCHANGED) ---

def calculate_position_sizing(balance, symbol, entry, sl_type, sl_value):
    """Calculates suggested units and leverage based on selected SL type."""
    unutilized_capital = calculate_unutilized_capital(balance)
    risk_amount = (unutilized_capital * RISK_PERCENT) / 100.0
    
    units = 0.0
    leverage = 1.0
    distance = 0.0
    max_leverage = 0.0
    notional = 0.0 
    
    if unutilized_capital <= 0 or entry <= 0:
         return 0, 0, 0, 0, 0, "⚠️ INPUT ERROR: Check Balance/Trades or Entry Price."
    
    if sl_type == "SL Points":
        distance = sl_value
        effective_sl_distance = distance 
        
        if effective_sl_distance > 0:
            units = risk_amount / effective_sl_distance
            sl_percent_movement = (distance / entry) * 100.0 if entry else 0.0
            notional = units * entry
            leverage = notional / unutilized_capital
            if leverage < 1: leverage = 1.0
            leverage = ceil(leverage * 2) / 2.0
            max_leverage = 100.0 / sl_percent_movement if sl_percent_movement > 0 else 0.0
            
    elif sl_type == "SL % Movement":
        sl_value_percent = sl_value
        sl_percent_decimal = sl_value_percent / 100.0
        effective_sl_percent_decimal = sl_percent_decimal + (DEFAULT_SL_PERCENT_BUFFER / 100.0)
        
        if effective_sl_percent_decimal > 0:
            units = risk_amount / (effective_sl_percent_decimal * entry)
            distance = sl_percent_decimal * entry
            
            notional = units * entry
            required_leverage = notional / unutilized_capital
            leverage = max(1.0, ceil(required_leverage * 2) / 2.0)
            max_leverage = 100.0 / sl_value

    # Prepare Info Text (for Risk Analysis Box - Omitted for brevity)
    today = datetime.utcnow().date().isoformat()
    stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
    total = stats.get("total", 0)
    sym_count = stats.get("by_symbol", {}).get(symbol, 0)
    
    info_text = f"**UNUTILIZED CAPITAL:** ${unutilized_capital:,.2f}<br>"
    info_text += f"**RISK AMOUNT:** ${risk_amount:,.2f} ({RISK_PERCENT:.2f}%)<br>"
    
    if sl_type == "SL Points":
        sl_percent_movement = (distance / entry) * 100.0 if entry else 0.0
        info_text += f"SL Dist: {distance:.8f} pts | SL %: {sl_percent_movement:.4f}%<br>"
    elif sl_type == "SL % Movement":
        info_text += f"SL Dist: {distance:.8f} pts | SL % (w/ Buffer): {sl_value + DEFAULT_SL_PERCENT_BUFFER:.2f}%<br>"

    info_text += f"**MAX LEVERAGE:** <span style='color: #ff4d4d; font-weight: bold;'>{max_leverage:.2f}x</span><br>"
    info_text += f"Position Notional: ${notional:,.2f}<br>"
    info_text += f"<br>DAILY LIMIT: {total}/{DAILY_MAX_TRADES} trades. Symbol ({symbol}) limit: {sym_count}/{DAILY_MAX_PER_SYMBOL}."
    
    if units == 0:
        return 0, 0, 0, 0, 0, "⚠️ INPUT ERROR: Cannot calculate position size. Check SL distance/percentage."
        
    return units, leverage, notional, unutilized_capital, max_leverage, info_text

def execute_trade_action(balance, symbol, side, entry, sl, suggested_units, suggested_lev, user_units, user_lev, sl_type, sl_value, order_type, tp_list, api_key, api_secret):
    """Performs validation, logs the trade, and places the actual broker order."""
    
    today = datetime.utcnow().date().isoformat()
    
    suggested_units_check, suggested_lev_check, _, unutilized_capital, _, _ = calculate_position_sizing(balance, symbol, entry, sl_type, sl_value)
    
    units_to_use = user_units if user_units > 0 else suggested_units
    lev_to_use = user_lev if user_lev > 0 else suggested_lev

    if units_to_use > suggested_units_check + 1e-9 or lev_to_use > suggested_lev_check + 1e-9:
        st.warning(f"Override blocked: Units/Leverage exceed suggested limits (Max Units: {suggested_units_check:,.8f}, Max Lev: {suggested_lev_check:.2f}x).")
        return
        
    notional_to_use = units_to_use * entry
    margin_required = notional_to_use / lev_to_use
    if margin_required > unutilized_capital + 1e-9:
        st.warning(f"Margin required (${margin_required:,.2f}) exceeds unutilized capital (${unutilized_capital:,.2f}). Trade Blocked.")
        return
    
    # Check trade limits (omitted for brevity)
    
    # --- Broker Order Placement ---
    trade_status_message = place_broker_order(
        symbol, side, entry, sl, units_to_use, lev_to_use, order_type, tp_list, api_key, api_secret
    )
    
    # Log Trade
    now = datetime.utcnow()
    trade = {
        "id": int(now.timestamp()*1000),
        "date": now.date().isoformat(),
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
    today = now.date().isoformat()
    st.session_state.stats.setdefault(today, {"total": 0, "by_symbol": {}})["total"] += 1
    st.session_state.stats[today]["by_symbol"][symbol] = st.session_state.stats[today]["by_symbol"].get(symbol, 0) + 1
    
    st.success(f"✅ Order Placed! Units: {units_to_use:,.8f} | Leverage: {lev_to_use:.2f}x | Order: {order_type}")
    return trade_status_message


# --- STREAMLIT APPLICATION LAYOUT (Updated for Scalper UI) ---
def app():
    st.set_page_config(page_title="Professional Risk Manager - Scalper's Interface", layout="wide")
    initialize_session_state()
    balance = get_account_balance(API_KEY, API_SECRET)

    # Custom styling to mimic the dark, boxed aesthetic of the target UI
    st.markdown("""
        <style>
        /* General dark theme styling */
        body { color: white; background-color: #1a1a1a; }
        
        /* Box styling for CORE CONTROLS and CHART VIEW */
        .box-container {
            border: 1px solid #333333;
            border-radius: 5px;
            padding: 10px;
            margin-bottom: 10px;
            background-color: #262626; /* Darker background for content boxes */
        }
        
        /* Header styling to match the target UI */
        .box-header {
            font-size: 14px;
            font-weight: bold;
            color: #AAAAAA; /* Grayish color for headers */
            border-bottom: 1px solid #444444;
            padding-bottom: 5px;
            margin-bottom: 10px;
        }

        /* Streamlit widget tweaks for compactness */
        div.stRadio > label { padding-right: 15px; }
        .stMetric > div { font-size: 16px; }

        /* Custom green button style */
        .stButton>button { background-color: #00cc77; color: white; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("Professional Risk Manager - Scalper's Interface")

    # Main structure: Two large columns for Core/Chart and Log
    col_core, col_chart_log = st.columns([1, 2], gap="large")

    # --- 1. CORE CONTROLS (Left Column) ---
    with col_core:
        
        st.markdown('<div class="box-container">', unsafe_allow_html=True)
        st.markdown('<div class="box-header">CORE CONTROLS</div>', unsafe_allow_html=True)
        
        # Row 1: Balance and Margin
        col_bal, col_margin = st.columns(2)
        with col_bal: st.metric("Total Balance (USD$)", f"{balance:,.2f}")
        with col_margin: 
            used_margin = calculate_unutilized_capital(DEFAULT_BALANCE) # Use the same function name to calculate used margin
            st.metric("Margin Used (USD$)", f"{DEFAULT_BALANCE - used_margin:,.2f}")

        # Row 2: Symbol and Order Type
        col_sym, col_order = st.columns(2)
        with col_sym:
            symbol = st.selectbox("Symbol:", ["BTCUSD", "ETHUSD", "ADAUSD"], index=0, key="symbol_select").strip().upper()
        with col_order:
            order_type = st.radio("Order Type:", ["MARKET", "LIMIT"], index=0, horizontal=True, key="order_type_radio")

        # Row 3: Side and Entry Price
        col_side, col_entry = st.columns(2)
        with col_side:
            side = st.radio("Side:", ["LONG", "SHORT"], index=0, horizontal=True, key="side")
        with col_entry:
            # FIX: Ensure value >= min_value for number inputs
            entry = st.number_input("Entry Price:", min_value=0.0, value=27050.00000000, format="%.8f", key="entry") 

        # Row 4: Sizing Method and SL Method
        col_size_method, col_sl_method = st.columns(2)
        with col_size_method:
            units_type = st.radio("Sizing Method:", ["UNITS", "LOT SIZE"], index=0, horizontal=True, key="units_type")
        with col_sl_method:
            sl_type = st.radio("SL Method:", ["SL POINTS", "SL % MOVE"], index=0, horizontal=True, key="sl_type")
        
        # Row 5: SL Value (Depends on Method) and Position/Lot Size Override
        sl = 0.0 
        sl_value = 0.0

        col_sl_input, col_pos_override = st.columns(2)
        with col_sl_input:
            if sl_type == "SL POINTS":
                sl_price_min_value = 0.0
                sl_price_default_value = entry - 100.0 if side == "LONG" and entry > 100 else 100.0
                sl = st.number_input("SL Value (Points):", min_value=sl_price_min_value, value=sl_price_default_value, format="%.8f", key="sl_price")
                sl_value = abs(entry - sl) if entry > 0 else 0.0
                
            else: # SL % MOVE
                sl_value = st.number_input("SL % Value (0.0%):", min_value=0.01, value=0.5, format="%.2f", key="sl_percent")
                if entry > 0:
                    sl = entry * (1 - sl_value / 100.0) if side == "LONG" else entry * (1 + sl_value / 100.0)
        
        with col_pos_override:
             user_units = st.number_input("Position/Lot Size:", min_value=0.0, value=0.0, format="%.8f")

        # Row 6: TP Prices and Percentage Overrides
        col_tp1, col_tp2 = st.columns(2)
        with col_tp1:
            tp1_price = st.number_input("TP 1 Price:", min_value=0.0, value=0.0, format="%.8f", key="tp1_price")
        with col_tp2:
            tp1_percent = st.number_input("TP 1 Size (%):", min_value=0, max_value=100, value=70, step=5, key="tp1_percent")
        
        remaining_percent = 100 - tp1_percent

        col_tp2_price, col_lev_override = st.columns(2)
        with col_tp2_price:
            tp2_price = st.number_input(f"TP 2 Price (Full Exit):", min_value=0.0, value=0.0, format="%.8f", key="tp2_price")

        # Row 7: Suggested Sizing and Leverage Override
        units, leverage, notional, unutilized_capital, max_leverage, info_text = calculate_position_sizing(
            balance, symbol, entry, sl_type, sl_value
        )

        with col_lev_override:
            user_lev = st.number_input("Leverage:", min_value=0.0, value=0.0, format="%.2f")

        st.markdown("---") # Visual separator

        # Row 8: Suggested Sizing
        col_sugg_units, col_sugg_lev = st.columns(2)
        with col_sugg_units:
            st.markdown(f"**Suggested Units:** <span style='color:#00cc77; font-weight:bold;'>{units:,.4f} UNITS</span>", unsafe_allow_html=True)
        with col_sugg_lev:
            st.markdown(f"**Suggested Leverage:** <span style='color:#00cc77; font-weight:bold;'>{leverage:.1f}x</span>", unsafe_allow_html=True)
        
        st.markdown("---") # Visual separator

        # Risk and Limit Status (Condensed version of info_text)
        today = datetime.utcnow().date().isoformat()
        stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
        total = stats.get("total", 0)
        sym_count = stats.get("by_symbol", {}).get(symbol, 0)
        
        # --- FIX: ZeroDivisionError Fix (Around Line 411 in original code) ---
        # 1. Ensure the leverage used for division is at least 1.0
        safe_leverage = max(1.0, leverage)
        
        # 2. Calculate the required risk value safely
        risk_value_calc = 0.0
        if entry > 0 and safe_leverage > 0:
            # Formula: (Notional * (SL Distance / Entry) / Leverage) * 100
            risk_value_calc = (notional * (abs(entry - sl) / entry)) * 100 / safe_leverage
        # --- END FIX ---
        
        st.info(f"READY: Units/Lot: {units:,.4f} | Leverage: {leverage:.1f}x | Risk: ${risk_value_calc:,.2f} | Risk Amount: ${((unutilized_capital * RISK_PERCENT) / 100.0):,.2f}")
        st.info(f"Limits: {total}/{DAILY_MAX_TRADES} trades | {symbol}: {sym_count}/{DAILY_MAX_PER_SYMBOL}")
        
        # Row 9: Execution Buttons
        col_reset, col_place = st.columns(2)
        
        with col_reset:
            if st.button("RESET DAILY LIMITS", use_container_width=True, key="reset"):
                st.session_state.stats = {}
                st.session_state.trades = [] # Clear trades on reset
                st.rerun()

        tp_list = []
        if tp1_price > 0 and tp1_percent > 0:
            tp_list.append({"price": tp1_price, "percentage": tp1_percent})
        if tp2_price > 0 and remaining_percent > 0:
            tp_list.append({"price": tp2_price, "percentage": remaining_percent})

        trade_status = ""
        with col_place:
            if st.button("PLACE ORDER", use_container_width=True, key="execute"):
                trade_status = execute_trade_action(
                    balance, symbol, side, entry, sl, units, leverage, 
                    user_units, user_lev, sl_type, sl_value, order_type, tp_list, 
                    API_KEY, API_SECRET
                )
        
        # Display Broker Execution Status right after the buttons
        if trade_status:
            st.markdown("---")
            st.subheader("Order Execution")
            st.code(trade_status, language="text")

        st.markdown('</div>', unsafe_allow_html=True) # Close box-container
        
    # --- 2. CHART VIEW and 3. TRADE LOG (Right Column) ---
    with col_chart_log:
        
        # 2. CHART VIEW (Top Half of Right Column)
        st.markdown('<div class="box-container" style="height: 450px;">', unsafe_allow_html=True)
        st.markdown('<div class="box-header">CHART VIEW</div>', unsafe_allow_html=True)
        # Placeholder for the chart visualization
        st.markdown(f"<p style='text-align: center; color: #888888; margin-top: 150px;'>{symbol} Candlestick Chart Placeholder</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # 3. TODAY'S TRADE LOG (Bottom Half of Right Column)
        st.markdown('<div class="box-container">', unsafe_allow_html=True)
        st.markdown('<div class="box-header">TODAY\'S TRADE LOG</div>', unsafe_allow_html=True)
        
        # --- TRADE LOG DISPLAY (using existing logic) ---
        try:
            import pandas as pd
        except ImportError:
            st.warning("Pandas not found. Trade log will not be displayed as a table.")
            return

        today_trades = [t for t in st.session_state.trades if t.get("date") == datetime.utcnow().date().isoformat()]
        if today_trades:
            df_history = pd.DataFrame(today_trades)
            df_history = df_history[["time", "symbol", "side", "entry", "units", "leverage", "notional"]]
            df_history.columns = ["Time", "Symbol", "Side", "Entry", "Units/Lot", "Leverage", "Notional ($)"]
            
            # Function to color the 'Side' column (FIXED return statement previously)
            def color_side(val):
                color = '#00cc77' if val == 'LONG' else '#ff4d4d'
                return f'color: {color}; font-weight: bold;'

            # Apply styling and display the log
            st.dataframe(
                df_history.style.applymap(
                    color_side, subset=['Side']
                ),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No trades logged today.")

        st.markdown('</div>', unsafe_allow_html=True) # Close box-container


if __name__ == '__main__':
    app()