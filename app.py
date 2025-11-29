import streamlit as st
from datetime import datetime
from math import ceil
import numpy as np 
import pandas as pd 
import mplfinance as mpf
import matplotlib.pyplot as plt

# --- Configuration and Constants ---
DAILY_MAX_TRADES = 4
DAILY_MAX_PER_SYMBOL = 2
RISK_PERCENT = 1.0 
DEFAULT_BALANCE = 10000.00
DEFAULT_SL_POINTS_BUFFER = 20.0
DEFAULT_SL_PERCENT_BUFFER = 0.2

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
    # Find all trades logged today
    today_trades = [t for t in st.session_state.trades if t.get("date") == today]
    
    # Sum the capital tied up (Notional / Leverage)
    used_capital = sum(t.get("notional", 0) / t.get("leverage", 1) for t in today_trades)
    
    # Unutilized capital is the total balance minus the capital used for today's trades
    unutilized_capital = balance - used_capital
    return max(0.0, unutilized_capital) # Ensure it's not negative

# --- Chart Generation (Adapted) ---

def generate_simulated_data():
    """Generates synthetic OHLCV data for demonstration."""
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
    """Plots candlestick chart using mplfinance and returns the figure."""
    data['MA20'] = data['Close'].rolling(window=20).mean()
    # Define a custom style for the dark theme integration
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

# --- Core Logic (Recalculation and Execution) ---

def calculate_position_sizing(balance, symbol, entry, sl, sl_type, sl_value, units_type):
    """
    Calculates suggested units and leverage based on selected SL type (points or %).
    Enforces risk and Max Leverage rules.
    """
    unutilized_capital = calculate_unutilized_capital(balance)
    risk_amount = (unutilized_capital * RISK_PERCENT) / 100.0
    
    units = 0.0
    leverage = 1.0
    distance = 0.0
    max_leverage = 0.0
    
    # Check for minimal inputs before calculation
    if unutilized_capital <= 0 or entry <= 0:
         return 0, 0, 0, 0, 0, "⚠️ INPUT ERROR: Check Balance/Trades or Entry Price."
    
    # 1. Calculate SL Distance (Points) and Position Units
    if sl_type == "SL Points":
        distance = abs(entry - sl)
        
        # Formula: (1% of unutilised capital) / (Sl points + 20 points)
        effective_sl_distance = distance + DEFAULT_SL_POINTS_BUFFER
        
        if effective_sl_distance > 0:
            units = risk_amount / effective_sl_distance
            
            # Calculate leverage required for this position
            notional = units * entry
            leverage = notional / unutilized_capital
            if leverage < 1: leverage = 1.0
            # Round up to the nearest 0.5x
            leverage = ceil(leverage * 2) / 2.0
            
    elif sl_type == "SL % Movement":
        
        # SL Value is a percentage (e.g., 0.5), convert to decimal for calculation (0.005)
        sl_percent_decimal = sl_value / 100.0
        
        # Formula: (1% of Unutilised capital) / (Sl% movement + 0.2%)
        effective_sl_percent_decimal = sl_percent_decimal + (DEFAULT_SL_PERCENT_BUFFER / 100.0)
        
        if effective_sl_percent_decimal > 0:
            # Position Units: Risk Amount / (Effective SL % * Entry Price)
            units = risk_amount / (effective_sl_percent_decimal * entry)
            
            # Max Leverage is calculated here: 100 / SL % movement
            max_leverage = 100.0 / sl_value
            
            # Suggested Leverage is defined as the Max Leverage
            leverage = max_leverage
            
            # Calculate notional for info text
            notional = units * entry
            
    else: # Should not happen, but a safe guard
        notional = 0.0
        units = 0.0
        leverage = 1.0
        max_leverage = 0.0


    # 2. Prepare Info Text
    today = datetime.utcnow().date().isoformat()
    stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
    total = stats.get("total", 0)
    sym_count = stats.get("by_symbol", {}).get(symbol, 0)
    
    info_text = f"**UNUTILIZED CAPITAL:** ${unutilized_capital:,.2f}<br>"
    info_text += f"**RISK AMOUNT:** ${risk_amount:,.2f} ({RISK_PERCENT:.2f}%)<br><br>"
    
    if sl_type == "SL Points":
        info_text += f"SL Distance: {distance:.8f} points<br>"
        info_text += f"SL Points (w/ Buffer): {distance + DEFAULT_SL_POINTS_BUFFER:.8f}<br>"
        info_text += f"Position Notional: ${notional:,.2f}<br>"
    elif sl_type == "SL % Movement":
        info_text += f"SL % (w/ Buffer): {sl_value + DEFAULT_SL_PERCENT_BUFFER:.2f}%<br>"
        info_text += f"**MAX LEVERAGE:** <span style='color: #ff4d4d; font-weight: bold;'>{max_leverage:.2f}x</span><br>"
        info_text += f"Position Notional: ${notional:,.2f}<br>"

    info_text += f"<br>DAILY LIMIT: {total}/{DAILY_MAX_TRADES} trades used. Symbol ({symbol}) limit: {sym_count}/{DAILY_MAX_PER_SYMBOL} used."
    
    if units == 0:
        return 0, 0, 0, 0, 0, "⚠️ INPUT ERROR: Cannot calculate position size. Check SL distance/percentage."
        
    return units, leverage, notional, unutilized_capital, max_leverage, info_text

