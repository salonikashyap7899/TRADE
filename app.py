# app.py
import streamlit as st
from datetime import datetime
from math import ceil
import pandas as pd

# --- Configuration and Constants ---
DAILY_MAX_TRADES = 4
DAILY_MAX_PER_SYMBOL = 2
RISK_PERCENT = 1.0  # 1% default
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
        st.session_state.sl_method = "POINTS"
    if "sizing_method" not in st.session_state:
        st.session_state.sizing_method = "POSITION"  # or "LOT"
    if "use_manual" not in st.session_state:
        st.session_state.use_manual = False


# ------------------------------------------
# CAPITAL CALCULATOR
# ------------------------------------------
def calculate_unutilized_capital(balance):
    # sum notional/leverage for active trades
    return balance - sum(t.get("notional", 0) / max(1, t.get("leverage", 1)) for t in st.session_state.trades)


def get_account_balance(api_key, api_secret):
    # replace with broker API call as needed
    return DEFAULT_BALANCE


# ------------------------------------------
# POSITION SIZING (1% risk default)
# ------------------------------------------
def calculate_position_sizing(balance, entry, sl_price):
    sl_points = abs(entry - sl_price)
    if sl_points <= 0:
        return 0.0, 1, 0.0, "INVALID SL"

    unutil_capital = calculate_unutilized_capital(balance)
    if unutil_capital <= 0:
        return 0.0, 1, 0.0, "NO CAPITAL"

    risk_amount = (unutil_capital * RISK_PERCENT) / 100.0
    # units = risk / (sl_points * price-per-unit) — approximate using entry as price-per-unit
    # to keep unit scale reasonable, we use units = risk_amount / (sl_points)
    # then notional = units * entry, leverage suggested to fit notional in capital (ceil to integer)
    units = risk_amount / max(1e-9, sl_points)
    if units <= 0:
        return 0.0, 1, 0.0, "TOO SMALL"

    # naive leverage suggestion: ensure notional/lev <= unutil_capital  => lev >= notional / unutil_capital
    notional = units * entry
    suggested_lev = max(1, ceil((notional / unutil_capital) if unutil_capital > 0 else 1))
    # clamp suggested leverage to reasonable max (example 50)
    suggested_lev = min(suggested_lev, 50)

    return round(units, 6), suggested_lev, round(risk_amount, 2), "OK"


# ------------------------------------------
# ORDER EXECUTION (SIMULATION)
# ------------------------------------------
def execute_trade_action(balance, symbol, side, entry, sl, units, leverage, order_type, tp1, tp2):
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
        "tp1": tp1,
        "tp2": tp2,
        "units": units,
        "notional": notional_to_use,
        "leverage": leverage,
    }

    st.session_state.trades.append(trade)

    today = now.date().isoformat()
    st.session_state.stats.setdefault(today, {"total": 0, "by_symbol": {}})["total"] += 1
    st.session_state.stats[today]["by_symbol"][symbol] = st.session_state.stats[today]["by_symbol"].get(symbol, 0) + 1

    return f"SIMULATION: Order placed (units={units:.6f}, lev={leverage}x)"


