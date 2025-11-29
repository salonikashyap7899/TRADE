# app.py (updated)
import streamlit as st
from datetime import datetime
from math import ceil
import numpy as np 
import pandas as pd 
import mplfinance as mpf
import matplotlib.pyplot as plt

# --- WARNING: Real API Integration Libraries ---


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

# --- Live Price Fetching (Simulated) ---
def fetch_live_price(symbol, api_key, api_secret):
    """Fetches live market price for a symbol using a broker API (simulated fallback)."""
    if not api_key or not api_secret:
        # Simulation fallback
        offset = (datetime.utcnow().minute % 10) * 0.5 
        return DEFAULT_LIVE_PRICE + offset

    try:
        offset = (datetime.utcnow().minute % 10) * 0.5 
        return DEFAULT_LIVE_PRICE + offset
        
    except Exception as e:
        return DEFAULT_LIVE_PRICE

# --- Core Logic (Position / Lot Sizing) ---
def calculate_position_sizing(balance, symbol, entry, sl_type, sl_value, sizing_method):
    """
    Calculates suggested units and leverage based on selected SL type (points or %) and
    sizing method (Position Size / Units or Lot Size / Units).

    sizing_method: "Position Size / Units" or "Lot Size / Units"
    """
    unutilized_capital = calculate_unutilized_capital(balance)
    # risk_amount is 1% of unutilized capital (RISK_PERCENT set to 1.0)
    risk_amount = (unutilized_capital * RISK_PERCENT) / 100.0
    
    units = 0.0
    leverage = 1.0
    distance = 0.0
    max_leverage = 0.0
    notional = 0.0 
    info_text = ""
    
    # Basic validation
    if unutilized_capital <= 0 or entry <= 0 or sl_value <= 0:
         return 0, 0, 0, 0, 0, "⚠️ INPUT ERROR: Check Balance/Trades, Entry Price, or SL distance/percentage."
    
    # --- SL Points branch ---
    if sl_type == "SL Points":
        distance = sl_value
        effective_sl_distance = distance + DEFAULT_SL_POINTS_BUFFER  # +20 points buffer

        # Formula (literal from your spec):
        # Lot size formula = (1% of unutilised capital) / (Sl points + 20)
        # For position sizing we compute units by: risk_amount / effective_sl_distance
        if effective_sl_distance > 0:
            units = risk_amount / effective_sl_distance
            # Position notional (approximate)
            notional = units * entry
            # leverage based on notional vs unutilized capital
            leverage = notional / unutilized_capital if unutilized_capital > 0 else 1.0
            if leverage < 1: leverage = 1.0
            # round leverage to nearest 0.5 for display
            leverage = ceil(leverage * 2) / 2.0
            # compute sl% movement for display & max leverage
            sl_percent_movement = (distance / entry) * 100.0 if entry > 0 else 0.0
            max_leverage = 100.0 / sl_percent_movement if sl_percent_movement > 0 else 0.0

    # --- SL % Movement branch ---
    elif sl_type == "SL % Movement":
        sl_value_percent = sl_value  # e.g., 0.5 (meaning 0.5%)
        sl_percent_decimal = sl_value_percent / 100.0
        effective_sl_percent_decimal = sl_percent_decimal + (DEFAULT_SL_PERCENT_BUFFER / 100.0)  # +0.2% buffer
        
        # Convert percent movement to price distance (distance in currency units)
        distance = sl_percent_decimal * entry
        effective_price_distance = effective_sl_percent_decimal * entry
        
        if effective_price_distance > 0:
            # Units = (1% of unutilised capital) / (effective % distance * entry)
            units = risk_amount / effective_price_distance
            notional = units * entry
            # For percent mode we show max leverage as 100 / sl%
            max_leverage = 100.0 / sl_value_percent if sl_value_percent > 0 else 0.0
            # Suggest leverage equal to max_leverage (you can override in UI)
            leverage = max_leverage if max_leverage > 0 else 1.0

    # If user selected "Lot Size / Units" display label as "Lot Size" but calculation remains consistent with your formulas.
    # (Both methods use the same core formulas; the UI label differs.)
    
    # Build info text for display (clear explanation of formulas + results)
    info_text += f"**UNUTILIZED CAPITAL:** ${unutilized_capital:,.2f}<br>"
    info_text += f"**RISK AMOUNT (1%):** ${risk_amount:,.2f} ({RISK_PERCENT:.2f}%)<br><br>"

    if sl_type == "SL Points":
        info_text += f"SL Distance: {distance:.8f} points<br>"
        info_text += f"Buffer Added: {DEFAULT_SL_POINTS_BUFFER} points<br>"
        info_text += f"Effective SL Distance used in denominator: {distance + DEFAULT_SL_POINTS_BUFFER:.8f}<br>"
        info_text += f"**Formula Used:** (1% of unutilised capital) / (SL points + 20)<br>"
        info_text += f"Calculated {sizing_method}: {units:,.8f} units (or lots)<br>"
        info_text += f"Position Notional (units * entry): ${notional:,.2f}<br>"
        info_text += f"**MAX LEVERAGE (from SL % movement):** {max_leverage:.2f}x<br>"

    elif sl_type == "SL % Movement":
        info_text += f"SL % Movement (user): {sl_value:.4f}%<br>"
        info_text += f"Buffer Added: {DEFAULT_SL_PERCENT_BUFFER:.2f}% -> Effective SL %: {sl_value + DEFAULT_SL_PERCENT_BUFFER:.2f}%<br>"
        info_text += f"Effective Price Distance used in denominator: {effective_price_distance:.8f} (price units)<br>"
        info_text += f"**Formula Used:** (1% of unutilised capital) / ((SL% movement + 0.2%) * entry)<br>"
        info_text += f"Calculated {sizing_method}: {units:,.8f} units (or lots)<br>"
        info_text += f"Position Notional (units * entry): ${notional:,.2f}<br>"
        info_text += f"**MAX LEVERAGE:** {max_leverage:.2f}x (100 / SL%)<br>"

    # Daily stats
    today = datetime.utcnow().date().isoformat()
    stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
    total = stats.get("total", 0)
    sym_count = stats.get("by_symbol", {}).get(symbol, 0)
    info_text += f"<br>DAILY LIMIT: {total}/{DAILY_MAX_TRADES} trades used. Symbol ({symbol}) limit: {sym_count}/{DAILY_MAX_PER_SYMBOL} used."

    return units, leverage, notional, unutilized_capital, max_leverage, info_text