def execute_trade_action(balance, symbol, side, entry, sl, suggested_units, suggested_lev, user_units, user_lev, sl_type, sl_value):
    """Performs validation and logs the trade."""
    today = datetime.utcnow().date().isoformat()
    stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
    total = stats.get("total", 0)
    sym_count = stats.get("by_symbol", {}).get(symbol, 0)
    
    # 1. Validation Checks (Daily & Symbol Limits)
    if total >= DAILY_MAX_TRADES:
        st.error(f"Daily max trades reached ({DAILY_MAX_TRADES}).")
        return
    if sym_count >= DAILY_MAX_PER_SYMBOL:
        st.error(f"Daily max trades reached for {symbol} ({DAILY_MAX_PER_SYMBOL}).")
        return

    units_to_use = user_units if user_units > 0 else suggested_units
    lev_to_use = user_lev if user_lev > 0 else suggested_lev
    
    # Recalculate suggested numbers for comparison
    suggested_units_check, suggested_lev_check, _, unutilized_capital, _, _ = calculate_position_sizing(balance, symbol, entry, sl, sl_type, sl_value, "")

    # Check for unit override exceeding suggested units (1% risk)
    if units_to_use > suggested_units_check + 1e-9:
        st.warning(f"Override units ({units_to_use:,.8f}) exceed suggested units ({suggested_units_check:,.8f}) based on 1% risk. Trade Blocked.")
        return
        
    # Check for leverage override exceeding suggested or max leverage
    if lev_to_use > suggested_lev_check + 1e-9:
        # suggested_lev_check already incorporates the max leverage cap
        st.warning(f"Override leverage ({lev_to_use:.2f}x) exceeds suggested leverage ({suggested_lev_check:.2f}x). Trade Blocked.")
        return
    
    # Check if the margin required for the position exceeds unutilized capital
    notional_to_use = units_to_use * entry
    margin_required = notional_to_use / lev_to_use
    if margin_required > unutilized_capital + 1e-9:
        st.warning(f"Margin required (${margin_required:,.2f}) exceeds unutilized capital (${unutilized_capital:,.2f}). Trade Blocked.")
        return
    
    # 2. Log Trade
    now = datetime.utcnow()
    trade = {
        "id": int(now.timestamp()*1000),
        "date": today,
        "time": now.strftime('%H:%M:%S UTC'),
        "symbol": symbol,
        "side": side,
        "entry": entry,
        "stop_loss": sl,
        "units": units_to_use,
        "notional": notional_to_use,
        "leverage": lev_to_use
    }

    st.session_state.trades.append(trade)

    # 3. Update Stats
    s = st.session_state.stats.setdefault(today, {"total": 0, "by_symbol": {}})
    s["total"] = s.get("total", 0) + 1
    s["by_symbol"][trade["symbol"]] = s["by_symbol"].get(trade["symbol"], 0) + 1
    
    st.success(f"✅ Trade Executed! Units: {units_to_use:,.8f} | Leverage: {lev_to_use:.2f}x")

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
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center; color: #00cc77;'>RISK CONTROL DASHBOARD</h1>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2 = st.columns([4, 6], gap="large")

    # --- Column 1: Inputs and History ---
    with col1:
        st.subheader("POSITION SIZING")
        
        # Sizing Inputs
        st.markdown("#### Trade Parameters")
        balance = st.number_input("Total Balance ($):", min_value=1.00, value=DEFAULT_BALANCE, step=100.00, format="%.2f", key="balance")
        
        col_type_choice, col_sl_choice = st.columns(2)
        with col_type_choice:
            # Position size/lot size ye 2 option rkhne hai
            units_type = st.radio("Sizing Method:", ["Position Size / Units", "Lot Size / Units"], index=0, key="units_type")
        
        with col_sl_choice:
            # same sl ke liye sl points/ sl % movement
            sl_type = st.radio("Stop Loss Method:", ["SL Points", "SL % Movement"], index=0, key="sl_type")

        symbol = st.text_input("Symbol:", "BTCUSD").strip().upper()
        entry = st.number_input("Entry Price:", min_value=0.0000001, value=27050.00, format="%.8f", key="entry")

        sl = 0.0
        sl_value = 0.0 # Will store either SL distance in points or SL percentage
        
        if sl_type == "SL Points":
            sl = st.number_input("Stop Loss (SL) Price:", min_value=0.0000001, value=26950.00, format="%.8f", key="sl_price")
            sl_value = abs(entry - sl) 
            if sl_value == 0:
                st.warning("SL Price must be different from Entry Price.")
                
        else: # SL % Movement
            sl_value = st.number_input("Stop Loss (SL) % Movement:", min_value=0.01, value=0.5, format="%.2f", key="sl_percent")
            # Calculate a dummy SL price for logging (assuming long for simplicity in price calculation)
            if entry > 0:
                sl = entry * (1 - sl_value / 100.0)
            
        side = st.selectbox("Side:", ["LONG", "SHORT"])

        # Recalculation
        units, leverage, notional, unutilized_capital, max_leverage, info_text = calculate_position_sizing(
            balance, symbol, entry, sl, sl_type, sl_value, units_type
        )
        
        st.markdown("---")
        st.subheader("Suggested Position (1% Risk)")
        
        # Max Leverage is displayed within the info box in the calculation function for better context

        st.info(f"**Suggested Units:** `{units:,.8f}`")
        st.info(f"**Suggested Leverage:** `{leverage:.2f}x`")
        
        # Info Label
        st.markdown(f"""
        <div style='border: 1px solid #00aaff; padding: 10px; background-color: #2b2b2b; border-radius: 5px; margin-top: 15px; color: #e0e0e0; font-weight: 500;'>
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

        if st.button("EXECUTE TRADE (1% RISK)", use_container_width=True, key="execute"):
            execute_trade_action(balance, symbol, side, entry, sl, units, leverage, user_units, user_lev, sl_type, sl_value)

        if st.button("RESET DAILY LIMITS", use_container_width=True, key="reset"):
            # Note: This reset only clears today's limits in the session
            st.session_state.stats[datetime.utcnow().date().isoformat()] = {"total": 0, "by_symbol": {}}
            st.session_state.trades = [t for t in st.session_state.trades if t.get("date") != datetime.utcnow().date().isoformat()]
            st.success("Today's limits and trade log have been reset.")
            st.rerun()

        st.markdown("---")
        st.subheader("TODAY'S TRADE LOG")
        
        # Display Trade History Table
        today_trades = [t for t in st.session_state.trades if t.get("date") == datetime.utcnow().date().isoformat()]
        if today_trades:
            df_history = pd.DataFrame(today_trades)
            df_history = df_history[["time", "symbol", "side", "units", "leverage", "notional"]]
            df_history.columns = ["Time", "Symbol", "Side", "Units", "Leverage", "Notional ($)"]
            
            # Apply color coding to the 'Side' column
            def color_side(val):
                color = '#00cc77' if val == 'LONG' else '#ff4d4d'
                return f'background-color: {color}; color: white'

            st.dataframe(df_history.style.applymap(color_side, subset=['Side']), use_container_width=True, hide_index=True)
        else:
            st.write("No trades logged today.")

    # --- Column 2: Chart ---
    with col2:
        st.subheader("VISUAL ANALYSIS")
        
        data = generate_simulated_data()
        fig = plot_candlestick_chart(data)
        
        # Display the chart using Streamlit
        st.pyplot(fig)


if __name__ == '__main__':
    app()