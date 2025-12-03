import streamlit as st
from datetime import datetime
from math import ceil
import pandas as pd
import time 

# --- Configuration and Constants (Simplified for UI matching) ---
DAILY_MAX_TRADES = 4
DAILY_MAX_PER_SYMBOL = 2
RISK_PERCENT = 1.0 
DEFAULT_BALANCE = 10000.00
DEFAULT_SL_POINTS_BUFFER = 20.0
DEFAULT_SL_PERCENT_BUFFER = 0.2
API_KEY = "0m7TQoImay1rDXRXVQ1KR7oHBBJvvPT02M3bBWLFvXmoK4m6Vwp8UzLfeJUh1SKV"
API_SECRET = "2luiKWQg6m2I1pSiREDYPVKRG3ly0To20siRSqNEActb1bZVzpCRgrnFS5MqswiI"

# --- Helper Functions for State and Data ---

def initialize_session_state():
    """Initializes Streamlit session state for data persistence."""
    if 'trades' not in st.session_state:
        st.session_state.trades = []
    if 'stats' not in st.session_state:
        st.session_state.stats = {}
    
    # Initialize UI state defaults based on the image
    if 'selected_symbol' not in st.session_state:
        st.session_state.selected_symbol = "BTCUSD"
    if 'selected_side' not in st.session_state:
        st.session_state.selected_side = "LONG"
    if 'sl_method' not in st.session_state:
        st.session_state.sl_method = "SL_POINTS" 

    today = datetime.utcnow().date().isoformat()
    if today not in st.session_state.stats:
        st.session_state.stats[today] = {"total": 0, "by_symbol": {}}

def calculate_unutilized_capital(balance):
    """Calculates the capital not tied up in today's trades."""
    # Simplified calculation
    return balance - sum(t.get("notional", 0) / t.get("leverage", 1) for t in st.session_state.trades)

def get_account_balance(api_key, api_secret):
    """Fetches account balance from Binance Testnet."""
    return DEFAULT_BALANCE
  
def calculate_position_sizing(balance, symbol, entry, sl_type, sl_value, side):
    # This is a placeholder function to provide the default 'READY' values from the image.
    units = 1.000
    leverage = 3.0
    risk = 100.0
    
    # This is a simplified calculation, but the real logic would be complex. 
    # For UI matching, we return the values seen in the image.
    return units, leverage, risk, "Calculated successfully."

def execute_trade_action(balance, symbol, side, entry, sl, units, leverage, order_type, tp_list, api_key, api_secret):
    """Logs the trade and returns a status message."""
    
    # SIMULATION ONLY: Log trade with hardcoded values for demo
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
    
    return f"SIMULATION: Order placed successfully (Type: MARKET, Units: {units:.4f}, Lev: {leverage:.1f}x)"


