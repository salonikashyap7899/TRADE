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

API_KEY = "0m7TQoImay1rDXRXVQ1KR7oHBBJvvPT02M3bBWLFvXmoK4m6Vwp8UzLfeJUh1SKV"
API_SECRET = "2luiKWQg6m2I1pSiREDYPVKRG3ly0To20siRSqNEActb1bZVzpCRgrnFS5MqswiI"


# ------------------------------------------
# SESSION STATE INITIALIZER
# ------------------------------------------
def initialize_session_state():
    if "trades" not in st.session_state:
        st.session_state.trades = []
    if "stats" not in st.session_state:
        st.session_state.stats = {}

    if "selected_symbol" not in st.session_state:
        st.session_state.selected_symbol = "BTCUSD"
    if "selected_side" not in st.session_state:
        st.session_state.selected_side = "LONG"
    if "sl_method" not in st.session_state:
        st.session_state.sl_method = "SL_POINTS"

    today = datetime.utcnow().date().isoformat()
    if today not in st.session_state.stats:
        st.session_state.stats[today] = {"total": 0, "by_symbol": {}}


# ------------------------------------------
# CAPITAL CALCULATOR
# ------------------------------------------
def calculate_unutilized_capital(balance):
    return balance - sum(
        t.get("notional", 0) / t.get("leverage", 1)
        for t in st.session_state.trades
    )


def get_account_balance(api_key, api_secret):
    return DEFAULT_BALANCE


# ------------------------------------------
# POSITION SIZING
# ------------------------------------------
def calculate_position_sizing(balance, symbol, entry, sl_type, sl_price, side):
    sl_points = abs(entry - sl_price)

    if sl_points <= 0:
        return 0, 0, 0, "SL NOT VALID"

    unutil_capital = calculate_unutilized_capital(balance)
    risk_amount = (unutil_capital * RISK_PERCENT) / 100

    units = risk_amount / (sl_points + DEFAULT_SL_POINTS_BUFFER)

    leverage = max(1, min(5, ceil(units * entry / unutil_capital)))

    return round(units, 3), leverage, round(risk_amount, 2), "Calculated successfully."


# ------------------------------------------
# ORDER EXECUTION (SIMULATION)
# ------------------------------------------
def execute_trade_action(
    balance,
    symbol,
    side,
    entry,
    sl,
    units,
    leverage,
    order_type,
    tp_list,
    api_key,
    api_secret,
):

    notional_to_use = units * entry
    now = datetime.utcnow()

    trade = {
        "id": int(now.timestamp() * 1000),
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M:%S UTC"),
        "symbol": symbol,
        "side": side,
        "entry": entry,
        "stop_loss": sl,
        "units": units,
        "notional": notional_to_use,
        "leverage": leverage,
    }

    st.session_state.trades.append(trade)

    today = now.date().isoformat()
    st.session_state.stats.setdefault(today, {"total": 0, "by_symbol": {}})[
        "total"
    ] += 1
    st.session_state.stats[today]["by_symbol"][symbol] = (
        st.session_state.stats[today]["by_symbol"].get(symbol, 0) + 1
    )

    return f"SIMULATION: Order placed successfully (Units: {units:.4f}, Lev: {leverage}x)"


