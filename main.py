import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
import fear_and_greed

# 페이지 설정 (반응형 layout)
st.set_page_config(page_title="AI Pro 주식 진단 대시보드", page_icon="📈", layout="wide")

# --- 전문적인 대시보드를 위한 커스텀 CSS 스타일링 ---
st.markdown("""
<style>
    /* 배경 및 전반적인 텍스트 색상 */
    .stApp { background-color: #161A25; color: #E0E2E6; }
    
    /* 카드 스타일링 (박스형 레이아웃) */
    .css-1r6slb0, .css-1r16z1y {
        border-radius: 10px;
        background-color: #1F2331;
        padding: 20px;
        border: 1px solid #2D3243;
        margin-bottom: 20px;
    }
    
    /* Metric(주요 지표) 타이틀 및 값 스타일 */
    .stMetric label { color: #A0AEC0 !important; font-size: 1.1rem !important; }
    .stMetric div[data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 2.2rem !important; font-weight: 700 !important; }
    
    /* 서브 헤더 스타일 */
    h3, h4 { color: #EDF2F7 !important; border-bottom: 2px solid #3182CE; padding-bottom: 5px; margin-bottom: 15px; }

    /* AI 응답 박스 스타일 */
    .ai-response {
        background-color: #1A1D27;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #3182CE;
        color: #D1D5DB;
        line-height: 1.7;
    }
</style>
""", unsafe_allow_html=True)

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

def get_exchange_rate():
    try:
        data = yf.download("USDKRW=X", period="1d", progress=False)
        return data['Close'].iloc[-1]
    except: return None

def main():
    # 사이드바 (필요한 설정만 노출)
    st.sidebar.markdown("### 🔧 **Professional Settings**")
    market = st.sidebar.selectbox("시장 선택", ["KR", "US"], index=0)
    krx_dict = get_krx_list() if market == 'KR' else {}
    default_val = "삼성전자" if market == 'KR' else "AAPL"
    user_input = st.sidebar.text_input("종목명 또는 코드", value=default_val)
    
    if "GEMINI_API_KEY" in st.secrets: api_key = st.secrets["GEMINI_API_KEY"]
    else: api_key = st.sidebar.text_input("Google Gemini API Key", type="password")

    # --- 메인 상단: Macro Overview 섹션 (Card 스타일) ---
    st.markdown("#### 🌍 **Macro Market Overview**")
    m_col1, m_col2, m_col3 = st.columns([2, 2, 1])
    
    with m_col1:
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        try:
            fg_data = fear_and_greed.get()
            fg_color = "red" if fg_data.score < 40 else "green" if fg_data.score > 60 else "#E0E2E6"
            st.metric("Fear & Greed Index", f"{fg_data.score:.0f}", fg_data.description)
        except: st.caption("F&G 로드 실패")
        st.markdown('</div>', unsafe_allow_html=True)
            
    with m_col2:
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        rate = get_exchange_rate()
        if rate is not None: st.metric("USD/KRW 환율", f"{rate:,.2f} 원")
        else: st.caption("환율 로드 실패")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True) # 여백

    # --- 분석 실행 logic 및 UI 출력 ---
    if st.sidebar.button("📊 **전문 분석 실행**", use_container_width=True):
        ticker_symbol = get_full_ticker(user_input, market, krx_dict)
        
        with st.spinner('Pro 서버에서 데이터를 분석 중입니다...'):
            df = yf.download(ticker_symbol, period='1y', progress=False)
            if df.empty and '.KS' in ticker_symbol:
                df = yf.download(ticker_symbol.replace('.KS', '.KQ'), period='1y', progress=False)

            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                df['MA20'] = df['Close'].rolling(window=20).mean()
                df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
                latest = df.iloc[-1]
                
                # --- 메인 분석 화면: 전문적인 레이아웃 ---
                st.subheader(f"📈 {user_input} ({ticker_symbol}) **Pro Diagnostic Report**")
                
                # Row 1: 주요 Metric 카드 배치 (예시 이미지의 Website Impressions 스타일)
                st.markdown("#### 📊 핵심 기술 지표")
                met1, met2, met3, met4 = st.columns(4)
                
                with met1:
                    st.markdown('<div class="card-box">', unsafe_allow_html=True)
                    price_diff = latest['Close'] - df.iloc[-2]['Close']
                    st.metric("현재가", f"{latest['Close']:,.0f}", f"{price_diff:,.0f} 원")
                    st.markdown('</div>', unsafe_allow_html=True)
                with met2:
                    st.markdown('<div class="card-box">', unsafe_allow_html=True)
                    rsi_color = "🔴" if latest['RSI'] > 70 else "🟢" if latest['RSI'] < 30 else ""
                    st.metric("RSI (14) {rsi_color}", f"{latest['RSI']:.2f}")
                    st.markdown('</div>', unsafe_allow_html=True)
                with met3:
                    st.markdown('<div class="card-box">', unsafe_allow_html=True)
                    val_unit = "억 원" if market == 'KR' else "USD"
                    trading_val = (latest['Close'] * latest['Volume']) / (100000000 if market == 'KR' else 1)
                    st.metric("당일 거래대금", f"{trading_val:,.1f} {val_unit}")
                    st.markdown('</div>', unsafe_allow_html=True)
                with met4:
                    st.markdown('<div class="card-box">', unsafe_allow_html=True)
                    ma_signal = "🟢 붕괴" if latest['Close'] > latest['MA20'] else "🔴 돌파"
                    st.metric("20일 이평선 신호", ma_signal)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Row 2: 차트와 AI 의견 (메인 화면)
                graph_col, ai_col = st.columns([2, 1])
                
                with graph_col:
                    st.markdown("#### 캔들스틱 차트")
                    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                    # 다크 모드 차트 설정
                    fig.update_layout(
                        xaxis_rangeslider_visible=False, 
                        height=500, 
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(t=10, b=10, l=10, r=10)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with ai_col:
                    st.markdown("#### 🤖 AI 종합 투자 의견")
                    if api_key:
                        try:
                            genai.configure(api_key=api_key)
                            # Fallback 로직 유지
                            try:
                                model = genai.GenerativeModel('gemini-3-flash-preview')
                                response = model.generate_content(f"{user_input} ({ticker_symbol}) Pro 분석: 현재가 {latest['Close']}, RSI {latest['RSI']:.2f}. 전문 리포트를 작성해줘.")
                                st.markdown(f'<div class="ai-response">✨ **Gemini 3 Flash Pro 리포트:**<br><br>{response.text}</div>', unsafe_allow_html=True)
                            except:
                                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                                response = model.generate_content(f"{user_input} ({ticker_symbol}) Pro 분석: 현재가 {latest['Close']}, RSI {latest['RSI']:.2f}")
                                st.markdown(f'<div class="ai-response">📊 **Gemini 1.5 Flash Pro 리포트:**<br><br>{response.text}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"AI 호출 에러: {e}")
                    else:
                        st.warning("⚠️ AI 의견을 보려면 API Key가 필요합니다.")
            else:
                st.error("주식 데이터를 불러올 수 없습니다.")

if __name__ == "__main__":
    main()
