# ██████╗ ██████╗  ██████╗      ████████╗██████╗  █████╗ ██████╗ ███████╗██████╗ 
# ██╔══██╗██╔══██╗██╔═══██╗     ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
# ██████╔╝██████╔╝██║   ██║        ██║   ██████╔╝███████║██║  ██║█████╗  ██████╔╝
# ██╔═══╝ ██╔══██╗██║   ██║        ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  ██╔══██╗
# ██║     ██║  ██║╚██████╔╝        ██║   ██║  ██║██║  ██║██████╔╝███████╗██║  ██║
# ╚═╝     ╚═╝  ╚═╝ ╚═════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝

import streamlit as st
import pandas as pd
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime
import requests
import os

# ========================
# PAGE CONFIG & STATE
# ========================
st.set_page_config(page_title="PRO TRADER TERMINAL", layout="wide")

# Initialize session state
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "trades" not in st.session_state:
    st.session_state.trades = []
if "balance" not in st.session_state:
    st.session_state.balance = 10000.0

# ========================
# DARK / LIGHT MODE TOGGLE
# ========================
def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

theme = st.session_state.theme
bg = "#0e1117" if theme == "dark" else "#ffffff"
text_color = "#fafafa" if theme == "dark" else "#1a1a1a"
card_bg = "#1e2233" if theme == "dark" else "#f8f9fa"
border_color = "#00ff9d"
accent = "#00ff9d"

# Custom CSS - Binance Pro Style
st.markdown(f"""
<style>
    .main {{ background-color: {bg}; color: {text_color}; }}
    .stApp {{ background-color: {bg}; }}
    h1, h2, h3, h4 {{ color: {text_color}; margin: 0.5rem 0; }}
    .price-big {{ font-size: 48px; font-weight: bold; color: {accent}; line-height: 1; }}
    .card {{ background: {card_bg}; padding: 18px; border-radius: 12px; border: 1px solid #333; height: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
    .big-btn button {{ height: 70px !important; font-size: 26px !important; font-weight: bold !important; }}
    .mode-btn {{ position: fixed; top: 12px; right: 20px; z-index: 999; }}
    .stDataFrame {{ background: {card_bg}; }}
</style>
""", unsafe_allow_html=True)

# Theme Toggle Button
with st.container():
    st.markdown('<div class="mode-btn">', unsafe_allow_html=True)
    if st.button("Light Mode" if theme == "dark" else "Dark Mode", key="theme_toggle"):
        toggle_theme()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ========================
# LIVE PRICE FROM BINANCE
# ========================
@st.cache_data(ttl=3)  # Update every 3 seconds
def get_live_price():
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=BTCUSDT"
        data = requests.get(url, timeout=5).json()
        return float(data['price'])
    except:
        return 90724.80

price = get_live_price()
change = round(np.random.uniform(-300, 300), 2)
change_pct = round(change / price * 100, 2)

# ========================
# MAIN LAYOUT - 3 COLUMNS (Binance Style)
# ========================
col_left, col_center, col_right = st.columns([2.4, 3.8, 3], gap="medium")