# ------------------------------------------
# STREAMLIT App
# ------------------------------------------
def app():

    st.set_page_config(page_title="Risk Manager", layout="wide")
    initialize_session_state()
    balance = get_account_balance(API_KEY, API_SECRET)

    # ------------------------------------------------
    # Custom CSS UI styling
    # ------------------------------------------------
    st.markdown(
        """
        <style>
        .stApp { background-color:#1A1A1A; color:white; }
        .box-container { background:#202228; padding:15px; border-radius:5px; margin-bottom:20px; }
        .box-header { font-size:1.2em; font-weight:bold; margin-bottom:10px; }
        .ready-status-container { background:#333; padding:10px; border-radius:5px; margin:10px 0; }
        .highlight { color:#00cc77; font-weight:bold; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col_core, col_chart_log = st.columns([1, 2], gap="large")

    # ==================================================
    # LEFT COLUMN
    # ==================================================
    with col_core:

        st.title("Risk Manager (Final Updated)")

        st.markdown('<div class="box-container">', unsafe_allow_html=True)
        st.markdown(
            '<div class="box-header">CORE CONTROLS</div>', unsafe_allow_html=True
        )

        # Balance
        col_bal, col_margin = st.columns(2)
        with col_bal:
            st.metric("Total Balance", f"{balance:,.1f}")
        with col_margin:
            used = DEFAULT_BALANCE - calculate_unutilized_capital(DEFAULT_BALANCE)
            st.metric("Margin Used", f"{used:,.2f}")

        # Symbols
        col_btc, col_eth, col_ada = st.columns(3)
        for col, symbol in zip(
            [col_btc, col_eth, col_ada], ["BTCUSD", "ETHUSD", "ADAUSD"]
        ):
            with col:
                if st.button(symbol, key=f"symbol_{symbol}", use_container_width=True):
                    st.session_state.selected_symbol = symbol

        # LONG / SHORT
        col_long, col_short = st.columns(2)
        with col_long:
            if st.button("LONG", key="LONG", use_container_width=True):
                st.session_state.selected_side = "LONG"
        with col_short:
            if st.button("SHORT", key="SHORT", use_container_width=True):
                st.session_state.selected_side = "SHORT"

        # ENTRY + SL TYPE
        col_entry, col_sl_method = st.columns(2)

        with col_entry:
            entry = st.number_input(
                "Entry Price", min_value=0.0, value=27050.0, format="%.6f"
            )

        with col_sl_method:
            sl_method = st.selectbox(
                "SL Method",
                ["SL_POINTS", "SL_%_MOVE"],  # <-- SL % ADDED
                index=0,
            )
            st.session_state.sl_method = sl_method

        # SL INPUTS (Dynamic)
        col_sl_value, col_sl_price = st.columns(2)

        if sl_method == "SL_POINTS":

            with col_sl_value:
                sl_points = st.number_input(
                    "SL Value (Points)", min_value=1.0, value=100.0
                )

            with col_sl_price:
                default_sl = (
                    entry - sl_points
                    if st.session_state.selected_side == "LONG"
                    else entry + sl_points
                )
                sl_price = st.number_input(
                    "SL Price", min_value=0.0, value=default_sl, format="%.6f"
                )

        else:  # SL % MOVEMENT

            with col_sl_value:
                sl_percent = st.number_input(
                    "SL % Movement", min_value=0.1, value=1.0, format="%.2f"
                )

            sl_move = entry * (sl_percent / 100)

            with col_sl_price:
                if st.session_state.selected_side == "LONG":
                    default_sl = entry - sl_move
                else:
                    default_sl = entry + sl_move

                sl_price = st.number_input(
                    "SL Price", min_value=0.0, value=default_sl, format="%.6f"
                )

        # User Inputs
        col_pos, col_lev = st.columns(2)
        with col_pos:
            user_units = st.number_input("Position/Lot Size", min_value=0.0, value=0.0)
        with col_lev:
            user_lev = st.number_input("Leverage", min_value=1.0, value=1.0)

        # Auto sizing
        rec_units, rec_lev, risk_value, _ = calculate_position_sizing(
            balance,
            st.session_state.selected_symbol,
            entry,
            sl_method,
            sl_price,
            st.session_state.selected_side,
        )

        # Count trades
        today = datetime.utcnow().date().isoformat()
        stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
        total_today = stats["total"]
        symbol_today = stats["by_symbol"].get(st.session_state.selected_symbol, 0)

        st.markdown(
            f"""
        <div class='ready-status-container'>
        READY: Units <span class='highlight'>{rec_units}</span> |
        Leverage <span class='highlight'>{rec_lev}x</span> |
        Risk <span class='highlight'>${risk_value}</span> <br>
        Daily: {total_today}/{DAILY_MAX_TRADES} |
        {st.session_state.selected_symbol}: {symbol_today}/{DAILY_MAX_PER_SYMBOL}
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Buttons
        col_reset, col_place = st.columns(2)

        with col_reset:
            st.button(
                "RESET DAILY LIMITS (DISABLED)", disabled=True, use_container_width=True
            )

        with col_place:
            if st.button("PLACE ORDER", use_container_width=True):

                # SL mandatory
                if sl_price <= 0:
                    st.error("❌ STOP LOSS REQUIRED.")
                    st.stop()

                # Trades limit
                if total_today >= DAILY_MAX_TRADES:
                    st.error("❌ DAILY LIMIT REACHED (4 trades)")
                    st.stop()

                if symbol_today >= DAILY_MAX_PER_SYMBOL:
                    st.error("❌ SYMBOL LIMIT REACHED")
                    st.stop()

                # Restrict user overrides
                if user_units > rec_units:
                    st.error(f"❌ Quantity too high! Allowed max: {rec_units}")
                    st.stop()

                if user_lev > rec_lev:
                    st.error(f"❌ Leverage too high! Allowed max: {rec_lev}x")
                    st.stop()

                # Use recommended if empty
                final_units = user_units if user_units > 0 else rec_units
                final_lev = user_lev if user_lev > 0 else rec_lev

                execute_trade_action(
                    balance,
                    st.session_state.selected_symbol,
                    st.session_state.selected_side,
                    entry,
                    sl_price,
                    final_units,
                    final_lev,
                    "MARKET",
                    [],
                    API_KEY,
                    API_SECRET,
                )

                st.toast("Order Executed!")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ==================================================
    # RIGHT COLUMN
    # ==================================================
    with col_chart_log:

        # Chart Block
        st.markdown(
            '<div class="box-container" style="height:480px;">', unsafe_allow_html=True
        )
        st.markdown('<div class="box-header">CHART VIEW</div>', unsafe_allow_html=True)
        st.write("Chart placeholder…")
        st.markdown("</div>", unsafe_allow_html=True)

        # Trade Log
        st.markdown(
            '<div class="box-container" style="height:280px;">', unsafe_allow_html=True
        )
        st.markdown(
            '<div class="box-header">TODAY\'S TRADE LOG</div>',
            unsafe_allow_html=True,
        )

        today_trades = [
            t
            for t in st.session_state.trades
            if t["date"] == datetime.utcnow().date().isoformat()
        ]

        if today_trades:
            df = pd.DataFrame(today_trades)
            df = df[["time", "symbol", "side", "entry", "units", "leverage"]]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.write("No trades today.")

        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    app()
