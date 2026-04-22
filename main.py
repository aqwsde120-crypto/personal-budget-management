import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import plotly.graph_objects as go
from ta.momentum import RSIIndicator

# 페이지 설정
st.set_page_config(page_title="AI 주식 진단 대시보드", page_icon="📈", layout="wide")

@st.cache_data
def get_krx_list():
    """한국 거래소 종목 리스트를 가져오는 더 안정적인 방법"""
    try:
        # KIND 사이트가 막힐 경우를 대비해 더 직접적인 URL 사용
        url = 'http://kind.krx.co.kr/corpoide/corpList.do?method=download'
        df = pd.read_html(url, header=0)[0]
        df = df[['회사명', '종목코드']]
        df['종목코드'] = df['종목코드'].apply(lambda x: f"{x:06d}")
        # 공백 제거 및 이름:코드 매핑
        return {name.strip(): code for name, code in zip(df['회사명'], df['종목코드'])}
    except Exception as e:
        st.error(f"종목 리스트를 불러오는 중 오류 발생: {e}")
        return {}

def get_full_ticker(user_input, market, krx_dict):
    user_input = user_input.strip()
    
    if market == 'KR':
        # 1. 종목명으로 찾기
        if user_input in krx_dict:
            return f"{krx_dict[user_input]}.KS"
        # 2. 부분 일치 검색 (예: '삼성'만 쳐도 '삼성전자'를 찾음)
        for name, code in krx_dict.items():
            if user_input in name:
                st.info(f"'{name}'(으)로 검색합니다.")
                return f"{code}.KS"
        # 3. 코드 숫자를 바로 입력한 경우
        if user_input.isdigit():
            return f"{user_input}.KS"
            
    return user_input # 미국 주식(티커) 또는 변환 실패 시 그대로 반환

def get_stock_data(ticker_symbol, market, period='1y'):
    try:
        df = yf.download(ticker_symbol, period=period, progress=False)
        # 코스피(.KS)로 안나오면 코스닥(.KQ) 시도
        if (df is None or df.empty) and '.KS' in ticker_symbol:
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
        krx_dict = get_krx_list()
        user_input = st.sidebar.text_input("종목명 또는 코드 입력", value="삼성전자")
    else:
        user_input = st.sidebar.text_input("티커 입력 (예: AAPL)", value="AAPL")
        
    api_key = st.sidebar.text_input("Gemini API Key", type="password")
    
    if st.sidebar.button("📊 분석 실행"):
        ticker_symbol = get_full_ticker(user_input, market, krx_dict)
        
        with st.spinner(f'{ticker_symbol} 데이터 분석 중...'):
            df = get_stock_data(ticker_symbol, market)
            
            if df is not None and not df.empty:
                # 지표 계산
                df['MA20'] = df['Close'].rolling(window=20).mean()
                rsi = RSIIndicator(close=df['Close'], window=14)
                df['RSI'] = rsi.rsi()
                
                # 거래대금 (억 단위)
                if market == 'KR':
                    df['Trading_Value'] = (df['Close'] * df['Volume']) / 100000000
                else:
                    df['Trading_Value'] = df['Close'] * df['Volume']

                # 결과 출력
                st.subheader(f"📈 {user_input} 분석 결과")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                    fig.update_layout(xaxis_rangeslider_visible=False, height=500, template='plotly_white')
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    latest = df.iloc[-1]
                    st.metric("현재가", f"{latest['Close']:,.0f}")
                    tv_unit = "억 원" if market == 'KR' else "$"
                    st.metric("당일 거래대금", f"{latest['Trading_Value']:,.1f} {tv_unit}")
                    st.metric("RSI (14)", f"{latest['RSI']:.2f}")

                # Gemini AI 분석
                if api_key:
                    st.divider()
                    st.write("### 🤖 AI 종합 의견")
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = f"{user_input}의 현재가 {latest['Close']}, RSI {latest['RSI']:.2f}를 바탕으로 투자 의견을 요약해줘."
                        response = model.generate_content(prompt)
                        st.write(response.text)
                    except Exception as e:
                        st.error(f"AI 분석 중 오류 발생: {e}")
            else:
                st.error(f"'{user_input}' 데이터를 찾을 수 없습니다. 종목명이나 티커가 정확한지 확인해 주세요.")

if __name__ == "__main__":
    main()
