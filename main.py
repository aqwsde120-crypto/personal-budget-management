import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import requests
from bs4 import BeautifulSoup
import time

st.set_page_config(layout="wide")

# -----------------------------
# 네이버 (한국 주식)
# -----------------------------
def get_kr_data(code):
    try:
        url = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count=180&requestType=0"
        headers = {"User-Agent":"Mozilla/5.0"}

        res = requests.get(url, headers=headers, timeout=5)

        rows = []
        for line in res.text.split("\n"):
            p = line.split("|")
            if len(p) > 5:
                rows.append([p[0], p[4]])

        df = pd.DataFrame(rows, columns=["date","close"])
        df["date"] = pd.to_datetime(df["date"])
        df["close"] = pd.to_numeric(df["close"])

        return df

    except:
        return pd.DataFrame()

# -----------------------------
# 미국 주식
# -----------------------------
def get_us_data(ticker):
    for _ in range(3):
        try:
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            if not df.empty:
                df.columns = df.columns.get_level_values(0)
                return df
        except:
            pass
        time.sleep(1)
    return pd.DataFrame()

# -----------------------------
# UI
# -----------------------------
st.title("📈 투자 분석")

market = st.sidebar.selectbox("시장", ["KR","US"])

if market == "KR":
    code = st.sidebar.text_input("종목코드", "005930")
else:
    code = st.sidebar.text_input("티커", "AAPL")

# -----------------------------
# 실행
# -----------------------------
if st.sidebar.button("분석 실행"):

    if market == "KR":
        df = get_kr_data(code)
        close_col = "close"
    else:
        df = get_us_data(code)
        close_col = "Close"

    if df.empty:
        st.error("데이터 불러오기 실패")
        st.stop()

    if market == "KR":
        df = df.set_index("date")

    df["rsi"] = RSIIndicator(df[close_col]).rsi()

    price = float(df[close_col].iloc[-1])
    rsi = float(df["rsi"].iloc[-1])

    st.write(f"현재가: {price:,.0f}" if market=="KR" else f"${price:.2f}")
    st.write(f"RSI: {rsi:.1f}")

    monthly = df[close_col].resample("ME").last()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly.index, y=monthly.values))
    st.plotly_chart(fig)
