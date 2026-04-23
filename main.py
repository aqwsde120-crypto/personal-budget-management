import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from ta.momentum import RSIIndicator
from ta.trend import MACD

# 페이지 설정
st.set_page_config(page_title="AI 주식 통합 진단 대시보드", page_icon="📈", layout="wide")

st.markdown('<h1>📈 AI 주식 통합 진단</h1>', unsafe_allow_html=True)

# -----------------------------
# 데이터 불러오기
# -----------------------------
def get_stock_data(ticker, market='US'):
    try:
        if market == 'KR':
            end_date = datetime.now()
            start_date = end_date - timedelta(days=400)
            df = fdr.DataReader(ticker, start_date, end_date)
        else:
            df = yf.Ticker(ticker).history(period="1y")
        return df
    except:
        return None

# -----------------------------
# 기술적 지표 계산
# -----------------------------
def calculate_technical_indicators(df):
    df = df.copy()

    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()

    df['RSI'] = RSIIndicator(df['Close']).rsi()

    macd = MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()

    return df

# -----------------------------
# 눌림목 분석
# -----------------------------
def detect_pullback(df):
    latest = df.iloc[-1]

    cond1 = latest['Close'] > latest['MA20']
    cond2 = abs((latest['Close'] - latest['MA20']) / latest['MA20']) < 0.03

    vol_recent = df['Volume'].iloc[-5:].mean()
    vol_prev = df['Volume'].iloc[-20:-5].mean()
    cond3 = vol_recent < vol_prev

    is_pullback = cond1 and cond2 and cond3

    return is_pullback

# -----------------------------
# 🔥 핵심: AI 대체 분석 엔진
# -----------------------------
def generate_analysis(df, pullback):
    latest = df.iloc[-1]

    score = 0
    signals = []

    # 추세
    if latest['Close'] > latest['MA20'] > latest['MA60']:
        score += 2
        signals.append("상승 추세")
    else:
        score -= 2
        signals.append("하락 추세")

    # RSI
    if latest['RSI'] < 30:
        score += 2
        signals.append("과매도")
    elif latest['RSI'] > 70:
        score -= 2
        signals.append("과매수")

    # MACD
    if latest['MACD'] > latest['MACD_Signal']:
        score += 1
        signals.append("MACD 상승")
    else:
        score -= 1
        signals.append("MACD 하락")

    # 눌림목
    if pullback:
        score += 2
        signals.append("눌림목 구간")

    # 결과
    if score >= 4:
        opinion = "🟢 매수"
    elif score >= 1:
        opinion = "🟡 관망"
    else:
        opinion = "🔴 매도"

    return score, opinion, signals

# -----------------------------
# 차트
# -----------------------------
def create_chart(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='MA20'), row=1, col=1)

    fig.add_trace(go.Bar(x=df.index, y=df['Volume']), row=2, col=1)

    return fig

# -----------------------------
# 메인
# -----------------------------
def main():
    market = st.sidebar.selectbox("시장", ["US", "KR"])
    ticker = st.sidebar.text_input("종목", "AAPL" if market=="US" else "005930")

    if st.sidebar.button("분석 실행"):

        df = get_stock_data(ticker, market)

        if df is None or df.empty:
            st.error("데이터 없음")
            return

        df = calculate_technical_indicators(df)
        pullback = detect_pullback(df)

        score, opinion, signals = generate_analysis(df, pullback)

        st.subheader("📊 분석 결과")

        st.metric("투자 의견", opinion)
        st.metric("점수", score)

        st.write("### 📌 주요 신호")
        for s in signals:
            st.write(f"- {s}")

        if pullback:
            st.success("눌림목 발생")
        else:
            st.info("눌림목 없음")

        st.plotly_chart(create_chart(df), use_container_width=True)

if __name__ == "__main__":
    main()
