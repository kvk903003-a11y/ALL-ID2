import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import os

# --- PAGE SETUP ---
st.set_page_config(page_title="1-Min Multi-Exchange Intraday Engine", layout="wide")
st.title("🌎 1-Min Multi-Exchange Intraday Engine (TSX/NASDAQ/NYSE)")

# --- SETTINGS ---
INITIAL_CAPITAL = 100000
TOP_N = 5
STOP_LOSS = 0.5
TAKE_PROFIT = 1.0
TRAILING_STOP = True

# --- SESSION STATE ---
if "equity_curve" not in st.session_state:
    st.session_state.equity_curve = [INITIAL_CAPITAL]
if "capital" not in st.session_state:
    st.session_state.capital = INITIAL_CAPITAL
if "positions" not in st.session_state:
    st.session_state.positions = {}

# --- AUTO REFRESH EVERY 1 MINUTE ---
st_autorefresh(interval=60*1000, key="datarefresh")

# --- SAFE CSV LOADING ---
def load_csv(path):
    if not os.path.exists(path):
        st.error(f"CSV file not found: {path}")
        return pd.DataFrame(columns=["Symbol","Name"])
    try:
        df = pd.read_csv(path)
        if df.empty:
            st.error(f"CSV file is empty: {path}")
        return df
    except Exception as e:
        st.error(f"Error reading CSV {path}: {e}")
        return pd.DataFrame(columns=["Symbol","Name"])

TSX = load_csv("data/tsx_tickers.csv")["Symbol"].tolist()
NASDAQ = load_csv("data/nasdaq_tickers.csv")["Symbol"].tolist()
NYSE = load_csv("data/nyse_tickers.csv")["Symbol"].tolist()
stocks = {"TSX": TSX, "NASDAQ": NASDAQ, "NYSE": NYSE}

# --- SIGNAL FUNCTION ---
def generate_signal(df):
    if len(df) < 30:
        return 0, None, 0, df
    df["EMA10"] = ta.trend.ema_indicator(df["Close"],10)
    df["EMA30"] = ta.trend.ema_indicator(df["Close"],30)
    df["RSI7"] = ta.momentum.rsi(df["Close"],7)
    last = df.iloc[-1]
    signal = 0
    score = 0
    if last["EMA10"]>last["EMA30"] and last["RSI7"]<70:
        signal = 1
        score = ((last["EMA10"]-last["EMA30"])/last["EMA30"])*100 + (70-last["RSI7"])
    elif last["EMA10"]<last["EMA30"] and last["RSI7"]>30:
        signal = -1
        score = ((last["EMA30"]-last["EMA10"])/last["EMA10"])*100 + (last["RSI7"]-30)
    return signal, last["Close"], score, df

# --- FETCH DATA ---
def fetch_data(ticker):
    try:
        df = yf.download(ticker, period="7d", interval="1m", progress=False)
        if df.empty:
            df = yf.download(ticker, period="60d", interval="1d", progress=False)
        if isinstance(df.columns,pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return pd.DataFrame()

# --- MAIN LOGIC ---
exchange_results = {}
for exchange, tickers in stocks.items():
    results = []
    for ticker in tickers:
        df = fetch_data(ticker)
        if df.empty:
            continue
        signal, price, score, df = generate_signal(df)
        if price is None:
            continue
        results.append({"Stock":ticker,"Signal":signal,"Price":price,"Score":score,"DF":df})
    exchange_results[exchange] = pd.DataFrame(results)

# --- DISPLAY TABS ---
tabs = st.tabs(["TSX","NASDAQ","NYSE"])
for i, exchange in enumerate(["TSX","NASDAQ","NYSE"]):
    with tabs[i]:
        df = exchange_results[exchange]
        if df.empty:
            st.warning(f"No intraday data for {exchange}.")
            continue

        # --- TOP BUY SIGNALS ---
        buy_signals = df[df["Signal"]==1].sort_values(by="Score",ascending=False).head(TOP_N)
        table_data = []
        for _, row in buy_signals.iterrows():
            buy_price = row["Price"]
            sell_price = buy_price*(1+TAKE_PROFIT/100)
            table_data.append({"Stock":row["Stock"],"Buy Price":round(buy_price,2),
                               "Sell Price":round(sell_price,2),"Score":round(row["Score"],2)})
        st.subheader(f"🏆 Top {TOP_N} Buy Signals - {exchange}")
        st.dataframe(pd.DataFrame(table_data))

        # --- CHARTS ---
        st.subheader(f"📊 Charts - {exchange}")
        for _, row in buy_signals.iterrows():
            ticker = row["Stock"]
            df_c = row["DF"]
            fig = go.Figure()
            if df_c.index.freqstr=="1T":
                fig.add_trace(go.Candlestick(x=df_c.index, open=df_c["Open"], high=df_c["High"],
                                             low=df_c["Low"], close=df_c["Close"], name="Price"))
            else:
                fig.add_trace(go.Scatter(x=df_c.index, y=df_c["Close"], mode="lines", name="Close"))
            fig.add_trace(go.Scatter(x=df_c.index, y=df_c["EMA10"], mode="lines", name="EMA10"))
            fig.add_trace(go.Scatter(x=df_c.index, y=df_c["EMA30"], mode="lines", name="EMA30"))
            fig.update_layout(xaxis_rangeslider_visible=False, height=500, title=ticker)
            st.plotly_chart(fig, use_container_width=True)

st.info("Dashboard auto-refreshes every 1 minute.")
