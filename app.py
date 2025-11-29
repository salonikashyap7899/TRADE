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

# --- Helper Functions for State and Data ---

def initialize_session_state():
    """Initializes Streamlit session state for data persistence."""
    # Use st.session_state to hold all application data
    if 'trades' not in st.session_state:
        st.session_state.trades = []
    if 'stats' not in st.session_state:
        st.session_state.stats = {}
        
    today = datetime.utcnow().date().isoformat()
    if today not in st.session_state.stats:
        st.session_state.stats[today] = {"total": 0, "by_symbol": {}}

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
    plt.close(fig) # Important: Close the figure to free memory
    return fig

# --- Core Logic (Recalculation and Execution) ---

def recalculate_risk(entry, sl, balance, symbol):
    """Calculates suggested units and leverage (Reused PyQt logic)."""
    distance = abs(entry - sl)
    if distance == 0 or balance <= 0:
        return 0, 0, 0, "⚠️ INPUT ERROR: Check Entry, Stop Loss, and Balance."

    risk_amount = (balance * RISK_PERCENT) / 100.0
    units = risk_amount / distance
    
    notional = units * entry
    leverage = notional / balance
    if leverage < 1: leverage = 1.0
    leverage = ceil(leverage * 2) / 2.0

    current_info = f"RISK AMOUNT: ${risk_amount:,.2f} (1.00%) | SL Distance: {distance:.8f} | Position Notional: ${notional:,.2f}"
    
    today = datetime.utcnow().date().isoformat()
    stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
    total = stats.get("total", 0)
    sym_count = stats.get("by_symbol", {}).get(symbol, 0)

    current_info += f"\n\nDAILY LIMIT: {total}/{DAILY_MAX_TRADES} trades used. Symbol ({symbol}) limit: {sym_count}/{DAILY_MAX_PER_SYMBOL} used."
    
    return units, leverage, notional, current_info

def execute_trade_action(entry, sl, balance, symbol, side, suggested_units, suggested_lev, user_units, user_lev):
    """Performs validation and logs the trade (Reused PyQt logic)."""
    today = datetime.utcnow().date().isoformat()
    stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
    total = stats.get("total", 0)
    sym_count = stats.get("by_symbol", {}).get(symbol, 0)
    
    # 1. Validation Checks
    if total >= DAILY_MAX_TRADES:
        st.error(f"Daily max trades reached ({DAILY_MAX_TRADES}).")
        return
    if sym_count >= DAILY_MAX_PER_SYMBOL:
        st.error(f"Daily max trades reached for {symbol} ({DAILY_MAX_PER_SYMBOL}).")
        return

    units_to_use = user_units if user_units > 0 else suggested_units
    lev_to_use = user_lev if user_lev > 0 else suggested_lev
    
    # Check for overrides being too large (PyQt logic)
    if units_to_use > suggested_units + 1e-9:
        st.warning("Override units exceed suggested units based on 1% risk. Trade Blocked.")
        return
    if lev_to_use > suggested_lev + 1e-9:
        st.warning("Override leverage exceeds suggested leverage. Trade Blocked.")
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
        "notional": units_to_use * entry,
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

    # Custom styling for the title
    st.markdown("""
        <style>
        .stButton>button {
            background-color: #00cc77; color: white; font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #00b366;
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
        st.markdown("#### Inputs")
        balance = st.number_input("Balance ($):", min_value=1.00, value=DEFAULT_BALANCE, step=100.00, format="%.2f", key="balance")
        symbol = st.text_input("Symbol:", "BTCUSD").strip().upper()
        entry = st.number_input("Entry Price:", min_value=0.0000001, value=27050.00, format="%.8f", key="entry")
        sl = st.number_input("Stop Loss (SL):", min_value=0.0000001, value=26950.00, format="%.8f", key="sl")
        side = st.selectbox("Side:", ["LONG", "SHORT"])

        units, leverage, notional, info_text = recalculate_risk(entry, sl, balance, symbol)
        
        st.markdown("---")
        st.subheader("Suggested Position")
        st.info(f"**Suggested Units:** `{units:,.8f}`")
        st.info(f"**Suggested Leverage:** `{leverage:.2f}x`")
        
        # Info Label
        st.markdown(f"""
        <div style='border: 1px solid #00aaff; padding: 10px; background-color: #2b2b2b; border-radius: 5px; margin-top: 15px; color: #e0e0e0; font-weight: 500;'>
            {info_text.replace('\n\n', '<br><br>')}
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
            execute_trade_action(entry, sl, balance, symbol, side, units, leverage, user_units, user_lev)

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