import streamlit as st
from datetime import datetime
from math import ceil
import pandas as pd
import time 

# --- Configuration and Constants ---
DAILY_MAX_TRADES = 4
DAILY_MAX_PER_SYMBOL = 2
RISK_PERCENT = 1.0 
DEFAULT_BALANCE = 10000.00
DEFAULT_SL_POINTS_BUFFER = 20.0
DEFAULT_SL_PERCENT_BUFFER = 0.2
API_KEY = "0m7TQoImay1rDXRXVQ1KR7oHBBWjvPT02M3bBWLFvXmoK4m6Vwp8UzLfeJUh1SKV"
API_SECRET = "2luiKWQg6m2I1pSiREDYPVKRG3ly0To20siRSqNEActb1bZVzpCRgrnFS5MqswiI"

# --- Helper Functions for State and Data ---
def initialize_session_state():
    """Initializes Streamlit session state for data persistence."""
    if 'trades' not in st.session_state:
        st.session_state.trades = []
    if 'stats' not in st.session_state:
        st.session_state.stats = {}
    if 'selected_symbol' not in st.session_state:
        st.session_state.selected_symbol = "BTCUSD"
    if 'selected_side' not in st.session_state:
        st.session_state.selected_side = "LONG"
    if 'sl_method' not in st.session_state:
        st.session_state.sl_method = "SL_POINTS" # Using string for consistency with Image 1 dropdown

    today = datetime.utcnow().date().isoformat()
    if today not in st.session_state.stats:
        st.session_state.stats[today] = {"total": 0, "by_symbol": {}}

def calculate_unutilized_capital(balance):
    """Calculates the capital not tied up in today's trades."""
    # Simplified calculation for UI consistency
    return balance - sum(t.get("notional", 0) / t.get("leverage", 1) for t in st.session_state.trades)

def get_account_balance(api_key, api_secret):
    """Fetches account balance from Binance Testnet."""
    return DEFAULT_BALANCE
  
def place_broker_order(symbol, side, entry, sl, units, leverage, order_type, tp_list, api_key, api_secret):
    """Function to connect to the broker and place the order (Testnet)."""
    return f"SIMULATION: Order placed successfully (Type: {order_type}, Units: {units:.4f}, Lev: {leverage:.1f}x)"

# --- Core Logic (Position Sizing and Execution) ---
def calculate_position_sizing(balance, symbol, entry, sl_type, sl_value, side):
    """Calculates suggested units and leverage based on selected SL type."""
    unutilized_capital = calculate_unutilized_capital(balance)
    risk_amount = (unutilized_capital * RISK_PERCENT) / 100.0
    
    units = 0.0
    leverage = 1.0
    distance = 0.0
    notional = 0.0 
    
    if unutilized_capital <= 0 or entry <= 0:
         return 0, 0, 0, 0, "⚠️ INPUT ERROR: Check Balance/Trades or Entry Price."
    
    # Image 1 uses 'SL_POINTS' for a point value difference, and assumes price is calculated from that
    if sl_type == "SL_POINTS": 
        # sl_value is the SL Price here, we calculate distance
        sl_price = sl_value
        distance = abs(entry - sl_price)

        if distance > 0:
            units = risk_amount / distance
            notional = units * entry
            required_leverage = notional / unutilized_capital
            leverage = max(1.0, ceil(required_leverage * 2) / 2.0)
            
    else:
        # Simplified: If the SL Method is not points, we can't calculate a position easily.
        return 0, 0, 0, 0, "⚠️ ERROR: Position sizing only available for SL_POINTS in this version."

    # Max leverage is set to a standard 5x for this simple risk calc display
    max_leverage = 5.0 
    info_text = "Calculated successfully." 
    
    if units == 0:
        return 0, 0, 0, 0, "⚠️ INPUT ERROR: Cannot calculate position size. Check SL price/distance."
        
    return units, leverage, notional, risk_amount, info_text

