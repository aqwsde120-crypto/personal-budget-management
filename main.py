import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
import fear_and_greed

# 페이지 설정
st.set_page_config(page_title="AI 주식 진단", page_icon="📈", layout="wide")

# --- 토스 스타일 CSS (화이트 테마) ---
st.markdown("""
<style>
    /* 전체 배경을 밝은 회색/흰색으로 설정 */
    .stApp { background-color: #F2F4F6; color: #191F28; }
    
    /* 사이드바 스타일링 */
    section[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E5E8EB; }
    
    /* 카드 컨테이너 스타일 */
    .toss-card {
        background-color: #FFFFFF;
        padding: 24px;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    
    /* 메트릭 폰트 및 스타일 */
    [data-testid="stMetricLabel"] { font-size: 1rem !important; color: #4E5968 !important; font-weight: 500 !important; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #191F28 !important; font-weight: 700 !important; }
    
    /* 제목 스타일 */
    h1, h2, h3, h4 { color: #191F28 !important; font-weight: 700 !important; border: none !important; }
    
    /* AI 박스 스타일 */
    .ai-box {
        background-color: #F9FAFB;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #E5E8EB;
        color: #333D4B;
        line-height: 1.8;
    }
    
    /* 버튼 스타일 커스텀 */
    .stButton>button {
        background-color: #3182F6 !important; /* 토스 블루 */
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
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
    # --- 사이드바 설정 ---
    st.sidebar.title("설정")
    market = st.sidebar.selectbox("시장", ["KR", "US"])
    krx_dict = get_krx_list() if market == "KR" else {}
    user_input = st.sidebar.text_input("종목명 또는 코드", value="삼성전자" if market == "KR" else "AAPL")
    api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password")

    # 데이터 로드
    rate = get_exchange_rate()
    
    # --- 메인 화면 시작 ---
    st.title("시장 요약")
    
    # 상단 요약 카드 (Fear & Greed, 환율)
    col_fg, col_ex = st.columns(2)
    
    with col_fg:
        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
        try:
            fg = fear_and_greed.get()
            st.metric("공포와 탐욕 지수", f"{fg.score:.0f}", fg.description)
        except:
            st.metric("공포와 탐욕 지수", "-", "데이터 연결 중")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_ex:
        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
        if rate:
            st.metric("실시간 환율 (USD/KRW)", f"{rate:,.2f}원")
        else:
            st.metric("실시간 환율 (USD/KRW)", "-", "데이터 로드 실패")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.sidebar.button("분석하기"):
        ticker = user_input.strip()
        if market == "KR":
            if ticker in krx_dict: ticker = f"{krx_dict[ticker]}.KS"
            elif ticker.isdigit(): ticker = f"{ticker}.KS"

        with st.spinner('데이터 분석 중...'):
            df = yf.download(ticker, period='1y', progress=False)
            if df.empty and '.KS' in ticker:
                df = yf.download(ticker.replace('.KS', '.KQ'), period='1y', progress=False)

            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df['MA20'] = df['Close'].rolling(window=20).mean()
                df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
                latest = df.iloc[-1]
                prev = df.iloc[-2]

                # 가격 계산
                curr_price = float(latest['Close'])
                if market == "US" and rate:
                    krw_price = curr_price * rate
                    price_val = f"${curr_price:,.2f}"
                    price_sub = f"약 {krw_price:,.0f}원"
                else:
                    price_val = f"{curr_price:,.0f}원"
                    price_sub = f"전일비 {curr_price - prev['Close']:,.0f}"

                # --- 분석 상세 대시보드 ---
                st.markdown(f"## {user_input} 분석 결과")
                
                # 핵심 지표 3열
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

                # 차트 및 AI 의견
                c_chart, c_ai = st.columns([2, 1])
                
                with c_chart:
                    st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                    st.markdown("#### 주가 흐름")
                    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                    fig.update_layout(
                        xaxis_rangeslider_visible=False, 
                        template='plotly_white', 
                        height=500,
                        margin=dict(t=0, b=0, l=0, r=0)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                with c_ai:
                    st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                    st.markdown("#### 🤖 AI 투자 제안")
                    if api_key:
                        try:
                            genai.configure(api_key=api_key)
                            # 1순위: Gemini 3 Flash Preview 시도
                            model = genai.GenerativeModel('gemini-3-flash-preview')
                            prompt = f"{user_input} 종목 분석: 현재가 {price_val}, RSI {latest['RSI']:.2f}. 전문적이고 친절한 투자 전략을 제안해줘."
                            res = model.generate_content(prompt)
                            st.markdown(f'<div class="ai-box">{res.text}</div>', unsafe_allow_html=True)
                        except:
                            st.write("AI 의견을 불러오는 중입니다...")
                    else:
                        st.info("사이드바에 API 키를 입력하면 AI 분석을 볼 수 있습니다.")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error("데이터를 찾을 수 없습니다. 종목 코드를 확인해 주세요.")

if __name__ == "__main__":
    main()
