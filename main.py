import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, time as dt_time
import time

st.set_page_config(page_title="North America Intraday Engine", layout="wide")

# =============================
# SETTINGS
# =============================

REFRESH_SECONDS = 60
TOP_N = 10
RISK_PER_TRADE = 0.005  # 0.5%

# =============================
# LIVE EST TIME
# =============================

est = pytz.timezone("US/Eastern")
now_est = datetime.now(est)

st.title("📊 Institutional Intraday Scanner")
st.markdown(f"### 🕒 Live EST Time: {now_est.strftime('%Y-%m-%d %H:%M:%S')}")

# =============================
# MARKET HOURS CHECK
# =============================

def market_status():
    now = datetime.now(est).time()

    us_open = dt_time(9, 30)
    us_close = dt_time(16, 0)

    tsx_open = dt_time(9, 30)
    tsx_close = dt_time(16, 0)

    us_market = us_open <= now <= us_close
    tsx_market = tsx_open <= now <= tsx_close

    return us_market, tsx_market

us_open, tsx_open = market_status()

st.write(f"🇺🇸 US Market Open: {us_open}")
st.write(f"🇨🇦 TSX Market Open: {tsx_open}")

# =============================
# LOAD TICKERS
# =============================

@st.cache_data(ttl=3600)
def load_tickers():
    try:
        tsx = pd.read_csv("data/tsx_tickers.csv")["Symbol"].dropna().tolist()
    except:
        tsx = ["SHOP.TO","RY.TO","TD.TO","SU.TO","ENB.TO"]

    try:
        nasdaq = pd.read_csv("data/nasdaq_tickers.csv")["Symbol"].dropna().tolist()
    except:
        nasdaq = ["AAPL","MSFT","NVDA","TSLA","AMD"]

    try:
        nyse = pd.read_csv("data/nyse_tickers.csv")["Symbol"].dropna().tolist()
    except:
        nyse = ["JPM","XOM","BA","KO","DIS"]

    return tsx[:50], nasdaq[:50], nyse[:50]

TSX, NASDAQ, NYSE = load_tickers()

# =============================
# INDEX TREND FILTER
# =============================

@st.cache_data(ttl=300)
def get_index_trend(symbol):
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)

    if df.empty:
        return False

    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:,0]

    if len(close) < 200:
        return False

    ema200 = close.ewm(span=200, adjust=False).mean()

    return close.iloc[-1] > ema200.iloc[-1]

spy_bull = get_index_trend("SPY")
tsx_bull = get_index_trend("^GSPTSE")

st.write(f"SPY Bullish: {spy_bull}")
st.write(f"TSX Index Bullish: {tsx_bull}")

# =============================
# SIGNAL ENGINE
# =============================

def intraday_signal(symbol, market_type):

    try:
        df = yf.download(symbol, period="5d", interval="5m", progress=False)

        if df.empty or len(df) < 50:
            return None

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        if isinstance(close, pd.DataFrame):
            close = close.iloc[:,0]

        # Indicators
        ema10 = close.ewm(span=10, adjust=False).mean()
        ema30 = close.ewm(span=30, adjust=False).mean()

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        atr = (high - low).rolling(14).mean()

        last = -1

        score = 0

        if ema10.iloc[last] > ema30.iloc[last]:
            score += 40

        if 50 < rsi.iloc[last] < 75:
            score += 30

        if close.iloc[last] > close.rolling(20).mean().iloc[last]:
            score += 30

        # Market Filter
        if market_type == "US" and not spy_bull:
            return None
        if market_type == "TSX" and not tsx_bull:
            return None

        entry = close.iloc[last]
        stop = entry - atr.iloc[last]
        target = entry + (atr.iloc[last] * 2)

        return {
            "Symbol": symbol,
            "Score": round(score,2),
            "Buy": round(entry,2),
            "Sell Target": round(target,2),
            "Stop Loss": round(stop,2)
        }

    except:
        return None

# =============================
# SCAN MARKETS
# =============================

results = []

for ticker in TSX:
    signal = intraday_signal(ticker, "TSX")
    if signal:
        results.append(signal)

for ticker in NASDAQ:
    signal = intraday_signal(ticker, "US")
    if signal:
        results.append(signal)

for ticker in NYSE:
    signal = intraday_signal(ticker, "US")
    if signal:
        results.append(signal)

# =============================
# DISPLAY RESULTS
# =============================

if results:

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values("Score", ascending=False)
    df_results = df_results.head(TOP_N)

    st.subheader("🔥 Top Intraday Opportunities (Best → Worst)")
    st.dataframe(df_results, use_container_width=True)

else:
    st.warning("No qualifying stocks right now based on filters.")

# =============================
# AUTO REFRESH
# =============================

time.sleep(REFRESH_SECONDS)
st.rerun()
