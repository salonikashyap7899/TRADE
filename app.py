# app.py - Binance-style Order Panel (single page, dark compact)
import os
import streamlit as st
from datetime import datetime
import numpy as np

# Try optional binance lib for live price (fallback to simulated)
try:
    from binance.client import Client
    BINANCE_AVAILABLE = True
except Exception:
    BINANCE_AVAILABLE = False

st.set_page_config(page_title="Order Panel", layout="wide", initial_sidebar_state="collapsed")

# -------------------------
# Small helpers
# -------------------------
def simulated_price(base=27050.0):
    offset = (datetime.utcnow().second % 60) * 0.1
    return base + offset

def fetch_price_for_symbol(symbol, broker='Simulation', api_key=None, api_secret=None):
    symbol = (symbol or "BTCUSDT").upper()
    if broker == "Binance Testnet" and BINANCE_AVAILABLE and api_key and api_secret:
        try:
            client = Client(api_key, api_secret)
            # futures small compatibility handling may be required for some environments
            ticker = client.futures_symbol_ticker(symbol=symbol)
            return float(ticker.get("price", simulated_price()))
        except Exception:
            return simulated_price()
    return simulated_price()

# -------------------------
# Styling to emulate Binance dark card and apply overrides
# -------------------------
CARD_CSS = """
<style>
:root{
  --bg:#0b0e11;
  --card:#111316;
  --muted:#9aa0a6;
  --accent:#ffd166; /* Orange underline */
  --border:#202428;
  --green:#28c08a;
  --red:#ff6b6b;
  --input-bg:#0f1113;
  --panel-radius:10px;
}
body { background: var(--bg); }
.stApp > div:first-child { background: var(--bg); }

.order-card{
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(0,0,0,0));
  border-radius: var(--panel-radius);
  padding: 16px;
  color: #e6e6e6;
  border: 1px solid var(--border);
  max-width: 420px;
  font-family: Inter, Arial, sans-serif;
}
.top-row {
  display:flex; gap:8px; align-items:center; justify-content:space-between;
  margin-bottom:8px;
}
.toggle-tabs {
  display:flex; gap:8px;
}
.tab {
  padding:8px 14px; border-radius:8px; background:transparent; color:var(--muted);
  border:1px solid transparent; font-weight:600;
  cursor:pointer;
}
.tab.active{
  background:#14171a; color:#fff; border:1px solid rgba(255,255,255,0.04);
}
.small-pill { padding:6px 8px; background:#121416; border-radius:8px; font-size:13px; color:var(--muted); border:1px solid rgba(255,255,255,0.03) }

/* Order Type Tabs (Limit, Market, Stop Limit) */
.order-type-tabs {
    display: flex;
    gap: 16px; /* Increased gap for spacing */
    margin-top: 12px;
    margin-bottom: 12px;
    padding-bottom: 4px; /* Space for the underline */
}
.order-type-tab {
    color: var(--muted);
    font-weight: 500;
    padding-bottom: 4px;
    cursor:pointer;
}
.order-type-tab.active {
    color: #fff;
    font-weight: 600;
    border-bottom: 2px solid var(--accent); /* Orange underline */
}
/* Hide default Streamlit radio label/container */
div[data-testid="stRadio"] { display: none; } 

.muted { color: var(--muted); font-size:14px; margin-bottom:6px; }
.input-box {
  background: var(--input-bg); border-radius:8px; padding:12px; border:1px solid rgba(255,255,255,0.03);
  display:flex; align-items:center; justify-content:space-between; gap:8px;
}
.size-text { color:#fff; font-weight:600; }
.slider-wrap { margin-top:10px; margin-bottom:10px; }
.chk { display:flex; gap:8px; align-items:center; margin-top:8px; margin-bottom:8px; color:var(--muted); }
.row-buttons{ display:flex; gap:12px; margin-top:12px; }

/* Apply custom styles to Streamlit buttons */
div[data-testid="stVerticalBlock"] > div:nth-child(4) button { /* Targeting the container where the buttons are placed */
    width: 100%;
    padding: 12px 26px;
    border-radius: 10px;
    font-weight: 700;
    color: #fff !important;
    border: none !important;
    box-shadow: none !important;
}

/* Open Long button style */
div[data-testid="stVerticalBlock"] > div:nth-child(4) div:nth-child(1) button {
    background: linear-gradient(180deg,#23be7e,#19a868) !important;
}
/* Open Short button style */
div[data-testid="stVerticalBlock"] > div:nth-child(4) div:nth-child(2) button {
    background: linear-gradient(180deg,#ff7b7b,#ff4b4b) !important;
}

/* Streamlit Checkbox Overrides */
/* Hide default Streamlit checkbox styling and replace with text */
div[data-testid="stCheckbox"] > label {
    padding-top: 4px;
    padding-bottom: 4px;
    margin: 0;
    display: flex;
    gap: 8px;
    color: var(--muted) !important;
    font-size: 14px;
}
div[data-testid="stCheckbox"] span:first-child { /* The checkmark box */
    border: 1px solid rgba(255,255,255,0.2) !important;
    background: transparent !important;
    border-radius: 3px;
}

/* Streamlit Slider Overrides */
div[data-testid="stSlider"] { padding: 0 !important; } /* Remove Streamlit padding */
div[data-testid="stSlider"] div:nth-child(2) { /* The track container */
    padding: 0 !important;
    margin-top: 10px;
    margin-bottom: 10px;
}
.stSlider > div > div:nth-child(2) { /* The track itself */
    background: var(--input-bg) !important;
}


.footer-grid { display:flex; justify-content:space-between; margin-top:12px; font-size:13px; color:var(--muted); }
.footer-col { width:48%; }
.small-muted { font-size:12px; color:var(--muted); margin-top:6px; }
</style>
"""

