import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai

# 페이지 설정
st.set_page_config(page_title="AI 주식 진단 대시보드", page_icon="📈", layout="wide")

@st.cache_data
def get_krx_list():
    try:
        url = 'http://kind.krx.co.kr/corpoide/corpList.do?method=download'
        df = pd.read_html(url, header=0)[0]
        return {name.strip(): f"{code:06d}" for name, code in zip(df['회사명'], df['종목코드'])}
    except:
        return {}

def get_full_ticker(user_input, market, krx_dict):
    user_input = user_input.strip()
    if market == 'KR':
        if user_input in krx_dict: return f"{krx_dict[user_input]}.KS"
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
    
    # API 키 확인
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.sidebar.success("✅ 시스템 API 키 로드 완료")
    else:
        api_key = st.sidebar.text_input("Google Gemini API Key", type="password")
    
    if st.sidebar.button("📊 분석 실행"):
        ticker_symbol = get_full_ticker(user_input, market, krx_dict)
        
        with st.spinner('데이터 분석 중...'):
            df = yf.download(ticker_symbol, period='1y', progress=False)
            if df.empty and '.KS' in ticker_symbol:
                df = yf.download(ticker_symbol.replace('.KS', '.KQ'), period='1y', progress=False)

            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                df['MA20'] = df['Close'].rolling(window=20).mean()
                df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
                latest = df.iloc[-1]
                
                st.subheader(f"📈 {user_input} ({ticker_symbol}) 분석 결과")
                col1, col2 = st.columns([2, 1])
                with col1:
                    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                    fig.update_layout(xaxis_rangeslider_visible=False, height=450, template='plotly_white')
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.metric("현재가", f"{latest['Close']:,.0f}")
                    st.metric("RSI (14)", f"{latest['RSI']:.2f}")

                # AI 분석 섹션 (에러 수정 포인트)
                st.markdown("---")
                st.write("### 🤖 AI 종합 투자 의견")
                
                if api_key:
                    try:
                        genai.configure(api_key=api_key)
                        # 모델명을 명확하게 지정하여 404 에러 방지
                        model = genai.GenerativeModel(model_name='gemini-1.5-flash')
                        
                        prompt = f"{user_input} 주식의 현재가 {latest['Close']:.0f}, RSI {latest['RSI']:.2f}를 기반으로 투자 조언을 해줘."
                        response = model.generate_content(prompt)
                        st.info(response.text)
                    except Exception as e:
                        # 1.5-flash가 안될 경우 1.0-pro로 재시도 로직
                        try:
                            model = genai.GenerativeModel(model_name='gemini-1.0-pro')
                            response = model.generate_content(prompt)
                            st.info(response.text)
                        except:
                            st.error(f"AI 호출 실패. API 키 권한이나 모델 설정을 확인해주세요: {e}")
            else:
                st.error("데이터를 찾을 수 없습니다.")

if __name__ == "__main__":
    main()
