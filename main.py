import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import plotly.graph_objects as go
from ta.momentum import RSIIndicator

# 페이지 설정
st.set_page_config(page_title="AI 주식 진단 (종목명 검색)", page_icon="📈", layout="wide")

@st.cache_data
def get_krx_list():
    """한국 거래소 종목 리스트를 가져와서 이름:코드 딕셔너리 생성"""
    # 라이브러리 의존성을 줄이기 위해 URL에서 직접 가져오거나 
    # 간단한 매핑 함수를 만들 수 있습니다. 
    # 여기서는 범용성을 위해 사용자가 이름을 입력하면 코드를 찾는 로직을 구성합니다.
    try:
        url = 'http://kind.krx.co.kr/corpoide/corpList.do?method=download&searchType=13'
        df_krx = pd.read_html(url, header=0)[0]
        df_krx = df_krx[['회사명', '종목코드']]
        df_krx['종목코드'] = df_krx['종목코드'].apply(lambda x: f"{x:06d}")
        return dict(zip(df_krx['회사명'], df_krx['종목코드']))
    except:
        return {}

def get_full_ticker(user_input, market, krx_dict):
    """종목명 또는 코드를 판단하여 yfinance용 티커로 변환"""
    user_input = user_input.strip()
    
    if market == 'KR':
        # 1. 입력값이 종목명인 경우 (딕셔너리에서 검색)
        if user_input in krx_dict:
            code = krx_dict[user_input]
            return f"{code}.KS"
        # 2. 입력값이 이미 코드인 경우
        elif user_input.isdigit():
            return f"{user_input}.KS"
        
    return user_input # 미국 주식은 보통 티커(AAPL 등)를 그대로 사용

# [기존 데이터 호출 및 지표 계산 로직은 동일하게 유지]
def get_stock_data(ticker_symbol, market, period='1y'):
    try:
        df = yf.download(ticker_symbol, period=period, progress=False)
        if df.empty and '.KS' in ticker_symbol:
            df = yf.download(ticker_symbol.replace('.KS', '.KQ'), period=period, progress=False)
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

def main():
    st.sidebar.header("🔧 설정")
    market = st.sidebar.selectbox("시장 선택", ["KR", "US"])
    
    krx_dict = {}
    if market == 'KR':
        with st.spinner('종목 리스트 불러오는 중...'):
            krx_dict = get_krx_list()
        user_input = st.sidebar.text_input("종목명 또는 코드 입력", value="삼성전자")
    else:
        user_input = st.sidebar.text_input("티커 입력 (예: AAPL)", value="AAPL")
        
    api_key = st.sidebar.text_input("Gemini API Key", type="password")
    
    if st.sidebar.button("📊 분석 실행"):
        ticker_symbol = get_full_ticker(user_input, market, krx_dict)
        
        df = get_stock_data(ticker_symbol, market)
        
        if df is not None and not df.empty:
            # 기술적 지표 계산
            df['MA20'] = df['Close'].rolling(window=20).mean()
            rsi = RSIIndicator(close=df['Close'], window=14)
            df['RSI'] = rsi.rsi()
            
            # 거래대금 (억 단위)
            if market == 'KR':
                df['Trading_Value'] = (df['Close'] * df['Volume']) / 100000000
            else:
                df['Trading_Value'] = df['Close'] * df['Volume']

            # 화면 출력
            st.subheader(f"📈 {user_input} ({ticker_symbol}) 분석 결과")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.update_layout(xaxis_rangeslider_visible=False, height=500)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                latest = df.iloc[-1]
                st.metric("현재가", f"{latest['Close']:,.0f}")
                tv_unit = "억 원" if market == 'KR' else "$"
                st.metric("당일 거래대금", f"{latest['Trading_Value']:,.1f} {tv_unit}")
                st.metric("RSI (14)", f"{latest['RSI']:.2f}")

            # AI 분석 (Gemini)
            if api_key:
                st.divider()
                st.write("### 🤖 AI 종합 의견")
                # [이전 답변의 generate_ai_analysis 함수 호출]
                # ... 생략 (코드 구조는 이전과 동일) ...
        else:
            st.error(f"'{user_input}' 데이터를 찾을 수 없습니다. 정확한 종목명이나 코드를 입력해주세요.")

if __name__ == "__main__":
    main()