# ------------------------------------------
# STREAMLIT App
# ------------------------------------------
def app():
    st.set_page_config(page_title="Risk Manager — Single Page", layout="wide")
    initialize_session_state()
    balance = get_account_balance(API_KEY, API_SECRET)

    # --- Optional: load external styles.css if you want to use it ---
    # If you keep styles.css in the same folder and want to inject it:
    # try:
    #     with open("styles.css") as f:
    #         st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    # except FileNotFoundError:
    #     pass

    # Inline minimal CSS to keep controls compact
    st.markdown(
        """
        <style>
        .stApp { background-color:#0b0f12; color:#e6e6e6; }
        .compact { padding:6px; margin:0; }
        .status { background:#071921; padding:8px; border-radius:6px; border:1px solid #0b5d7a; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # layout: left control column (compact single-page), right log/chart
    col_ctrl, col_right = st.columns([1, 1], gap="large")

    # --------------------------
    # LEFT: order execution area
    # --------------------------
    with col_ctrl:
        st.header("Order Entry")

        # Row 1: Symbol (toggle), Side, Order type
        # In production: replace symbol list with broker API symbol list
        symbols = ["BTCUSD", "ETHUSD", "ADAUSD"]  # fetched from broker API in future
        sym_col, side_col, ord_col = st.columns([2, 1, 1])
        with sym_col:
            st.session_state.selected_symbol = st.radio("", symbols, index=symbols.index(st.session_state.selected_symbol))
        with side_col:
            st.session_state.selected_side = st.radio("", ["LONG", "SHORT"], index=0 if st.session_state.selected_side == "LONG" else 1, horizontal=True)
        with ord_col:
            order_type = st.radio("", ["MARKET", "LIMIT"], index=0, horizontal=True)

        # Row 2: Balance metric and available capital
        cap_col, used_col = st.columns(2)
        with cap_col:
            st.metric("Balance", f"{balance:,.2f}")
        with used_col:
            used = DEFAULT_BALANCE - calculate_unutilized_capital(DEFAULT_BALANCE)
            st.metric("Margin Used", f"{used:,.2f}")

        # Row 3: Entry and SL method (POINTS / %)
        e_col, sm_col = st.columns([2, 1])
        with e_col:
            entry = st.number_input("", value=27050.0, min_value=0.0, format="%.6f", key="entry_input", label_visibility="collapsed")
        with sm_col:
            st.session_state.sl_method = st.radio("", ["POINTS", "PERCENT"], index=0, horizontal=True, label_visibility="collapsed")

        # Row 4: SL inputs (compact)
        if st.session_state.sl_method == "POINTS":
            s1_col, s2_col = st.columns([1, 1])
            with s1_col:
                sl_points = st.number_input("", value=100.0, min_value=0.0, key="sl_points", label_visibility="collapsed")
            # compute default SL price
            default_sl = entry - sl_points if st.session_state.selected_side == "LONG" else entry + sl_points
            with s2_col:
                sl_price = st.number_input("", value=round(default_sl, 6), min_value=0.0, format="%.6f", key="sl_price", label_visibility="collapsed")
        else:
            s1_col, s2_col = st.columns([1, 1])
            with s1_col:
                sl_percent = st.number_input("", value=1.0, min_value=0.01, format="%.2f", key="sl_pct", label_visibility="collapsed")
            sl_move = entry * (sl_percent / 100.0)
            default_sl = entry - sl_move if st.session_state.selected_side == "LONG" else entry + sl_move
            with s2_col:
                sl_price = st.number_input("", value=round(default_sl, 6), min_value=0.0, format="%.6f", key="sl_price_pct", label_visibility="collapsed")

        # Row 5: Position sizing method toggle (Position / Lot)
        s_method_col, manual_col = st.columns([2, 1])
        with s_method_col:
            sizing_choice = st.radio("", ["POSITION SIZE", "LOT SIZE"], index=0, horizontal=True, label_visibility="collapsed")
        # Show manual inputs (if user wants to override, they enter >0; otherwise recommended used)
        with manual_col:
            user_units = st.number_input("", min_value=0.0, value=0.0, format="%.6f", key="user_units", label_visibility="collapsed")
            user_lev = st.number_input("", min_value=1.0, value=1.0, step=1.0, key="user_leverage", label_visibility="collapsed")

        # Row 6: TP1 and TP2 (compact)
        tp1_col, tp2_col = st.columns(2)
        with tp1_col:
            tp1 = st.number_input("", value=0.0, format="%.6f", key="tp1", label_visibility="collapsed")
        with tp2_col:
            tp2 = st.number_input("", value=0.0, format="%.6f", key="tp2", label_visibility="collapsed")

        # compute recommended sizing
        rec_units, rec_lev, risk_value, msg = calculate_position_sizing(balance, entry, sl_price)

        # status row (very compact, no extra text)
        st.markdown(f'<div class="status">Units: <strong>{rec_units}</strong>  |  Lev: <strong>{rec_lev}x</strong>  |  Risk: <strong>${risk_value}</strong></div>', unsafe_allow_html=True)

        # daily counters
        today = datetime.utcnow().date().isoformat()
        stats = st.session_state.stats.get(today, {"total": 0, "by_symbol": {}})
        total_today = stats["total"]
        symbol_today = stats["by_symbol"].get(st.session_state.selected_symbol, 0)
        st.caption(f"Daily: {total_today}/{DAILY_MAX_TRADES}  •  {st.session_state.selected_symbol}: {symbol_today}/{DAILY_MAX_PER_SYMBOL}")

        # Buttons: Reset disabled, Place / Execute
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            st.button("RESET DAILY LIMITS", disabled=True)
        with btn_col2:
            if st.button("Place Order"):
                # validations exactly as requested
                if sl_price <= 0:
                    st.error("STOP LOSS REQUIRED.")
                    st.stop()

                if total_today >= DAILY_MAX_TRADES:
                    st.error("DAILY LIMIT REACHED.")
                    st.stop()

                if symbol_today >= DAILY_MAX_PER_SYMBOL:
                    st.error("SYMBOL LIMIT REACHED.")
                    st.stop()

                # Use recommended if user left manual at 0
                final_units = user_units if user_units > 0 else rec_units
                final_lev = int(user_lev) if user_lev > 0 else int(rec_lev)

                # Restrict user overrides: cannot exceed recommended
                if user_units > 0 and user_units > rec_units:
                    st.error(f"Quantity too high! Max allowed: {rec_units}")
                    st.stop()

                if user_lev > 0 and user_lev > rec_lev:
                    st.error(f"Leverage too high! Max allowed: {rec_lev}x")
                    st.stop()

                # Execute (simulation)
                result = execute_trade_action(balance, st.session_state.selected_symbol, st.session_state.selected_side, entry, sl_price, final_units, final_lev, order_type, tp1, tp2)
                st.success(result)
                st.experimental_rerun()

    # --------------------------
    # RIGHT: chart & trade log
    # --------------------------
    with col_right:
        st.header("Chart / Log")
        st.markdown("Chart placeholder — integrate your chart component here.")
        st.markdown("---")
        st.subheader("Today's Trades")
        today_trades = [t for t in st.session_state.trades if t["date"] == datetime.utcnow().date().isoformat()]
        if today_trades:
            df = pd.DataFrame(today_trades)
            df = df[["time", "symbol", "side", "entry", "stop_loss", "tp1", "tp2", "units", "leverage"]]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No trades today.")

if __name__ == "__main__":
    app()