# --- Broker Order Placement (placeholder) ---
def place_broker_order(symbol, side, entry, sl, units, leverage, order_type, tp_list, api_key, api_secret):
    if not api_key or not api_secret:
        return "SIMULATION: Order placement skipped. API keys required for real trading."
    # Placeholder sim
    return f"REAL TRADE (Testnet): Order placed successfully (Units: {units:.4f}, Lev: {leverage:.1f}x)"

def execute_trade_action(balance, symbol, side, entry, sl, suggested_units, suggested_lev, user_units, user_lev, sl_type, sl_value, order_type, tp_list, api_key, api_secret):
    """Performs validation, logs the trade, and places the actual broker order."""
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
    
    suggested_units_check, suggested_lev_check, _, unutilized_capital, _, _ = calculate_position_sizing(balance, symbol, entry, sl_type, sl_value, st.session_state.get("units_type", "Position Size / Units"))

    if units_to_use > suggested_units_check + 1e-9:
        st.warning(f"Override units ({units_to_use:,.8f}) exceed suggested units ({suggested_units_check:,.8f}) based on 1% risk. Trade Blocked.")
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
    trade_status_message = place_broker_order(
        symbol, side, entry, sl, units_to_use, lev_to_use, order_type, tp_list, api_key, api_secret
    )
    st.code(trade_status_message, language="text")

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

    s = st.session_state.stats.setdefault(today, {"total": 0, "by_symbol": {}})
    s["total"] = s.get("total", 0) + 1
    s["by_symbol"][trade["symbol"]] = s["by_symbol"].get(trade["symbol"], 0) + 1
    
    st.success(f"✅ Trade Logged! Units: {units_to_use:,.8f} | Leverage: {lev_to_use:.2f}x | Order: {order_type}")