def execute_trade_action(balance, symbol, side, entry, sl, units, leverage, order_type, tp_list, api_key, api_secret):
    """Performs validation, logs the trade, and places the actual broker order."""
    
    # Using the suggested sizing for simplicity in this demo.
    trade_status_message = place_broker_order(
        symbol, side, entry, sl, units, leverage, 'MARKET', tp_list, api_key, api_secret
    )
    
    notional_to_use = units * entry
    now = datetime.utcnow()
    trade = {
        "id": int(now.timestamp()*1000),
        "date": now.date().isoformat(),
        "time": now.strftime('%H:%M:%S UTC'),
        "symbol": symbol,
        "side": side,
        "entry": entry,
        "stop_loss": sl,
        "units": units,
        "notional": notional_to_use,
        "leverage": leverage
    }

    st.session_state.trades.append(trade)
    today = now.date().isoformat()
    st.session_state.stats.setdefault(today, {"total": 0, "by_symbol": {}})["total"] += 1
    st.session_state.stats[today]["by_symbol"][symbol] = st.session_state.stats[today]["by_symbol"].get(symbol, 0) + 1
    
    st.success(f"✅ Order Placed! Units: {units:,.4f} | Leverage: {leverage:.1f}x")
    return trade_status_message


# --- STREAMLIT APPLICATION LAYOUT (IMAGE 1 UI) ---
def app():
    st.set_page_config(page_title="Risk Manager (Flask)", layout="wide")
    initialize_session_state()
    balance = get_account_balance(API_KEY, API_SECRET)

    # Custom CSS for dark theme and Image 1 specific buttons/blocks
    st.markdown("""
        <style>
        /* General Dark Theme */
        .stApp {
            background-color: #1A1A1A;
            color: white;
        }
        
        /* Container/Box Styling */
        .box-container {
            background-color: #202228; /* Darker block color */
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .box-header {
            font-size: 1.2em;
            font-weight: bold;
            color: white;
            padding-bottom: 5px;
            margin-bottom: 10px;
        }
        
        /* Metric/Balance Styling */
        .css-v207s3 { /* Streamlit's internal style for st.metric label */
            color: #AAAAAA; 
        }
        .css-1ht1x5f { /* Streamlit's internal style for st.metric value */
            color: #00cc77 !important; /* Green for Total Balance value */
            font-size: 2em !important;
            font-weight: bold;
        }
        
        /* Button Styling (Symbol and Side) */
        .stButton>button {
            border: 1px solid #333333;
            background-color: #333333; /* Default Button color */
            color: white;
            font-weight: normal;
            border-radius: 5px;
        }
        
        /* Highlighted/Selected Buttons (Symbol and Side) */
        .stButton.selected > button {
            background-color: #0078d4; /* Blue for selected symbol */
            color: white;
            font-weight: bold;
        }
        .stButton.selected-long > button {
            background-color: #00cc77; /* Green for LONG */
            color: white;
            font-weight: bold;
        }
        .stButton.selected-short > button {
            background-color: #ff4d4d; /* Red for SHORT */
            color: white;
            font-weight: bold;
        }
        
        /* Input Field Styling */
        .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
            background-color: #333333;
            color: white;
            border: 1px solid #444444;
            border-radius: 5px;
        }
        .stSelectbox>label {
             color: #AAAAAA !important; /* Selectbox label color */
        }

        /* Trade Log Table Styling */
        .stDataFrame {
            max-height: 200px; 
            overflow: auto;
        }

        /* Chart View Placeholder Styling */
        .chart-placeholder {
            min-height: 350px;
            background-color: #1A1A1A;
            border-radius: 5px;
            padding: 10px;
            border: 1px solid #333333;
        }
        .chart-title {
            font-size: 1.2em;
            font-weight: bold;
            color: white;
            margin-bottom: 15px;
        }
        
        </style>
    """, unsafe_allow_html=True)
    
    # --- Symbol/Side Button Logic ---
    def set_symbol(symbol):
        st.session_state.selected_symbol = symbol
        
    def set_side(side):
        st.session_state.selected_side = side

    # Main structure: Two large columns
    col_core, col_chart_log = st.columns([1, 2], gap="large")

    # --- 1. CORE CONTROLS (Left Column) ---
    with col_core:
        
        st.markdown('<div class="box-container">', unsafe_allow_html=True)
        st.markdown('<div class="box-header">CORE CONTROLS</div>', unsafe_allow_html=True)
        
        # Row 1: Balance and Margin (Using st.markdown to mimic the exact look)
        col_bal, col_margin = st.columns(2)
        with col_bal: 
            st.markdown('<div style="font-size: 1em; color: #AAAAAA;">Total Balance (USD$)</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size: 2em; color: #00cc77; font-weight: bold;">{balance:,.1f}</div>', unsafe_allow_html=True)
        with col_margin: 
            used_capital = DEFAULT_BALANCE - calculate_unutilized_capital(DEFAULT_BALANCE) 
            st.markdown('<div style="font-size: 1em; color: #AAAAAA;">Margin Used (USD$)</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size: 2em; color: white; font-weight: bold;">{used_capital:,.2f}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True) # Spacer

        # Row 2: Symbol Buttons (BTCUSD, ETHUSD, ADAUSD)
        col_btc, col_eth, col_ada = st.columns(3)
        symbols = ["BTCUSD", "ETHUSD", "ADAUSD"]
        for col, symbol in zip([col_btc, col_eth, col_ada], symbols):
            with col:
                button_class = "stButton selected" if st.session_state.selected_symbol == symbol else "stButton"
                if st.button(symbol, key=f"symbol_{symbol}", use_container_width=True):
                    set_symbol(symbol)
                # Apply custom class based on selection (Streamlit doesn't support class setting on buttons directly, 
                # but we can simulate the visual style by setting the background color of the default button)
                if st.session_state.selected_symbol == symbol:
                     st.markdown(f"<style>div[data-testid='stButton'] > button[kind='primary'][data-testid='stMarkdownContainer'] > p:nth-child(1) {{background-color: #0078d4; font-weight: bold; color: white;}}</style>", unsafe_allow_html=True)
                
        st.markdown("<br>", unsafe_allow_html=True) # Spacer

        # Row 3: Side Buttons (LONG, SHORT)
        col_long, col_short = st.columns(2)
        with col_long:
            button_class = "stButton selected-long" if st.session_state.selected_side == "LONG" else "stButton"
            if st.button("LONG", key="side_long", use_container_width=True):
                set_side("LONG")
        with col_short:
            button_class = "stButton selected-short" if st.session_state.selected_side == "SHORT" else "stButton"
            if st.button("SHORT", key="side_short", use_container_width=True):
                set_side("SHORT")

        # Dynamic styling for Side buttons (more complex, using the actual button text/key)
        if st.session_state.selected_side == "LONG":
            st.markdown(f"<style>div[data-testid='stButton'] > button[data-testid='baseButton-primary']:contains('LONG') {{background-color: #00cc77 !important; font-weight: bold; color: white;}}</style>", unsafe_allow_html=True)
        if st.session_state.selected_side == "SHORT":
            st.markdown(f"<style>div[data-testid='stButton'] > button[data-testid='baseButton-primary']:contains('SHORT') {{background-color: #ff4d4d !important; font-weight: bold; color: white;}}</style>", unsafe_allow_html=True)


        # Row 4: Entry Price and SL Method (Dropdown)
        col_entry, col_sl_method = st.columns(2)
        with col_entry:
            entry = st.number_input("Entry Price", min_value=0.0, value=27050.000000, format="%.6f", key="entry_price") 
        with col_sl_method:
            sl_method = st.selectbox("SL Method", ["SL_POINTS", "SL % MOVE", "ATR"], key="sl_method_select", index=0)
            st.session_state.sl_method = sl_method


        # Row 5: SL Value (Points) and SL Price
        col_sl_value, col_sl_price = st.columns(2)
        with col_sl_value:
            # Assuming SL Value (Points) is the raw point distance input
            sl_points_input = st.number_input("SL Value (Points)", min_value=0.0, value=100.0, format="%.2f", key="sl_points_input")

        with col_sl_price:
            # SL Price is the actual price level the trade will be closed at
            default_sl_price = entry - sl_points_input if st.session_state.selected_side == "LONG" else entry + sl_points_input
            sl_price = st.number_input("SL Price", min_value=0.0, value=default_sl_price, format="%.6f", key="sl_price_input")
        
        
        # Row 6: Position/Lot Size and Leverage
        col_pos_size, col_lev = st.columns(2)
        with col_pos_size:
            user_units = st.number_input("Position/Lot Size", min_value=0.0, value=0.000000, format="%.6f")
        with col_lev:
            user_lev = st.number_input("Leverage", min_value=1.0, value=3.0, format="%.1f")

        # --- Dynamic Sizing Calculation and Risk Info ---
        units, leverage, notional, risk_amount, info_text = calculate_position_sizing(
            balance, st.session_state.selected_symbol, entry, st.session_state.sl_method, sl_price, st.session_state.selected_side
        )
        
        # We use the user inputs for the final READY calculation for UI consistency
        final_units = user_units if user_units > 0 else units
        final_lev = user_lev if user_lev > 0 else leverage
        final_risk_value_calc = risk_amount
        
        # Risk and Limit Status 
        today = datetime.utcnow().date().isoformat()
        stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
        total = stats.get("total", 0)
        sym_count = stats.get("by_symbol", {}).get(st.session_state.selected_symbol, 0)

        st.markdown("---") 
        st.markdown('<div style="font-size: 1.1em; color: white;">', unsafe_allow_html=True)
        st.markdown(f"**READY:** Units/Lot: <span style='color:#00cc77;'>{final_units:,.3f}</span> | Leverage: <span style='color:#00cc77;'>{final_lev:.1f}x</span> | Risk: <span style='color:#00cc77;'>${final_risk_value_calc:,.0f}</span>", unsafe_allow_html=True)
        st.markdown(f"**Daily:** {total}/{DAILY_MAX_TRADES} | **{st.session_state.selected_symbol}:** {sym_count}/{DAILY_MAX_PER_SYMBOL}", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")
        
        # Row 7: Execution Buttons
        col_reset, col_place = st.columns(2)
        
        with col_reset:
            if st.button("RESET DAILY LIMITS", use_container_width=True, key="reset_button"):
                st.session_state.stats = {}
                st.session_state.trades = []
                st.rerun()

        trade_status = ""
        with col_place:
            if st.button("PLACE ORDER", use_container_width=True, key="execute_button"):
                # Use calculated or user-overridden values for trade execution
                trade_status = execute_trade_action(
                    balance, st.session_state.selected_symbol, st.session_state.selected_side, entry, sl_price, 
                    final_units, final_lev, "MARKET", [], API_KEY, API_SECRET
                )
                if "Order Placed" in trade_status:
                    st.toast(trade_status)
                else:
                    st.error(trade_status)
                st.rerun() # Rerun to update logs and stats

        st.markdown('</div>', unsafe_allow_html=True) # Close box-container
        
    # --- 2. CHART VIEW and 3. TRADE LOG (Right Column) ---
    with col_chart_log:
        
        # 2. CHART VIEW 
        st.markdown('<div class="box-container">', unsafe_allow_html=True)
        st.markdown('<div class="box-header">CHART VIEW</div>', unsafe_allow_html=True)
        
        # Placeholder for the chart visualization
        st.markdown(f"""
            <div class="chart-placeholder">
                <p class="chart-title">{st.session_state.selected_symbol} Chart</p>
                <div style='text-align: center; color: #888888; margin-top: 100px;'>
                                    </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

        # 3. TODAY'S TRADE LOG 
        st.markdown('<div class="box-container">', unsafe_allow_html=True)
        st.markdown('<div class="box-header">TODAY\'S TRADE LOG</div>', unsafe_allow_html=True)
        
        # --- TRADE LOG DISPLAY ---
        today_trades = [t for t in st.session_state.trades if t.get("date") == datetime.utcnow().date().isoformat()]
        if today_trades:
            df_history = pd.DataFrame(today_trades)
            df_history = df_history[["time", "symbol", "side", "entry", "units", "leverage"]]
            df_history.columns = ["Time", "Symbol", "Side", "Entry", "Units/Lot", "Lev"]
            
            def color_side(val):
                color = '#00cc77' if val == 'LONG' else '#ff4d4d'
                return f'color: {color}; font-weight: bold;' 

            st.dataframe(
                df_history.style.applymap(color_side, subset=['Side']),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No trades logged today.")

        st.markdown('</div>', unsafe_allow_html=True) 


if __name__ == '__main__':
    app()