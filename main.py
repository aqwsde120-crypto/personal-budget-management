import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import google.generativeai as genai  # Google Gemini 라이브러리 추가
from ta.momentum import RSIIndicator
from ta.trend import MACD

# 페이지 설정
st.set_page_config(
    page_title="AI 주식 통합 진단 대시보드",
    page_icon="📈",
    layout="wide"
)

# [상단 생략: get_full_ticker, get_stock_data, get_financial_metrics 등은 기존과 동일]

def calculate_technical_indicators(df, market='US'):
    df = df.copy()
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    
    rsi = RSIIndicator(close=df['Close'], window=14)
    df['RSI'] = rsi.rsi()
    
    macd = MACD(close=df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    
    if market == 'KR':
        df['Trading_Value'] = (df['Close'] * df['Volume']) / 100000000
    else:
        df['Trading_Value'] = df['Close'] * df['Volume']
    return df

# [중단 생략: detect_pullback, get_macro_indicators, create_candlestick_chart 등 기존과 동일]

def generate_ai_analysis(ticker, financial_metrics, pullback_info, df, macro_indicators, api_key, market='US'):
    """Gemini API를 사용한 무료 AI 분석"""
    latest = df.iloc[-1]
    tv_unit = "억 원" if market == 'KR' else "USD"
    
    # Gemini 설정
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash') # 무료 티어에서 가장 빠른 모델

    prompt = f"""당신은 전문 금융 애널리스트입니다. 다음 정보를 바탕으로 '{ticker}' 종목에 대한 종합 투자 의견을 제시해주세요.

[데이터 요약]
- 재무: {financial_metrics}
- 눌림목: {pullback_info['reason']}
- 현재가: {latest['Close']:.2f}, RSI: {latest['RSI']:.2f}, 거래대금: {latest['Trading_Value']:,.2f} {tv_unit}
- 거시경제: 금리 {macro_indicators['미국10년물금리']['현재']}, 환율 {macro_indicators['원달러환율']['현재']}

[요청사항]
1. 투자 의견 (매수/매도/보유)
2. 기술적/재무적 근거 요약
3. 목표가 및 손절가 제시
한국어로 전문적이고 친절하게 답변해주세요.
"""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini 분석 실패: {e}\nAPI 키가 유효한지 확인해주세요."

def main():
    st.sidebar.header("🔧 설정 (Gemini 무료 버전)")
    market = st.sidebar.selectbox("시장 선택", ["KR", "US"])
    ticker = st.sidebar.text_input("종목 코드 입력", value="005930" if market=="KR" else "AAPL")
    api_key = st.sidebar.text_input("Google Gemini API Key", type="password", help="Google AI Studio에서 무료로 발급 가능")
    
    if st.sidebar.button("📊 분석 실행"):
        df = get_stock_data(ticker, market)
        if df is not None and not df.empty:
            df = calculate_technical_indicators(df, market=market)
            metrics = get_financial_metrics(ticker, market)
            pullback = detect_pullback(df)
            macro = get_macro_indicators()
            
            # 지표 표시 로직 (기존과 동일)
            st.subheader(f"📊 {ticker} 주요 지표")
            # ... [기존 코드의 지표 출력 부분] ...
            
            # 차트 표시
            st.plotly_chart(create_candlestick_chart(df), use_container_width=True)

            # AI 분석 섹션
            if api_key:
                st.subheader("🤖 Gemini AI 종합 의견 (무료)")
                with st.spinner('무료 AI가 데이터를 분석 중입니다...'):
                    result = generate_ai_analysis(ticker, metrics, pullback, df, macro, api_key, market)
                    st.write(result)
            else:
                st.warning("⚠️ Google Gemini API 키를 입력하면 무료로 AI 분석을 볼 수 있습니다.")

# [이하 생략: 기존 main() 구조 유지]