# --- Chart Generation ---
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
        addplot=[mpf.make_addplot(data['MA20'])], 
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
    st.set_page_config(layout="wide", page_title="Professional Risk Manager")
    initialize_session_state()

    # --- Hide scrollbars & compact layout as requested ---
    st.markdown("""
        <style>
        /* Remove default Streamlit scrollbar (user requested NO SCROLLBAR).
           WARNING: this will hide overflow; content must fit viewport. */
        html, body, .reportview-container, .main, .block-container {
            overflow: hidden !important;
            height: 100vh;
        }
        /* Slightly reduce padding to help fit content on single page */
        .block-container {
            padding-top: 10px;
            padding-bottom: 10px;
            padding-left: 10px;
            padding-right: 10px;
        }
        .stButton>button {
            background-color: #00cc77; color: white; font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #00b366;
        }
        .live-price-box {
            border: 2px solid #00cc77; 
            padding: 8px; 
            border-radius: 5px; 
            background-color: #1a1a1a; 
            text-align: center;
        }
        .live-price-label { font-size: 13px; color: #ccc; }
        .live-price-value { font-size: 20px; font-weight: bold; color: #00cc77; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center; color: #00cc77;'>RISK CONTROL DASHBOARD</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # --- API Configuration & Live Price Section ---
    st.subheader("🔑 Broker API Configuration (Binance Testnet)")
    col_api_key, col_api_secret = st.columns(2)
    
    with col_api_key:
        api_key = st.text_input("API Key:", "", type="password", key="api_key_input")
    with col_api_secret:
        api_secret = st.text_input("Secret Key:", "", type="password", key="api_secret_input")
    
    st.markdown("---")
    st.subheader("🎯 Order Entry & Position Sizing")

    # --- Column Layout for Order Entry ---
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        symbol = st.text_input("Symbol:", "BTCUSDT").strip().upper()
        live_price = fetch_live_price(symbol, api_key, api_secret)
        st.markdown(f"""
        <div class='live-price-box'>
            <div class='live-price-label'>CURRENT {symbol} PRICE</div>
            <div class='live-price-value'>{live_price:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("#### Trade Parameters")
        side = st.selectbox("Side:", ["LONG", "SHORT"])
        order_type = st.selectbox("Order Type:", ["MARKET ORDER", "LIMIT ORDER", "STOP LIMIT ORDER", "STOP MARKET ORDER"])

    with col2:
        balance = st.number_input("Total Balance ($):", min_value=1.00, value=DEFAULT_BALANCE, step=100.00, format="%.2f", key="balance")
        entry = st.number_input("Entry Price (Live Market Price):", min_value=0.0000001, value=live_price, format="%.8f", key="entry")
        
        col_type_choice, col_sl_choice = st.columns(2)
        with col_type_choice:
            units_type = st.radio("Sizing Method:", ["Position Size / Units", "Lot Size / Units"], index=0, key="units_type")
            # store in session for execute checks
            st.session_state["units_type"] = units_type
        
        with col_sl_choice:
            sl_type = st.radio("Stop Loss Method:", ["SL Points", "SL % Movement"], index=0, key="sl_type")

        # SL Input based on SL Type
        sl = 0.0
        sl_value = 0.0

        if sl_type == "SL Points":
            sl = st.number_input("Stop Loss (SL) Price:", min_value=0.0000001, value=entry * 0.996, format="%.8f", key="sl_price")
            sl_value = abs(entry - sl)
            if sl_value == 0:
                st.warning("SL Price must be different from Entry Price.")
        else:
            sl_value = st.number_input("Stop Loss (SL) % Movement:", min_value=0.01, value=0.5, format="%.2f", key="sl_percent")
            if entry > 0:
                if side == "LONG":
                    sl = entry * (1 - sl_value / 100.0)
                else:
                    sl = entry * (1 + sl_value / 100.0)

    # --- Take Profit and Execution (compact) ---
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

    tp_list = []
    if tp1_price > 0 and tp1_percent > 0:
        tp_list.append({"price": tp1_price, "percentage": tp1_percent})
    if tp2_price > 0 and remaining_percent > 0:
        tp_list.append({"price": tp2_price, "percentage": remaining_percent})

    # --- Calculate sizing using chosen method ---
    units, leverage, notional, unutilized_capital, max_leverage, info_text = calculate_position_sizing(
        balance, symbol, entry, sl_type, sl_value, units_type
    )
    
    col_suggested, col_info_text = st.columns([1, 1], gap="large")

    with col_suggested:
        st.markdown("#### Suggested Position (1% Risk)")
        st.info(f"**Suggested {units_type}:** `{units:,.8f}`")
        st.info(f"**Suggested Leverage:** `{leverage:.2f}x`")
        if sl_type == "SL % Movement":
            st.info(f"**Max Leverage (100 / SL%):** `{max_leverage:.2f}x`")

    with col_info_text:
        st.markdown("#### Risk Analysis")
        st.markdown(f"""
        <div style='border: 1px solid #00aaff; padding: 8px; background-color: #2b2b2b; border-radius: 5px; color: #e0e0e0; font-weight: 500;'>
            {info_text}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
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

    # Visual Analysis (kept at bottom; may be clipped by no-scrollbar)
    st.markdown("---")
    st.subheader("📊 Visual Analysis (Simulated Data)")
    data = generate_simulated_data()
    fig = plot_candlestick_chart(data)
    st.pyplot(fig)

if __name__ == '__main__':
    app()
