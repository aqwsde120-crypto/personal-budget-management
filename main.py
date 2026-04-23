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

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="AI 주식 통합 진단", layout="wide")
st.title("📈 AI 주식 통합 진단")

# -----------------------------
# 데이터 불러오기 (6개월)
# -----------------------------
def get_stock_data(ticker, market):
    try:
        if market == "KR":
            end = datetime.now()
            start = end - timedelta(days=180)
            df = fdr.DataReader(ticker, start, end)
        else:
            df = yf.Ticker(ticker).history(period="6mo")
        return df
    except:
        return None

# -----------------------------
# 환율 변환
# -----------------------------
def convert_to_krw(df, market):
    try:
        if market == "US":
            rate = yf.Ticker("KRW=X").history(period="1mo")['Close'].iloc[-1]
            for col in ['Open','High','Low','Close']:
                df[col] *= rate
        return df
    except:
        return df

# -----------------------------
# 기술적 지표
# -----------------------------
def calc_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()

    df['RSI'] = RSIIndicator(df['Close']).rsi()

    macd = MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()

    return df

# -----------------------------
# 눌림목
# -----------------------------
def detect_pullback(df):
    latest = df.iloc[-1]

    cond1 = latest['Close'] > latest['MA20']
    cond2 = abs((latest['Close'] - latest['MA20']) / latest['MA20']) < 0.03

    vol_recent = df['Volume'].iloc[-5:].mean()
    vol_prev = df['Volume'].iloc[-20:-5].mean()
    cond3 = vol_recent < vol_prev

    return cond1 and cond2 and cond3

# -----------------------------
# 시장 흐름
# -----------------------------
def get_market_trend(market):
    try:
        index = "^GSPC" if market == "US" else "KS11"
        df = yf.Ticker(index).history(period="3mo")

        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        latest = df['Close'].iloc[-1]

        return "상승" if latest > ma20 else "하락"
    except:
        return "N/A"

# -----------------------------
# 모멘텀
# -----------------------------
def get_momentum(df):
    latest = df.iloc[-1]

    ret20 = (latest['Close'] / df['Close'].iloc[-20] - 1) * 100

    vol_recent = df['Volume'].iloc[-5:].mean()
    vol_prev = df['Volume'].iloc[-20:-5].mean()
    vol_up = vol_recent > vol_prev

    return ret20, vol_up, latest['RSI']

# -----------------------------
# 분석 엔진
# -----------------------------
def generate_report(df, pullback, market):

    latest = df.iloc[-1]

    close = latest['Close']
    ma20 = latest['MA20']
    ma60 = latest['MA60']
    rsi = latest['RSI']
    macd = latest['MACD']
    macd_signal = latest['MACD_Signal']

    score = 0
    reasons = []

    # 추세
    if close > ma20 > ma60:
        trend = "상승"
        score += 2
        reasons.append("이동평균선 정배열")
    elif close < ma20:
        trend = "하락"
        score -= 2
        reasons.append("MA20 아래")
    else:
        trend = "횡보"

    # RSI
    if rsi < 30:
        score += 2
        reasons.append("과매도")
    elif rsi > 70:
        score -= 2
        reasons.append("과매수")

    # MACD
    if macd > macd_signal:
        score += 1
        reasons.append("MACD 상승")
    else:
        score -= 1
        reasons.append("MACD 하락")

    # 눌림목
    if pullback:
        score += 2
        reasons.append("눌림목")

    # 의견
    if score >= 4:
        opinion = "🟢 매수"
    elif score >= 1:
        opinion = "🟡 관망"
    else:
        opinion = "🔴 매도"

    # 가격 전략
    buy_price = ma20 if pullback else close * 0.97
    stop_loss = min(ma60, buy_price * 0.95)

    # 시장 + 모멘텀
    market_trend = get_market_trend(market)
    ret20, vol_up, _ = get_momentum(df)

    report = f"""
### 📊 종합 분석

**🌍 시장 흐름**
- 시장 추세: {market_trend}

**🚀 모멘텀**
- 20일 수익률: {ret20:.2f}%
- 거래량: {"증가" if vol_up else "감소"}

**📌 가격 전략**
- 현재가: {close:,.0f} 원
- 매수 추천가: {buy_price:,.0f} 원
- 손절가: {stop_loss:,.0f} 원

**📉 기술적 분석**
- 추세: {trend}
- RSI: {rsi:.1f}
- MACD: {"상승" if macd > macd_signal else "하락"}

**📍 판단 근거**
- {" / ".join(reasons)}

👉 최종 의견: **{opinion}**
"""

    return score, opinion, report, close, buy_price, stop_loss

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

    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name="MA20"), row=1, col=1)

    fig.add_trace(go.Bar(x=df.index, y=df['Volume']), row=2, col=1)

    fig.update_layout(
        yaxis=dict(title="가격 (KRW)", tickformat=","),
        height=600
    )

    return fig

# -----------------------------
# MAIN
# -----------------------------
def main():

    market = st.sidebar.selectbox("시장", ["US", "KR"])
    ticker = st.sidebar.text_input("종목", "AAPL" if market=="US" else "005930")

    if st.sidebar.button("분석 실행"):

        df = get_stock_data(ticker, market)

        if df is None or df.empty:
            st.error("데이터 없음")
            return

        df = convert_to_krw(df, market)
        df = calc_indicators(df)

        pullback = detect_pullback(df)

        score, opinion, report, price, buy, stop = generate_report(df, pullback, market)

        # 상단 KPI
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("투자 의견", opinion)
        col2.metric("현재가", f"{price:,.0f} 원")
        col3.metric("매수 추천가", f"{buy:,.0f} 원")
        col4.metric("손절가", f"{stop:,.0f} 원")

        if pullback:
            st.success("눌림목 발생")
        else:
            st.info("눌림목 없음")

        st.markdown(report)

        st.plotly_chart(create_chart(df), use_container_width=True)

# 실행
if __name__ == "__main__":
    main()
