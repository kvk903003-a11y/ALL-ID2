import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import pytz
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ---------------- SETTINGS ----------------
TOP_N = 50
TAKE_PROFIT = 1.01
STOP_LOSS = 0.995
MAX_POSITIONS = 10

st.set_page_config(layout="wide")
st.title("📊 Advanced Personal Trading Dashboard")

# ---------------- TIME ----------------
def est_time():
    est = pytz.timezone("America/New_York")
    return datetime.now(est)

def market_session():
    now = est_time()
    minutes = now.hour * 60 + now.minute
    if 240 <= minutes < 570:
        return "Pre-Market"
    elif 570 <= minutes < 960:
        return "Regular"
    elif 960 <= minutes < 1200:
        return "After-Hours"
    else:
        return "Closed"

st.markdown(f"### 🕒 EST Time: {est_time().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown(f"📊 US Market Session: **{market_session()}**")
st.markdown(f"⚙ Max Open Positions: {MAX_POSITIONS}")

st_autorefresh(interval=60*1000, key="refresh")

# ---------------- MARKET FILTERS ----------------
@st.cache_data(ttl=300)
def get_index_trend(symbol):
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)
    df["EMA200"] = ta.trend.ema_indicator(df["Close"], 200)
    return df.iloc[-1]["Close"] > df.iloc[-1]["EMA200"]

spy_bull = get_index_trend("SPY")
tsx_bull = get_index_trend("^GSPTSE")

st.markdown(f"🇺🇸 SPY Trend: {'Bullish' if spy_bull else 'Bearish'}")
st.markdown(f"🇨🇦 TSX Trend: {'Bullish' if tsx_bull else 'Bearish'}")

# ---------------- LOAD TICKERS ----------------
TSX = pd.read_csv("data/tsx_tickers.csv")["Symbol"].tolist()[:50]
NASDAQ = pd.read_csv("data/nasdaq_tickers.csv")["Symbol"].tolist()[:50]
NYSE = pd.read_csv("data/nyse_tickers.csv")["Symbol"].tolist()[:50]

# ---------------- BATCH DOWNLOAD ----------------
@st.cache_data(ttl=55)
def download_batch(tickers):
    return yf.download(
        tickers=tickers,
        period="5d",
        interval="1m",
        group_by="ticker",
        threads=True,
        progress=False
    )

# ---------------- SIGNAL ENGINE ----------------
def analyze_exchange(tickers, regime_bull):
    data = download_batch(tickers)
    results = []

    for ticker in tickers:
        try:
            df = data[ticker].dropna()
            if len(df) < 50:
                continue

            df["EMA10"] = ta.trend.ema_indicator(df["Close"],10)
            df["EMA30"] = ta.trend.ema_indicator(df["Close"],30)
            df["RSI"] = ta.momentum.rsi(df["Close"],14)
            df["VOL_MA"] = df["Volume"].rolling(20).mean()

            last = df.iloc[-1]

            if not regime_bull:
                continue

            if (
                last["EMA10"] > last["EMA30"] and
                45 < last["RSI"] < 65 and
                last["Volume"] > last["VOL_MA"]
            ):
                score = (
                    (last["EMA10"] - last["EMA30"]) / last["EMA30"] * 100 +
                    (65 - abs(55 - last["RSI"]))
                )

                buy = last["Close"]
                sell = buy * TAKE_PROFIT
                stop = buy * STOP_LOSS

                results.append({
                    "Ticker": ticker,
                    "Buy Price": round(buy,2),
                    "Sell Price": round(sell,2),
                    "Stop Price": round(stop,2),
                    "Score": round(score,2)
                })
        except:
            continue

    df_result = pd.DataFrame(results)
    if not df_result.empty:
        df_result = df_result.sort_values("Score", ascending=False)
        df_result.insert(0, "Rank", range(1, len(df_result)+1))
    return df_result

# ---------------- DISPLAY ----------------
tabs = st.tabs(["TSX","NASDAQ","NYSE"])

with tabs[0]:
    st.subheader("🇨🇦 TSX Ranked Signals")
    st.dataframe(analyze_exchange(TSX, tsx_bull))

with tabs[1]:
    st.subheader("🇺🇸 NASDAQ Ranked Signals")
    st.dataframe(analyze_exchange(NASDAQ, spy_bull))

with tabs[2]:
    st.subheader("🇺🇸 NYSE Ranked Signals")
    st.dataframe(analyze_exchange(NYSE, spy_bull))
