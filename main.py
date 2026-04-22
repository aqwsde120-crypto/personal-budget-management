import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import google.generativeai as genai
from ta.momentum import RSIIndicator
from ta.trend import MACD

# 페이지 설정
st.set_page_config(page_title="AI 주식 진단 (Gemini)", page_icon="📈", layout="wide")

def get_full_ticker(ticker, market):
    if market == 'KR' and ticker.isdigit():
        return f"{ticker}.KS"
    return ticker

def get_stock_data(ticker, market='US', period='1y'):
    full_ticker = get_full_ticker(ticker, market)
    try:
        df = yf.download(full_ticker, period=period, progress=False)
        if df.empty and market == 'KR':
            df = yf.download(f"{ticker}.KQ", period=period, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

def get_financial_metrics(ticker, market='US'):
    full_ticker = get_full_ticker(ticker, market)
    try:
        stock = yf.Ticker(full_ticker)
        info = stock.info
        return {
            'PER': info.get('trailingPE', 'N/A'),
            'PBR': info.get('priceToBook', 'N/A'),
            '시가총액': info.get('marketCap', 'N/A'),
            '52주최고': info.get('fiftyTwoWeekHigh', 'N/A')
        }
    except:
        return {k: 'N/A' for k in ['PER', 'PBR', '시가총액', '52주최고']}

def calculate_technical_indicators(df, market='US'):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    rsi = RSIIndicator(close=df['Close'], window=14)
    df['RSI'] = rsi.rsi()
    
    # 거래대금 계산 (한국은 억 단위)
    if market == 'KR':
        df['Trading_Value'] = (df['Close'] * df['Volume']) / 100000000
    else:
        df['Trading_Value'] = df['Close'] * df['Volume']
    return df

def generate_ai_analysis(ticker, metrics, df, api_key, market='US'):
    latest = df.iloc[-1]
    tv_unit = "억 원" if market == 'KR' else "USD"
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""당신은 주식 전문가입니다. {ticker} 종목을 분석하세요.
    - 현재가: {latest['Close']:.2f}
    - RSI: {latest['RSI']:.2f}
    - 거래대금: {latest['Trading_Value']:,.1f} {tv_unit}
    - 재무상태: {metrics}
    
    투자 의견과 목표가, 주의점을 한국어로 요약해줘."""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"분석 실패: {e}"

def main():
    st.sidebar.header("🔧 설정")
    market = st.sidebar.selectbox("시장", ["KR", "US"])
    ticker = st.sidebar.text_input("종목코드", "005930" if market=="KR" else "AAPL")
    api_key = st.sidebar.text_input("Gemini API Key", type="password")

    if st.sidebar.button("분석 실행"):
        df = get_stock_data(ticker, market)
        if df is not None and not df.empty:
            df = calculate_technical_indicators(df, market)
            metrics = get_financial_metrics(ticker, market)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.write("### 📊 현재 지표")
                st.metric("현재가", f"{df.iloc[-1]['Close']:,.0f}")
                tv_unit = "억" if market == 'KR' else "$"
                st.metric("거래대금", f"{df.iloc[-1]['Trading_Value']:,.1f} {tv_unit}")
            
            if api_key:
                st.divider()
                st.write("### 🤖 AI 분석 결과")
                with st.spinner('Gemini가 분석 중...'):
                    st.write(generate_ai_analysis(ticker, metrics, df, api_key, market))
        else:
            st.error("데이터를 불러올 수 없습니다.")

if __name__ == "__main__":
    main()