# -------------------------
# App UI (left panel only)
# -------------------------
st.markdown(CARD_CSS, unsafe_allow_html=True)

# Use session state to track which order type is active
if 'order_type_tab' not in st.session_state:
    st.session_state['order_type_tab'] = "Market"

col1, col2, col3 = st.columns([1, 0.08, 0.5])
with col1:
    st.markdown("<div class='order-card'>", unsafe_allow_html=True)
    
    # Top control row: Cross / Leverage / S
    top_controls = """
    <div class='top-row'>
      <div style='display:flex;gap:8px;align-items:center;'>
        <div class='small-pill'>Cross</div>
        <div class='small-pill'>150x</div>
        <div class='small-pill'>S</div>
      </div>
      <div style='display:flex;gap:8px;align-items:center;'>
        <div style='font-size:13px;color:var(--muted)'>⋮</div>
      </div>
    </div>
    """
    st.markdown(top_controls, unsafe_allow_html=True)

    # Open / Close big tabs
    st.markdown("""
      <div style='display:flex;gap:8px;margin-bottom:10px;'>
        <div class='tab active' style='flex:1;text-align:center;'>Open</div>
        <div class='tab' style='flex:1;text-align:center;'>Close</div>
      </div>
    """, unsafe_allow_html=True)

    # Order type tabs (Hidden radio and custom styled tabs)
    # The st.radio component is still used to manage state, but is hidden by CSS.
    order_type = st.radio("", ["Limit", "Market", "Stop Limit"], index=1, horizontal=True, key="ordertypetab")
    active_class = lambda tab: 'active' if st.session_state['order_type_tab'] == tab else ''
    
    # Use HTML/Markdown to render the styled tabs like the inspiration UI
    st.markdown(f"""
      <div class='order-type-tabs'>
        <div class='order-type-tab {active_class('Limit')}' onclick="document.querySelector('input[value=\"Limit\"]').click();">Limit</div>
        <div class='order-type-tab {active_class('Market')}' onclick="document.querySelector('input[value=\"Market\"]').click();">Market</div>
        <div class='order-type-tab {active_class('Stop Limit')}' onclick="document.querySelector('input[value=\"Stop Limit\"]').click();">Stop Limit</div>
      </div>
    """, unsafe_allow_html=True)
    
    # Update session state on tab change (required for the active_class to work)
    st.session_state['order_type_tab'] = order_type


    # Available balance line
    avail = st.session_state.get("avail_balance", 11.67)
    # Changed HTML slightly to match the look: Avbl (icon) 11.67 USDT
    st.markdown(f"""
        <div class='muted'>
            Avbl <span style='font-weight:400; color:var(--muted)'>11.67 USDT</span>
            <span style='color:var(--accent); margin-left:8px; font-weight:700;'>⇌</span>
        </div>
    """, unsafe_allow_html=True)

    # Size input row
    # Use a hidden Streamlit input and display the value in the styled box
    size_value = st.text_input("Size_Hidden", value="", placeholder="", key="size_input_hidden", label_visibility="collapsed")
    
    st.markdown(f"""
        <div class='input-box' style='margin-top:6px;'>
           <div style='color:var(--muted);'>Size</div>
           <div style='display:flex;gap:8px;align-items:center;'>
             <div style='color:#fff;font-weight:700;'> { size_value or '0.00' }</div>
             <div class='small-pill'>USDT ▾</div>
           </div>
        </div>
    """, unsafe_allow_html=True)

    # Slider representation (5 ticks)
    slider_val = st.slider("Slider_Hidden", 0, 100, 0, key="size_slider", label_visibility="collapsed")
    st.markdown(f"""
      <div class='slider-wrap'>
        <div style='display:flex;justify-content:space-between;align-items:center;color:var(--muted); margin-top:8px;'>
          <div style='width:18px;height:18px;border-radius:4px;border:2px solid rgba(255,255,255,0.08);'></div>
          <div style='width:18px;height:18px;border-radius:4px;border:2px solid rgba(255,255,255,0.08);'></div>
          <div style='width:18px;height:18px;border-radius:4px;border:2px solid rgba(255,255,255,0.08);'></div>
          <div style='width:18px;height:18px;border-radius:4px;border:2px solid rgba(255,255,255,0.08);'></div>
          <div style='width:18px;height:18px;border-radius:4px;border:2px solid rgba(255,255,255,0.08);'></div>
        </div>
      </div>
    """, unsafe_allow_html=True)

    # Option checkboxes (Labels match screenshot exactly)
    slippage = st.checkbox("Slippage Tolerance", key="slippage")
    tpsl = st.checkbox("TP/SL", key="tpsl")

    # Space
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Buttons row (Open Long / Open Short) - Only use Streamlit buttons, relying on CSS overrides
    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("Open Long", key="open_long"):
            st.session_state['last_action'] = "open_long"
    with c2:
        if st.button("Open Short", key="open_short"):
            st.session_state['last_action'] = "open_short"
            
    # Remove the duplicate Markdown buttons section to only show the styled Streamlit buttons

    # Footer (liquidation price / cost / max)
    col_footer = f"""
      <div class='footer-grid'>
        <div class='footer-col'>
          <div style='color:var(--muted);'>Liq Price: <span style='color:#fff'>-- USDT</span></div>
          <div style='color:var(--muted); margin-top:6px;'>Cost: <span style='color:#fff;font-weight:700'>0.00 USDT</span></div>
          <div style='color:var(--muted); margin-top:6px;'>Max <span style='color:#fff;font-weight:700'>1,360.5 USDT</span></div>
        </div>
        <div class='footer-col' style='text-align:right;'>
          <div style='color:var(--muted);'>Liq Price: <span style='color:#fff'>-- USDT</span></div>
          <div style='color:var(--muted); margin-top:6px;'>Cost: <span style='color:#fff;font-weight:700'>0.00 USDT</span></div>
          <div style='color:var(--muted); margin-top:6px;'>Max <span style='color:#fff;font-weight:700'>1,723.2 USDT</span></div>
        </div>
      </div>
      <div class='small-muted'>% Fee level</div>
    """
    st.markdown(col_footer, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    # Right column left empty
    st.write("")

# -------------------------
# Optional: show last action for demo
# -------------------------
if 'last_action' in st.session_state:
    st.success(f"Last action: {st.session_state['last_action']}. (Demo mode — no broker call made.)")

# -------------------------
# Security reminder
# -------------------------
st.markdown(
    """
    <div style='position:fixed;right:16px;bottom:12px;color:#999;font-size:12px'>
      Demo UI — do NOT paste real API keys here. Use testnet keys only for testing.
    </div>
    """, unsafe_allow_html=True)