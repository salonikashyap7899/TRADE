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
# Styling to emulate Binance dark card
# -------------------------
CARD_CSS = """
<style>
:root{
  --bg:#0b0e11;
  --card:#111316;
  --muted:#9aa0a6;
  --accent:#ffd166;
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
}
.tab.active{
  background:#14171a; color:#fff; border:1px solid rgba(255,255,255,0.04);
}
.small-pill { padding:6px 8px; background:#121416; border-radius:8px; font-size:13px; color:var(--muted); border:1px solid rgba(255,255,255,0.03) }
.order-tabs { display:flex; gap:8px; margin-top:12px; margin-bottom:6px; }
.order-tab { padding:8px 12px; border-radius:8px; background:#0f1113; color:var(--muted); border:1px solid transparent; }
.order-tab.active { color:#fff; background:#14171a; border:1px solid rgba(255,255,255,0.03); font-weight:600 }
.muted { color: var(--muted); font-size:14px; margin-bottom:6px; }
.input-box {
  background: var(--input-bg); border-radius:8px; padding:12px; border:1px solid rgba(255,255,255,0.03);
  display:flex; align-items:center; justify-content:space-between; gap:8px;
}
.size-text { color:#fff; font-weight:600; }
.slider-wrap { margin-top:10px; margin-bottom:10px; }
.chk { display:flex; gap:8px; align-items:center; margin-top:8px; margin-bottom:8px; color:var(--muted); }
.row-buttons{ display:flex; gap:12px; margin-top:12px; }
.btn-long {
  background: linear-gradient(180deg,#23be7e,#19a868); color:#fff; border:none; padding:12px 26px; border-radius:10px; font-weight:700; flex:1;
}
.btn-short {
  background: linear-gradient(180deg,#ff7b7b,#ff4b4b); color:#fff; border:none; padding:12px 26px; border-radius:10px; font-weight:700; flex:1;
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

    # Order type tabs
    order_type = st.radio("", ["Limit", "Market", "Stop Limit"], index=1, horizontal=True, key="ordertypetab")
    # Show active style using javascript-less method - just visually consistent via CSS above
    st.markdown(f"<div style='height:6px;margin-bottom:6px;'></div>", unsafe_allow_html=True)

    # Available balance line
    avail = st.session_state.get("avail_balance", 11.67)
    st.markdown(f"<div class='muted'>Avbl <span style='color:#fff;font-weight:700;margin-left:6px'>{avail:.2f} USDT</span></div>", unsafe_allow_html=True)

    # Size input row
    with st.container():
        st.markdown("<div style='margin-top:6px'/>", unsafe_allow_html=True)
        size = st.text_input("", value="", placeholder="", key="size_input")
        # We use custom display to make it match style: show the input styled container
        st.markdown(f"""
        <div class='input-box' style='margin-top:6px;'>
           <div style='color:var(--muted);'>Size</div>
           <div style='display:flex;gap:8px;align-items:center;'>
             <div style='color:#fff;font-weight:700;'> { ' ' if size=='' else size }</div>
             <div class='small-pill'>USDT ▾</div>
           </div>
        </div>
        """, unsafe_allow_html=True)

    # slider representation (5 ticks)
    slider_val = st.slider("", 0, 100, 0, key="size_slider")
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

    # Option checkboxes
    slippage = st.checkbox("Slippage Tolerance", key="slippage")
    tpsl = st.checkbox("TP/SL", key="tpsl")

    # Space
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Buttons row (Open Long / Open Short)
    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("Open Long", key="open_long"):
            st.session_state['last_action'] = "open_long"
    with c2:
        if st.button("Open Short", key="open_short"):
            st.session_state['last_action'] = "open_short"

    # Modify button visuals using JS-less approach: re-render styled buttons via markdown:
    st.markdown("""
      <div class='row-buttons'>
        <div style='flex:1;'><button class='btn-long' onclick="document.querySelector('button[kind=\"primary\"]').click();">Open Long</button></div>
        <div style='flex:1;'><button class='btn-short' onclick="document.querySelector('button[kind=\"secondary\"]').click();">Open Short</button></div>
      </div>
    """, unsafe_allow_html=True)

    # Footer (liquidation price / cost / max)
    col_footer = f"""
      <div class='footer-grid'>
        <div class='footer-col'>
          <div style='color:var(--muted);'>Liq Price: <span style='color:#fff'>--</span></div>
          <div style='color:var(--muted); margin-top:6px;'>Cost: <span style='color:#fff;font-weight:700'>0.00 USDT</span></div>
          <div style='color:var(--muted); margin-top:6px;'>Max <span style='color:#fff;font-weight:700'>1,360.5 USDT</span></div>
        </div>
        <div class='footer-col' style='text-align:right;'>
          <div style='color:var(--muted);'>Liq Price: <span style='color:#fff'>--</span></div>
          <div style='color:var(--muted); margin-top:6px;'>Cost: <span style='color:#fff;font-weight:700'>0.00 USDT</span></div>
          <div style='color:var(--muted); margin-top:6px;'>Max <span style='color:#fff;font-weight:700'>1,723.2 USDT</span></div>
        </div>
      </div>
      <div class='small-muted'>% Fee level</div>
    """
    st.markdown(col_footer, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    # Right column left empty (this code intentionally produces only the left panel like the screenshot)
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
