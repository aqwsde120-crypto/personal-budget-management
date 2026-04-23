import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from google import genai
from ta.momentum import RSIIndicator
from ta.trend import MACD

# 페이지 설정
st.set_page_config(
    page_title="AI 주식 통합 진단 대시보드",
    page_icon="📈",
    layout="wide"
)

# [UI 개선] 토스 스타일: 화이트 배경 및 깔끔한 전문 UI 설정
st.markdown("""
    <style>
    /* 전체 배경화면 흰색 */
    .stApp {
        background-color: #FFFFFF;
    }
    /* 제목 스타일 (Toss Dark Grey) */
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #333D4B;
        text-align: left;
        margin-bottom: 2rem;
        padding-left: 10px;
    }
    /* 메트릭 카드 스타일 */
    div[data-testid="stMetric"] {
        background-color: #F9FAFB;
        border: 1px solid #F2F4F6;
        border-radius: 16px;
        padding: 20px;
        transition: all 0.3s ease;
    }
    div[data-testid="stMetric"]:hover {
        background-color: #F2F4F6;
        transform: translateY(-2px);
    }
    /* 구분선 스타일 */
    hr {
        border: 0;
        height: 1px;
        background: #F2F4F6;
        margin: 2rem 0;
    }
    /* 사이드바 스타일 */
    .css-1d391kg {
        background-color: #F9FAFB;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">📈 AI 주식 통합 진단</h1>', unsafe_allow_html=True)

def get_stock_data(ticker, market='US', period='1y'):
    try:
        if market == 'KR':
            end_date = datetime.now()
            start_date = end_date - timedelta(days=400) # 충분한 데이터 확보
            df = fdr.DataReader(ticker, start_date, end_date)
        else:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
        return df
    except Exception as e:
        st.error(f"데이터 가져오기 실패: {e}")
        return None

def get_financial_metrics(ticker, market='US'):
    # [N/A 해결] yfinance 데이터 수집 안정화
    try:
        symbol = ticker if market == 'US' else (ticker + ".KS" if len(ticker) == 6 else ticker)
        stock = yf.Ticker(symbol)
        info = stock.info
        
        if not info or 'regularMarketPrice' not in info:
            info = {}

        def safe_get(key, default='N/A'):
            val = info.get(key, default)
            if val is None or val == 'N/A': return 'N/A'
            return val

        metrics = {
            'PER': safe_get('trailingPE'),
            'PBR': safe_get('priceToBook'),
            'ROE': safe_get('returnOnEquity'),
            '배당수익률': safe_get('dividendYield'),
            '시가총액': safe_get('marketCap'),
            '52주 최고가': safe_get('fiftyTwoWeekHigh'),
            '52주 최저가': safe_get('fiftyTwoWeekLow'),
            '베타': safe_get('beta')
        }
        
        # 포맷팅 로직
        if isinstance(metrics['PER'], (int, float)): metrics['PER'] = f"{metrics['PER']:.2f}"
        if isinstance(metrics['PBR'], (int, float)): metrics['PBR'] = f"{metrics['PBR']:.2f}"
        if isinstance(metrics['ROE'], (int, float)): metrics['ROE'] = f"{metrics['ROE']*100:.2f}%"
        if isinstance(metrics['배당수익률'], (int, float)): metrics['배당수익률'] = f"{metrics['배당수익률']*100:.2f}%"
        if isinstance(metrics['시가총액'], (int, float)):
            metrics['시가총액'] = f"${metrics['시가총액']/1e9:.2f}B" if market == 'US' else f"₩{metrics['시가총액']/1e12:.2f}조"
        
        return metrics
    except Exception:
        return {k: 'N/A' for k in ['PER', 'PBR', 'ROE', '배당수익률', '시가총액', '52주 최고가', '52주 최저가', '베타']}

def calculate_technical_indicators(df):
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
    df['Trading_Value'] = df['Close'] * df['Volume']
    return df

def detect_pullback(df):
    if len(df) < 20:
        return {'is_pullback': False, 'reason': '데이터 부족', 'details': {}}
    
    latest = df.iloc[-1]
    current_price = latest['Close']
    ma20 = latest['MA20']
    
    above_ma20 = current_price > ma20
    distance_from_ma20 = ((current_price - ma20) / ma20) * 100
    near_ma20 = 0 <= distance_from_ma20 <= 3
    
    recent_volume = df['Volume'].iloc[-5:-1].mean()
    previous_volume = df['Volume'].iloc[-15:-5].mean()
    volume_decreasing = recent_volume < previous_volume
    
    is_pullback = above_ma20 and near_ma20 and volume_decreasing
    
    details = {
        '현재가': f"{current_price:,.0f}",
        '20일선': f"{ma20:,.0f}",
        '거리': f"{distance_from_ma20:.2f}%",
        '20일선 상단': '✓' if above_ma20 else '✗',
        '20일선 근접': '✓' if near_ma20 else '✗',
        '거래량 감소': '✓' if volume_decreasing else '✗'
    }
    
    reason = "눌림목 감지!" if is_pullback else "눌림목 조건 미충족"
    return {'is_pullback': is_pullback, 'reason': reason, 'details': details}

def get_macro_indicators():
    # [SyntaxError 해결] 중복 구문 제거 및 예외 처리 단일화
    try:
        tnx = yf.Ticker("^TNX").history(period='5d')
        krw = yf.Ticker("KRW=X").history(period='5d')
        
        res = {}
        for name, data in [('미국10년물금리', tnx), ('원달러환율', krw)]:
            if not data.empty and len(data) >= 2:
                curr, prev = data['Close'].iloc[-1], data['Close'].iloc[-2]
                change = ((curr - prev) / prev) * 100
                res[name] = {'현재': f"{curr:.2f}%" if '금리' in name else f"{curr:.2f}", 
                             '변화': f"{change:+.2f}%"}
            else:
                res[name] = {'현재': 'N/A', '변화': 'N/A'}
        return res
    except Exception:
        return {'미국10년물금리': {'현재': 'N/A', '변화': 'N/A'}, '원달러환율': {'현재': 'N/A', '변화': 'N/A'}}

def create_candlestick_chart(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='MA20', line=dict(color='#4ECDC4')), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color='#F2F4F6'), row=2, col=1)
    fig.update_layout(height=500, template='plotly_white', showlegend=False, xaxis_rangeslider_visible=False)
    return fig

def generate_ai_analysis(ticker, financial_metrics, pullback_info, df, macro_indicators, api_key):
    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""
        종목 {ticker} 투자 분석

        재무: {financial_metrics}
        눌림목: {pullback_info}
        거시경제: {macro_indicators}

        1. 현재 상태
        2. 투자 의견
        3. 리스크
        4. 결론
        """

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        return response.text

    except Exception as e:
        return f"분석 실패: {str(e)}"

def main():
    st.sidebar.markdown("### ⚙️ 분석 설정")
    market = st.sidebar.selectbox("시장 선택", ["US", "KR"])
    ticker = st.sidebar.text_input("종목 코드", value="AAPL" if market == "US" else "005930")
    
    # [403 해결] 사용자 입력 API 키를 우선 사용
    user_api_key = st.sidebar.text_input("Gemini API Key", type="password", placeholder="AI Studio에서 발급받은 키 입력")
    # secrets.toml에 있는 유출된 키는 무시하고 사용자 입력을 권장
    api_key = user_api_key if user_api_key else st.secrets.get("GOOGLE_API_KEY", "")

    if st.sidebar.button("📊 분석 실행", type="primary"):
        df = get_stock_data(ticker, market)
        if df is not None:
            df = calculate_technical_indicators(df)
            metrics = get_financial_metrics(ticker, market)
            pullback = detect_pullback(df)
            macro = get_macro_indicators()

            # 상단 지표
            st.subheader("주요 재무 지표")
            m_cols = st.columns(4)
            keys = list(metrics.keys())
            for i in range(4): m_cols[i].metric(keys[i], metrics[keys[i]])
            m_cols2 = st.columns(4)
            for i in range(4, 8): m_cols2[i-4].metric(keys[i], metrics[keys[i]])
            
            st.divider()

            # 중간 차트 및 거시 지표
            c1, c2 = st.columns([2, 1])
            with c1:
                st.plotly_chart(create_candlestick_chart(df), use_container_width=True)
            with c2:
                st.markdown("#### 🎯 분석 결과")
                if pullback['is_pullback']: st.success(pullback['reason'])
                else: st.info(pullback['reason'])
                
                st.markdown("#### 🌍 거시 경제")
                st.metric("미국 10년물 금리", macro['미국10년물금리']['현재'], macro['미국10년물금리']['변화'])
                st.metric("원달러 환율", macro['원달러환율']['현재'], macro['원달러환율']['변화'])

            st.divider()

            # AI 분석
            st.subheader("🤖 AI 종합 투자 분석")
            if api_key:
                st.write(generate_ai_analysis(ticker, metrics, pullback, df, macro, api_key))
            else:
                st.warning("API 키를 입력하면 AI 분석을 볼 수 있습니다.")
        else:
            st.error("데이터를 불러오지 못했습니다.")

if __name__ == "__main__":
    main()