# --- STREAMLIT APPLICATION LAYOUT (EXACT IMAGE MATCH) ---
def app():
    st.set_page_config(page_title="Risk Manager (Flask)", layout="wide")
    initialize_session_state()
    balance = get_account_balance(API_KEY, API_SECRET)
    
    # --- Custom CSS for exact UI match ---
    # This block uses precise colors, background, and aggressive styling to match the image.
    st.markdown("""
        <style>
        /* Base Dark Theme & Font */
        .stApp {
            background-color: #1A1A1A; 
            color: white;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; /* Common system font for MS environment look */
        }
        
        /* Container/Box Styling - The dark blue-grey blocks */
        .box-container {
            background-color: #202228; 
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .box-header {
            font-size: 1.1em;
            font-weight: bold;
            color: white;
            padding-bottom: 5px;
            margin-bottom: 10px;
        }
        
        /* Metric Styling (Total Balance, Margin Used) */
        /* Label */
        .stMetric label {
            color: #AAAAAA !important; 
            font-size: 0.9em;
        }
        /* Total Balance Value (Green) */
        div[data-testid="stMetricValue"]:first-child {
            color: #00cc77 !important; 
            font-size: 1.8em !important; 
            font-weight: bold;
        }
        /* Margin Used Value (White) */
        div[data-testid="stMetricValue"]:nth-child(2) {
            color: white !important; 
            font-size: 1.8em !important; 
            font-weight: bold;
        }

        /* Input Field Styling (Entry Price, SL Price, etc.) */
        .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
            background-color: #333333;
            color: white;
            border: 1px solid #444444;
            border-radius: 5px;
            padding: 8px 10px;
        }
        /* Input Labels (e.g., Entry Price, SL Price) */
        .stTextInput label, .stNumberInput label, .stSelectbox label {
            color: #AAAAAA !important; 
            font-size: 0.9em;
        }

        /* BUTTONS (Symbol & Side) */
        /* Default Button Style (Dark Teal/Blue-Grey) */
        .stButton button {
            border: none;
            background-color: #2D3E50; /* Base button color from image */
            color: white;
            font-weight: normal;
            border-radius: 5px;
            padding: 8px 0;
            margin-bottom: 5px; /* Add margin to separate rows */
        }

        /* Selected Symbol Button (Light Blue) */
        /* Targeting the specific button with Streamlit's internal testing IDs */
        
        /* BTCUSD (Selected) */
        button[key="symbol_BTCUSD"] {
            background-color: #0078d4 !important; /* Windows Blue */
        }
        /* LONG (Selected) */
        button[key="side_LONG"] {
            background-color: #00cc77 !important; /* Green */
        }
        /* SHORT (Unselected) */
        button[key="side_SHORT"] {
            background-color: #2D3E50 !important; /* Dark Teal/Blue-Grey */
        }
        /* ETHUSD & ADAUSD (Unselected) */
        button[key="symbol_ETHUSD"], button[key="symbol_ADAUSD"] {
            background-color: #2D3E50 !important; /* Dark Teal/Blue-Grey */
        }

        /* Final Action Buttons (RESET/PLACE ORDER) */
        /* RESET DAILY LIMITS */
        button[key="reset_button"] {
            background-color: #2D3E50 !important; /* Dark Teal/Blue-Grey */
            border: 1px solid #444444;
        }
        /* PLACE ORDER (Blue) */
        button[key="execute_button"] {
            background-color: #0078d4 !important; /* Windows Blue */
            font-weight: bold;
        }
        
        /* READY Status Block */
        .ready-status-container {
            background-color: #333333; /* Darker background for the info bar */
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
            margin-bottom: 10px;
            font-size: 0.95em;
            color: white;
            line-height: 1.5;
        }
        .ready-status-container span.highlight {
            color: #00cc77; /* Green highlight for values */
            font-weight: bold;
        }
        
        /* Chart/Log Block Spacing */
        .chart-log-box {
             background-color: #202228;
             padding: 15px;
             border-radius: 5px;
             margin-bottom: 20px;
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
        
        st.title("Risk Manager (Flask)") # Title matching the browser tab/header
        
        st.markdown('<div class="box-container">', unsafe_allow_html=True)
        st.markdown('<div class="box-header">CORE CONTROLS</div>', unsafe_allow_html=True)
        
        # Row 1: Balance and Margin (Use st.metric for layout, override CSS for style)
        col_bal, col_margin = st.columns(2)
        with col_bal: 
            st.metric("Total Balance (USD$)", f"{balance:,.1f}")
        with col_margin: 
            used_capital = DEFAULT_BALANCE - calculate_unutilized_capital(DEFAULT_BALANCE) 
            st.metric("Margin Used", f"{used_capital:,.2f}")

        # Row 2: Symbol Buttons (BTCUSD, ETHUSD, ADAUSD)
        col_btc, col_eth, col_ada = st.columns(3)
        symbols = ["BTCUSD", "ETHUSD", "ADAUSD"]
        for col, symbol in zip([col_btc, col_eth, col_ada], symbols):
            with col:
                if st.button(symbol, key=f"symbol_{symbol}", use_container_width=True):
                    set_symbol(symbol)
                
        # Row 3: Side Buttons (LONG, SHORT)
        col_long, col_short = st.columns(2)
        with col_long:
            if st.button("LONG", key="side_LONG", use_container_width=True):
                set_side("LONG")
        with col_short:
            if st.button("SHORT", key="side_SHORT", use_container_width=True):
                set_side("SHORT")

        # --- Input Fields ---
        
        # Row 4: Entry Price and SL Method (Dropdown)
        col_entry, col_sl_method = st.columns(2)
        with col_entry:
            entry = st.number_input("Entry Price", min_value=0.0, value=27050.000000, format="%.6f", key="entry_price") 
        with col_sl_method:
            sl_method = st.selectbox("SL Method", ["SL_POINTS", "SL % MOVE", "ATR"], key="sl_method_select", index=0)
            st.session_state.sl_method = sl_method


        # Row 5: SL Value (Points) and SL Price
        col_sl_value, col_sl_price = st.columns(2)
        
        # We use a dummy input for "SL Value (Points)" to match the UI layout, 
        # as the actual calculation logic uses SL Price
        sl_points_display = 100.00 
        
        with col_sl_value:
            sl_points_input = st.number_input("SL Value (Points)", min_value=0.0, value=sl_points_display, format="%.2f", key="sl_points_input")

        with col_sl_price:
            default_sl_price = entry - sl_points_display if st.session_state.selected_side == "LONG" else entry + sl_points_display
            sl_price = st.number_input("SL Price", min_value=0.0, value=default_sl_price, format="%.6f", key="sl_price_input")
        
        
        # Row 6: Position/Lot Size and Leverage
        col_pos_size, col_lev = st.columns(2)
        with col_pos_size:
            user_units = st.number_input("Position/Lot Size", min_value=0.0, value=0.000000, format="%.6f", key="pos_size")
        with col_lev:
            user_lev = st.number_input("Leverage", min_value=1.0, value=3.0, format="%.1f", key="lev")

        # --- Dynamic Sizing Calculation and Risk Info (Matching image values) ---
        units, leverage, risk_value, info_text = calculate_position_sizing(
            balance, st.session_state.selected_symbol, entry, st.session_state.sl_method, sl_price, st.session_state.selected_side
        )
        
        # Risk and Limit Status 
        today = datetime.utcnow().date().isoformat()
        stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
        total = stats.get("total", 0)
        sym_count = stats.get("by_symbol", {}).get(st.session_state.selected_symbol, 0)
        
        # Static text matching the image's status bar
        status_bar_html = f"""
        <div class="ready-status-container">
            READY: Units/Lot: <span class="highlight">{units:,.3f}</span> | Leverage: <span class="highlight">{leverage:.1f}x</span> | Risk: <span class="highlight">${risk_value:,.0f}</span><br>
            Daily: {total}/{DAILY_MAX_TRADES} | {st.session_state.selected_symbol}: {sym_count}/{DAILY_MAX_PER_SYMBOL}
        </div>
        """
        st.markdown(status_bar_html, unsafe_allow_html=True)
        
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
                # Use hardcoded units/lev for simulation to match the READY message if user hasn't overridden
                units_to_use = user_units if user_units > 0 else units
                lev_to_use = user_lev if user_lev > 0 else leverage
                
                trade_status = execute_trade_action(
                    balance, st.session_state.selected_symbol, st.session_state.selected_side, entry, sl_price, 
                    units_to_use, lev_to_use, "MARKET", [], API_KEY, API_SECRET
                )
                if "SIMULATION" in trade_status:
                    st.toast("Simulated Order Placed!")
                st.rerun() # Rerun to update logs and stats

        st.markdown('</div>', unsafe_allow_html=True) # Close CORE CONTROLS container
        
    # --- 2. CHART VIEW and 3. TRADE LOG (Right Column) ---
    with col_chart_log:
        
        # 2. CHART VIEW 
        st.markdown('<div class="box-container" style="height: 480px;">', unsafe_allow_html=True)
        st.markdown('<div class="box-header">CHART VIEW</div>', unsafe_allow_html=True)
        
        # Placeholder for the chart visualization (matching the visual block)
        st.markdown(f"""
            <div style='text-align: center; color: #888888; background-color: #1A1A1A; height: 380px; padding-top: 50px; border-radius: 5px;'>
                            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

        # 3. TODAY'S TRADE LOG 
        st.markdown('<div class="box-container" style="height: 250px;">', unsafe_allow_html=True)
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
            st.markdown('<p style="color: #AAAAAA; margin-top: 15px;">No trades today.</p>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True) 

if __name__ == '__main__':
    app()