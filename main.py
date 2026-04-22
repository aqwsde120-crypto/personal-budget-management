import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
import fear_and_greed
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="AI 주식 진단", page_icon="📈", layout="wide")

# --- 토스 스타일 CSS (화이트 테마) ---
st.markdown("""
<style>
    .stApp { background-color: #F2F4F6; color: #191F28; }
    section[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E5E8EB; }
    .toss-card {
        background-color: #FFFFFF;
        padding: 24px;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    [data-testid="stMetricLabel"] { font-size: 1rem !important; color: #4E5968 !important; font-weight: 500 !important; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #191F28 !important; font-weight: 700 !important; }
    h1, h2, h3, h4 { color: #191F28 !important; font-weight: 700 !important; border: none !important; }
    .ai-box {
        background-color: #F9FAFB;
        padding: 25px;
        border-radius: 16px;
        border: 1px solid #E5E8EB;
        color: #333D4B;
        line-height: 1.8;
        font-size: 1.05rem;
    }
    .stButton>button {
        background-color: #3182F6 !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def get_krx_list():
    try:
        url = 'http://kind.krx.co.kr/corpoide/corpList.do?method=download'
        df = pd.read_html(url, header=0)[0]
        return {name.strip(): f"{code:06d}" for name, code in zip(df['회사명'], df['종목코드'])}
    except: return {}

def get_exchange_rate():
    try:
        ticker = yf.Ticker("USDKRW=X")
        data = ticker.history(period="5d")
        return float(data['Close'].iloc[-1]) if not data.empty else None
    except: return None

def main():
    st.sidebar.title("설정")
    market = st.sidebar.selectbox("시장", ["KR", "US"])
    krx_dict = get_krx_list() if market == "KR" else {}
    user_input = st.sidebar.text_input("종목명 또는 코드", value="삼성전자" if market == "KR" else "AAPL")
    api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password")

    rate = get_exchange_rate()
    
    st.title("시장 요약")
    col_fg, col_ex = st.columns(2)
    
    with col_fg:
        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
        try:
            fg = fear_and_greed.get()
            st.metric("공포와 탐욕 지수", f"{fg.score:.0f}", fg.description)
        except: st.metric("공포와 탐욕 지수", "-", "데이터 연결 중")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_ex:
        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
        if rate: st.metric("실시간 환율 (USD/KRW)", f"{rate:,.2f}원")
        else: st.metric("실시간 환율 (USD/KRW)", "-", "데이터 로드 실패")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.sidebar.button("분석하기"):
        ticker = user_input.strip()
        if market == "KR":
            if ticker in krx_dict: ticker = f"{krx_dict[ticker]}.KS"
            elif ticker.isdigit(): ticker = f"{ticker}.KS"

        with st.spinner('데이터 분석 중...'):
            # 최근 6개월 데이터 로드
            end_date = datetime.now()
            start_date = end_date - timedelta(days=180)
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if df.empty and '.KS' in ticker:
                df = yf.download(ticker.replace('.KS', '.KQ'), start=start_date, end=end_date, progress=False)

            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df['MA20'] = df['Close'].rolling(window=20).mean()
                df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
                latest = df.iloc[-1]
                prev = df.iloc[-2]

                curr_price = float(latest['Close'])
                if market == "US" and rate:
                    krw_price = curr_price * rate
                    price_val, price_sub = f"${curr_price:,.2f}", f"약 {krw_price:,.0f}원"
                else:
                    price_val, price_sub = f"{curr_price:,.0f}원", f"전일비 {curr_price - prev['Close']:,.0f}"

                st.markdown(f"## {user_input} 분석 리포트")
                
                # 지표 요약
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                    st.metric("현재가", price_val, price_sub)
                    st.markdown('</div>', unsafe_allow_html=True)
                with m2:
                    st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                    st.metric("RSI (심리 지표)", f"{latest['RSI']:.2f}")
                    st.markdown('</div>', unsafe_allow_html=True)
                with m3:
                    st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                    ma_display = f"${latest['MA20']:,.2f}" if market=="US" else f"{latest['MA20']:,.0f}원"
                    st.metric("20일 이동평균선", ma_display)
                    st.markdown('</div>', unsafe_allow_html=True)

                # --- 주가 흐름 (최근 6개월) ---
                st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                st.markdown("### 📊 주가 흐름 (최근 6개월)")
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.update_layout(xaxis_rangeslider_visible=False, template='plotly_white', height=500, margin=dict(t=20, b=20, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # --- AI 투자 의견 (차트 아래 배치) ---
                st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                st.markdown("### 🤖 AI 종합 투자 의견")
                if api_key:
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-3-flash-preview')
                        prompt = f"{user_input}의 최근 6개월 주가 데이터와 현재가 {price_val}(RSI {latest['RSI']:.2f})를 바탕으로 전문적인 투자 전략을 제안해줘. 특히 현재 가격이 실제 실시간 시장가와 일치하는지 확인하며 분석해줘."
                        res = model.generate_content(prompt)
                        st.markdown(f'<div class="ai-box">{res.text}</div>', unsafe_allow_html=True)
                    except: st.info("AI 분석 기능을 일시적으로 사용할 수 없습니다.")
                else: st.info("사이드바에 API 키를 입력해 주세요.")
                st.markdown('</div>', unsafe_allow_html=True)
            else: st.error("데이터를 불러올 수 없습니다.")

if __name__ == "__main__":
    main()
