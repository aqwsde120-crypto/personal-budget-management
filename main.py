import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import anthropic
from ta.momentum import RSIIndicator
from ta.trend import MACD

# 페이지 설정
st.set_page_config(
    page_title="AI 주식 통합 진단 대시보드",
    page_icon="📈",
    layout="wide"
)

# 스타일 설정
st.markdown("""
    <style>
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">📈 AI 주식 통합 진단 대시보드</h1>', unsafe_allow_html=True)

def get_full_ticker(ticker, market):
    """시장 선택에 따라 yfinance용 티커 포맷으로 변환"""
    if market == 'KR':
        if ticker.isdigit():
            return f"{ticker}.KS"
    return ticker

def get_stock_data(ticker, market='US', period='1y'):
    full_ticker = get_full_ticker(ticker, market)
    try:
        # FinanceDataReader 대신 yfinance만 사용
        df = yf.download(full_ticker, period=period, progress=False)
        if df.empty and market == 'KR':
            # .KS로 실패 시 .KQ(코스닥)로 재시도
            full_ticker = f"{ticker}.KQ"
            df = yf.download(full_ticker, period=period, progress=False)
        
        # yfinance 최신 버전 멀티인덱스 대응
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        return df
    except Exception as e:
        st.error(f"데이터 가져오기 실패: {e}")
        return None

def get_financial_metrics(ticker, market='US'):
    full_ticker = get_full_ticker(ticker, market)
    try:
        stock = yf.Ticker(full_ticker)
        info = stock.info
        
        metrics = {
            'PER': info.get('trailingPE', 'N/A'),
            'PBR': info.get('priceToBook', 'N/A'),
            'ROE': info.get('returnOnEquity', 'N/A'),
            '배당수익률': info.get('dividendYield', 'N/A'),
            '시가총액': info.get('marketCap', 'N/A'),
            '52주 최고가': info.get('fiftyTwoWeekHigh', 'N/A'),
            '52주 최저가': info.get('fiftyTwoWeekLow', 'N/A'),
            '베타': info.get('beta', 'N/A')
        }
        
        # 포맷팅
        if isinstance(metrics['ROE'], (int, float)):
            metrics['ROE'] = f"{metrics['ROE']*100:.2f}%"
        if isinstance(metrics['배당수익률'], (int, float)):
            metrics['배당수익률'] = f"{metrics['배당수익률']*100:.2f}%"
        if isinstance(metrics['시가총액'], (int, float)):
            metrics['시가총액'] = f"{metrics['시가총액']:,.0f}"
        
        return metrics
    except:
        return {k: 'N/A' for k in ['PER', 'PBR', 'ROE', '배당수익률', '시가총액', '52주 최고가', '52주 최저가', '베타']}

def calculate_technical_indicators(df, market='US'):
    df = df.copy()
    
    # 이동평균선
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    
    # RSI
    rsi = RSIIndicator(close=df['Close'], window=14)
    df['RSI'] = rsi.rsi()
    
    # MACD
    macd = MACD(close=df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()
    
    # 거래대금 계산 (한국 주식은 억 단위 변환 요청 반영)
    if market == 'KR':
        df['Trading_Value'] = (df['Close'] * df['Volume']) / 100000000
    else:
        df['Trading_Value'] = df['Close'] * df['Volume']
        
    return df

def detect_pullback(df):
    if len(df) < 20:
        return {'is_pullback': False, 'reason': '데이터 부족', 'details': {}}
    
    latest = df.iloc[-1]
    current_price = float(latest['Close'])
    ma20 = float(latest['MA20'])
    
    above_ma20 = current_price > ma20
    distance_from_ma20 = ((current_price - ma20) / ma20) * 100
    near_ma20 = 0 <= distance_from_ma20 <= 3
    
    recent_volume = df['Volume'].iloc[-5:-1].mean()
    previous_volume = df['Volume'].iloc[-15:-5].mean()
    volume_decreasing = recent_volume < previous_volume
    
    is_pullback = above_ma20 and near_ma20 and volume_decreasing
    
    details = {
        '현재가': f"{current_price:,.2f}",
        '20일선': f"{ma20:,.2f}",
        '20일선 대비 거리': f"{distance_from_ma20:.2f}%",
        '최근5일 평균거래량': f"{recent_volume:,.0f}",
        '이전10일 평균거래량': f"{previous_volume:,.0f}",
        '20일선 상단': '✓' if above_ma20 else '✗',
        '20일선 근접(3%이내)': '✓' if near_ma20 else '✗',
        '거래량 감소': '✓' if volume_decreasing else '✗'
    }
    
    if is_pullback:
        reason = "눌림목 패턴 감지! 20일선 상단에서 근접하며 거래량이 감소하고 있습니다."
    elif not above_ma20:
        reason = "20일선 하단에 위치하여 눌림목이 아닙니다."
    elif not near_ma20:
        reason = f"20일선과의 거리({distance_from_ma20:.2f}%)가 3%를 초과하여 눌림목이 아닙니다."
    elif not volume_decreasing:
        reason = "거래량이 감소하지 않아 에너지 응축 신호가 없습니다."
    else:
        reason = "눌림목 조건을 충족하지 않습니다."
        
    return {'is_pullback': is_pullback, 'reason': reason, 'details': details}

def get_macro_indicators():
    try:
        tnx = yf.download("^TNX", period='5d', progress=False)['Close']
        krw = yf.download("KRW=X", period='5d', progress=False)['Close']
        
        if isinstance(tnx, pd.DataFrame): tnx = tnx.iloc[:, 0]
        if isinstance(krw, pd.DataFrame): krw = krw.iloc[:, 0]

        return {
            '미국10년물금리': {'현재': f"{tnx.iloc[-1]:.2f}%", '변화': f"{((tnx.iloc[-1]-tnx.iloc[-2])/tnx.iloc[-2]*100):+.2f}%"},
            '원달러환율': {'현재': f"{krw.iloc[-1]:,.2f}", '변화': f"{((krw.iloc[-1]-krw.iloc[-2])/krw.iloc[-2]*100):+.2f}%"}
        }
    except:
        return {'미국10년물금리': {'현재': 'N/A', '변화': 'N/A'}, '원달러환율': {'현재': 'N/A', '변화': 'N/A'}}

def create_candlestick_chart(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    
    for ma, color in zip(['MA5', 'MA20', 'MA60', 'MA120'], ['#FF6B6B', '#4ECDC4', '#FFD93D', '#95E1D3']):
        fig.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma, line=dict(color=color, width=1.5)), row=1, col=1)
        
    colors = ['#FF6B6B' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#4ECDC4' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color=colors, opacity=0.5), row=2, col=1)
    
    fig.update_layout(height=600, template='plotly_white', xaxis_rangeslider_visible=False)
    return fig

def generate_ai_analysis(ticker, financial_metrics, pullback_info, df, macro_indicators, api_key, market='US'):
    latest = df.iloc[-1]
    
    # 한국과 미국 시장의 거래대금 단위 텍스트 다원화
    tv_unit = "억 원" if market == 'KR' else "USD"
    
    prompt = f"""당신은 전문 금융 애널리스트입니다. 다음 정보를 바탕으로 '{ticker}' 종목에 대한 종합 투자 의견을 제시해주세요.

## 1. 재무 지표
{chr(10).join([f'- {k}: {v}' for k, v in financial_metrics.items()])}

## 2. 눌림목(Pullback) 분석
- 눌림목 여부: {'✓ 감지됨' if pullback_info['is_pullback'] else '✗ 미감지'}
- 분석: {pullback_info['reason']}
- 세부사항:
{chr(10).join([f'  - {k}: {v}' for k, v in pullback_info['details'].items()])}

## 3. 기술적 지표
- 현재가: {latest['Close']:.2f}
- RSI(14): {latest['RSI']:.2f}
- MACD: {latest['MACD']:.2f}
- 당일 거래대금: {latest['Trading_Value']:,.2f} {tv_unit}
- MA5: {latest['MA5']:.2f}
- MA20: {latest['MA20']:.2f}
- MA60: {latest['MA60']:.2f}

## 4. 거시 경제 환경
- 미국 10년물 국채 금리: {macro_indicators['미국10년물금리']['현재']} ({macro_indicators['미국10년물금리']['변화']})
- 원/달러 환율: {macro_indicators['원달러환율']['현재']} ({macro_indicators['원달러환율']['변화']})

## 요청사항
위 모든 정보를 종합하여 다음 형식으로 답변해주세요:

1. **투자 의견**: 매수 / 매도 / 보유 중 하나를 명확히 제시
2. **기술적 근거**: 차트와 기술적 지표를 기반으로 한 분석 (3-4문장)
3. **재무적 근거**: 재무 지표를 기반으로 한 분석 (2-3문장)
4. **거시 환경 영향**: 금리와 환율이 해당 종목에 미치는 영향 (2-3문장)
5. **위험 요소**: 주의해야 할 리스크 (2-3문장)
6. **목표가 및 손절가**: 구체적인 가격대 제시
"""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        # 안정성이 검증된 Claude 3.5 Sonnet 최신 모델명으로 수정
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"AI 분석 실패: {e}\n[참고] Anthropic API 키나 결제 계정 상태를 확인해 주세요."

def main():
    st.sidebar.header("🔧 설정")
    market = st.sidebar.selectbox("시장 선택", ["KR", "US"])
    ticker = st.sidebar.text_input("종목 코드 입력", value="005930" if market=="KR" else "AAPL")
    api_key = st.sidebar.text_input("Anthropic API Key", type="password")
    
    if st.sidebar.button("📊 분석 실행"):
        df = get_stock_data(ticker, market)
        if df is not None and not df.empty:
            df = calculate_technical_indicators(df, market=market)
            metrics = get_financial_metrics(ticker, market)
            pullback = detect_pullback(df)
            macro = get_macro_indicators()
            
            # 상단: 재무 지표
            st.subheader("📊 주요 재무 지표")
            c1, c2, c3, c4 = st.columns(4)
            metrics_items = list(metrics.items())
            
            for idx, (key, value) in enumerate(metrics_items[:4]):
                with [c1, c2, c3, c4][idx]:
                    st.metric(label=key, value=value)
            
            c5, c6, c7, c8 = st.columns(4)
            for idx, (key, value) in enumerate(metrics_items[4:]):
                with [c5, c6, c7, c8][idx]:
                    st.metric(label=key, value=value)
                    
            st.divider()
            
            # 중단: 차트 및 눌림목 분석
            col_chart, col_side = st.columns([2, 1])
            with col_chart:
                st.subheader("📈 주가 차트")
                st.plotly_chart(create_candlestick_chart(df), use_container_width=True)
            with col_side:
                st.subheader("🎯 패턴 및 지표 분석")
                
                if pullback['is_pullback']:
                    st.success(pullback['reason'])
                else:
                    st.info(pullback['reason'])
                    
                st.write("**세부 분석**")
                for key, value in pullback['details'].items():
                    st.text(f"{key}: {value}")
                    
                st.divider()
                
                # 거래대금 표시 (한국 시장 '억 원' 단위)
                tv_unit = "억 원" if market == 'KR' else "USD"
                st.metric("당일 거래대금", f"{df.iloc[-1]['Trading_Value']:,.1f} {tv_unit}")
                
                st.divider()
                st.subheader("🌍 거시 경제 지표")
                st.metric("미국 10년 금리", macro['미국10년물금리']['현재'], macro['미국10년물금리']['변화'])
                st.metric("원달러 환율", macro['원달러환율']['현재'], macro['원달러환율']['변화'])
                
            st.divider()
            
            # 하단: AI 분석
            if api_key:
                st.subheader("🤖 AI 종합 투자 의견")
                with st.spinner('AI 분석을 생성하는 중...'):
                    st.write(generate_ai_analysis(ticker, metrics, pullback, df, macro, api_key, market=market))
            else:
                st.warning("⚠️ Anthropic API 키를 입력하면 AI 분석을 확인할 수 있습니다.")
        else:
            st.error("종목 데이터를 불러오지 못했습니다. 종목 코드와 시장 선택을 확인해 주세요.")
    else:
        st.info("👈 왼쪽 사이드바에서 종목을 선택하고 '분석 실행' 버튼을 클릭하세요.")

if __name__ == "__main__":
    main()
