import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai  # 이 부분이 반드시 있어야 합니다!

# 페이지 설정
st.set_page_config(page_title="AI 주식 진단 대시보드", page_icon="📈", layout="wide")

@st.cache_data
def get_krx_list():
    """한국 거래소 종목 리스트 로드"""
    try:
        url = 'http://kind.krx.co.kr/corpoide/corpList.do?method=download'
        df = pd.read_html(url, header=0)[0]
        return {name.strip(): f"{code:06d}" for name, code in zip(df['회사명'], df['종목코드'])}
    except:
        return {}

def get_full_ticker(user_input, market, krx_dict):
    user_input = user_input.strip()
    if market == 'KR':
        if user_input in krx_dict:
            return f"{krx_dict[user_input]}.KS"
        for name, code in krx_dict.items():
            if user_input in name: return f"{code}.KS"
        if user_input.isdigit(): return f"{user_input}.KS"
    return user_input

def main():
    st.sidebar.header("🔧 설정")
    market = st.sidebar.selectbox("시장 선택", ["KR", "US"])
    krx_dict = get_krx_list() if market == 'KR' else {}
    
    default_val = "삼성전자" if market == 'KR' else "AAPL"
    user_input = st.sidebar.text_input("종목명 또는 코드", value=default_val)
    
    # API 키 입력 및 Enter 유도
    api_key = st.sidebar.text_input("Google Gemini API Key", type="password", placeholder="AIza... 입력 후 Enter")
    st.sidebar.caption("[API 키 발급받기](https://aistudio.google.com/)")
    
    if st.sidebar.button("📊 분석 실행"):
        ticker_symbol = get_full_ticker(user_input, market, krx_dict)
        
        with st.spinner('데이터를 분석 중입니다...'):
            df = yf.download(ticker_symbol, period='1y', progress=False)
            
            # 코스피 실패 시 코스닥 재시도
            if df.empty and '.KS' in ticker_symbol:
                df = yf.download(ticker_symbol.replace('.KS', '.KQ'), period='1y', progress=False)

            if df is not None and not df.empty:
                # yfinance 멀티인덱스 대응
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                # 기술적 지표
                df['MA20'] = df['Close'].rolling(window=20).mean()
                df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
                latest = df.iloc[-1]
                
                # 결과 레이아웃
                st.subheader(f"📈 {user_input} ({ticker_symbol}) 분석 결과")
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                    fig.update_layout(xaxis_rangeslider_visible=False, height=450, template='plotly_white', margin=dict(t=10, b=10))
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.write("#### 📊 주요 데이터")
                    st.metric("현재가", f"{latest['Close']:,.0f}")
                    
                    val_unit = "억 원" if market == 'KR' else "USD"
                    trading_val = (latest['Close'] * latest['Volume']) / (100000000 if market == 'KR' else 1)
                    st.metric("당일 거래대금", f"{trading_val:,.1f} {val_unit}")
                    st.metric("RSI (14)", f"{latest['RSI']:.2f}")

                # AI 분석 섹션
                st.markdown("---")
                st.write("### 🤖 AI 종합 투자 의견")
                
                if api_key:
                    try:
                        # genai를 직접 사용하기 전 설정을 확인합니다.
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        prompt = f"""당신은 전문 주식 애널리스트입니다.
                        종목: {user_input} ({ticker_symbol})
                        현재가: {latest['Close']:.2f}
                        RSI: {latest['RSI']:.2f}
                        20일 이동평균선: {latest['MA20']:.2f}
                        
                        위 데이터를 바탕으로 투자 의견(매수/보유/매도)과 향후 전망을 한국어로 아주 상세하게 리포트 형식으로 작성해줘."""
                        
                        with st.spinner('Gemini AI 분석 리포트를 생성 중...'):
                            response = model.generate_content(prompt)
                            st.info(response.text)
                    except Exception as e:
                        st.error(f"AI 호출 에러: {e}")
                else:
                    st.warning("⚠️ 사이드바에 Gemini API Key를 입력해야 AI 리포트를 볼 수 있습니다.")
            else:
                st.error(f"'{user_input}'의 데이터를 불러오지 못했습니다. 종목명이나 코드가 정확한지 확인해 주세요.")

if __name__ == "__main__":
    main()