# ========================
# LEFT: Price + Order Panel
# ========================
with col_left:
    # Price Card
    st.markdown(f"""
    <div class="card">
        <h2 style="margin:0; color:#aaa;">BTCUSDT Perpetual</h2>
        <div class="price-big">${price:,.2f}</div>
        <div style="font-size:20px; color:{'#ff4444' if change<0 else '#00ff9d'}">
            {change:+.2f} ({change_pct:+.2f}%)
        </div>
        <small style="color:#888;">
            Mark: ${price+0.1:,.2f} • Index: ${price-12:,.2f} • 24h Vol: 2.41B
        </small>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Order Entry Card
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Order Entry")

    side = st.radio("Direction", ["LONG", "SHORT"], horizontal=True, label_visibility="collapsed")

    c1, c2 = st.columns(2)
    with c1:
        order_type = st.selectbox("Type", ["Market", "Limit", "Stop"], label_visibility="collapsed")
    with c2:
        leverage = st.selectbox("Leverage", ["20x", "50x", "75x", "100x", "125x"], index=2)

    entry_price = st.number_input("Entry Price", value=price, step=0.1, format="%.2f")
    amount_usd = st.number_input("Amount (USDT)", min_value=10.0, value=1000.0, step=100.0)

    # Risk Management
    risk_pct = st.slider("Risk % of Balance", 0.1, 5.0, 1.0, 0.1)
    sl_pct = st.slider("Stop Loss %", 0.1, 5.0, 1.0, 0.1)

    sl_price = entry_price * (1 - sl_pct/100) if side == "LONG" else entry_price * (1 + sl_pct/100)
    risk_amount = st.session_state.balance * (risk_pct / 100)

    # Calculate units
    units = round(risk_amount / (sl_pct/100 * entry_price), 6) if sl_pct > 0 else 0

    st.markdown(f"""
    <small>
    Risk: <b>${risk_amount:,.0f}</b> • SL: {sl_price:,.2f} 
    → <b>{units:,.6f} BTC</b> @ {leverage}
    </small>
    """, unsafe_allow_html=True)

    # TP Levels
    st.markdown("**Take Profit Targets**")
    tp1 = st.number_input("TP1", value=entry_price * 1.015, format="%.2f")
    tp1_pct = st.slider("TP1 %", 10, 90, 70, 5)
    tp2 = st.number_input("TP2", value=entry_price * 1.03, format="%.2f")

    st.markdown("---")

    # EXECUTE BUTTONS
    buy_col, sell_col = st.columns(2)
    with buy_col:
        if st.button("BUY / LONG", type="primary", use_container_width=True, key="buy_btn"):
            st.success(f"LONG ×{leverage} | ${amount_usd:,.0f} @ {entry_price:,.2f}")
            st.session_state.trades.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "side": "LONG",
                "price": entry_price,
                "amount": amount_usd,
                "lev": leverage,
                "pnl": 0
            })
    with sell_col:
        if st.button("SELL / SHORT", type="secondary", use_container_width=True, key="sell_btn"):
            st.success(f"SHORT ×{leverage} | ${amount_usd:,.0f} @ {entry_price:,.2f}")
            st.session_state.trades.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "side": "SHORT",
                "price": entry_price,
                "amount": amount_usd,
                "lev": leverage,
                "pnl": 0
            })

    st.markdown("</div>", unsafe_allow_html=True)

# ========================
# CENTER: Professional Chart
# ========================
with col_center:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### BTCUSDT Chart")

    # Generate realistic OHLC data
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=150, freq='5min')
    close = np.cumsum(np.random.randn(150) * 25) + price
    open_p = close.shift(1).fillna(price)
    high = np.maximum(open_p, close) + np.random.uniform(5, 60, 150)
    low = np.minimum(open_p, close) - np.random.uniform(5, 60, 150)
    volume = np.random.randint(80, 600, 150)

    df = pd.DataFrame({
        'Open': open_p,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': volume
    }, index=dates)

    # Custom style like Binance
    mc = mpf.make_marketcolors(up='#00ff9d', down='#ff4444',
                               edge='inherit', wick={'up':'#00ff9d', 'down':'#ff4444'},
                               volume='#333333')
    s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, gridstyle='')

    fig, axlist = mpf.plot(
        df.tail(80),
        type='candle',
        style=s,
        volume=True,
        mav=(7, 21),
        figsize=(10, 7),
        returnfig=True,
        tight_layout=True,
        show_nontrading=False
    )
    axlist[0].set_facecolor(card_bg)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)
    st.markdown("</div>", unsafe_allow_html=True)

# ========================
# RIGHT: Positions & Trade Log
# ========================
with col_right:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Open Positions")
    st.info("No open positions")

    st.markdown("### Today's Trade Log")
    if st.session_state.trades:
        log_df = pd.DataFrame(st.session_state.trades[-10:])  # Last 10 trades
        log_df.index = range(1, len(log_df) + 1)
        st.dataframe(
            log_df[["time", "side", "price", "amount", "lev"]],
            use_container_width=True,
            column_config={
                "side": st.column_config.TextColumn("Side", width="small"),
                "price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "amount": st.column_config.NumberColumn("Size", format="$%.0f"),
                "lev": st.column_config.TextColumn("Lev")
            }
        hide_index=False
        )
    else:
        st.caption("No trades executed today")

    # Balance & Stats
    st.markdown("---")
    st.markdown(f"**Account Balance:** `${st.session_state.balance:,.2f}`")
    st.markdown(f"**Daily Trades:** `{len(st.session_state.trades)} / 4`")
    st.markdown(f"**Risk Used Today:** `{risk_pct:.1f}%`")

    st.markdown("</div>", unsafe_allow_html=True)

# ========================
# FOOTER
# ========================
st.markdown(f"""
<div style='text-align:center; padding:20px; color:#666; font-size:14px; margin-top:20px;'>
    <b>PRO TRADER TERMINAL</b> • {datetime.now().strftime("%d %b %Y • %H:%M:%S")} UTC • 
    <span style='color:{accent};'>● LIVE</span> • Made with ❤️ for Elite Traders
</div>
""", unsafe_allow_html=True)