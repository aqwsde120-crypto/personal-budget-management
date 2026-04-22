import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
import fear_and_greed

# 페이지 설정
st.set_page_config(page_title="AI Pro 주식 진단", page_icon="📈", layout="wide")

# CSS 스타일 (Dark Dashboard 및 통화 표시 최적화)
st.markdown("""
<style>
    .stApp { background-color: #11141C; color: #E0E2E6; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    .ai-box {
        background-color: #1A1E29;
        padding: 20px;
        border-left: 5px solid #3182CE;
        border-radius: 8px;
        line-height: 1.6;
    }
    .card-label { color: #A0AEC0; font-size: 0.9rem; margin-bottom: 5px; }
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
        data = yf.download("USDKRW=X", period="1d", progress=False)
        if not data.empty:
            return float(data['Close'].iloc[-1])
        return None
    except: return None

def main():
    st.sidebar.markdown("### 🔧 **Settings**")
    market = st.sidebar.selectbox("시장 선택", ["KR", "US"])
    krx_dict = get_krx_list() if market == 'KR' else {}
    user_input = st.sidebar.text_input("종목명 또는 코드", value="삼성전자" if market == 'KR' else "AAPL")
    
    api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password")

    # 환율 데이터 미리 로드
    rate = get_exchange_rate()

    # --- Macro Overview ---
    st.markdown("#### 🌍 **Macro Market Overview**")
    m1, m2 = st.columns(2)
    with m1:
        try:
            fg_data = fear_and_greed.get()
            st.metric("Fear & Greed Index", f"{fg_data.score:.0f}", fg_data.description)
        except: st.info("Fear & Greed 로드 중...")
    with m2:
        if rate:
            st.metric("실시간 USD/KRW 환율", f"{rate:,.2f} 원")
        else: st.info("환율 정보를 가져올 수 없습니다.")

    st.divider()

    if st.sidebar.button("📊 분석 실행", use_container_width=True):
        ticker = user_input.strip()
        if market == 'KR':
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
                prev_close = df.iloc[-2]['Close']

                # 가격 계산 (한화 환산)
                current_price = float(latest['Close'])
                if market == 'US' and rate:
                    krw_price = current_price * rate
                    price_display = f"${current_price:,.2f}"
                    sub_display = f"약 {krw_price:,.0f} 원"
                else:
                    price_display = f"{current_price:,.0f} 원"
                    sub_display = f"전일비: {(current_price - prev_close):,.0f}"

                # --- UI 출력 ---
                st.subheader(f"📈 {user_input} ({ticker}) 분석")
                
                # 상단 메트릭 카드
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("현재가", price_display, sub_display)
                with c2:
                    st.metric("RSI (14)", f"{latest['RSI']:.2f}")
                with c3:
                    ma_val = f"${latest['MA20']:,.2f}" if market == 'US' else f"{latest['MA20']:,.0f}원"
                    st.metric("20일 이평선", ma_val)

                # 차트 및 AI 섹션
                g_col, a_col = st.columns([2, 1])
                with g_col:
                    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                    fig.update_layout(xaxis_rangeslider_visible=False, template='plotly_dark', height=480)
                    st.plotly_chart(fig, use_container_width=True)
                
                with a_col:
                    st.markdown("#### 🤖 AI 투자 전략")
                    if api_key:
                        try:
                            genai.configure(api_key=api_key)
                            model = genai.GenerativeModel('gemini-3-flash-preview')
                            prompt = f"{user_input} 분석: 현재가 {price_display}, 한화 약 {sub_display if market=='US' else ''}. RSI {latest['RSI']:.2f} 기반 대응책 제시."
                            res = model.generate_content(prompt)
                            st.markdown(f'<div class="ai-box">{res.text}</div>', unsafe_allow_html=True)
                        except:
                            st.write("AI 분석 리포트를 생성할 수 없습니다.")
            else: st.error("종목 데이터를 확인해 주세요.")

if __name__ == "__main__":
    main()
