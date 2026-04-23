import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import google.generativeai as genai
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
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">📈 AI 주식 통합 진단 대시보드</h1>', unsafe_allow_html=True)


def get_stock_data(ticker, market='US', period='1y'):
    """
    주식 데이터를 가져오는 함수
    
    Args:
        ticker: 종목 코드
        market: 'US' 또는 'KR'
        period: 데이터 기간
    
    Returns:
        DataFrame: 주가 데이터
    """
    try:
        if market == 'KR':
            # 한국 주식: FinanceDataReader 사용
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            df = fdr.DataReader(ticker, start_date, end_date)
            df = df.rename(columns={
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            })
        else:
            # 미국 주식: yfinance 사용
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
        
        return df
    except Exception as e:
        st.error(f"데이터 가져오기 실패: {e}")
        return None


def get_financial_metrics(ticker, market='US'):
    try:
        # Ticker 객체 생성 시 오류 방지를 위해 딜레이나 세션 추가 고려 가능
        symbol = ticker if market == 'US' else (ticker + ".KS" if len(ticker) == 6 else ticker)
        stock = yf.Ticker(symbol)
        
        # .info 접근 전 데이터 유무 확인
        info = {}
        try:
            info = stock.info
            if not info or 'regularMarketPrice' not in info:
                # 기본 정보가 없는 경우 빈 딕셔너리 처리
                info = {}
        except Exception:
            info = {}

        # 안전하게 값을 가져오는 내부 함수 강화
        def safe_get(key, default='N/A'):
            val = info.get(key, default)
            return val if val is not None and val != 'N/A' else default

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
        
        # 포맷팅
        try:
            if isinstance(metrics['PER'], (int, float)):
                metrics['PER'] = f"{metrics['PER']:.2f}"
            if isinstance(metrics['PBR'], (int, float)):
                metrics['PBR'] = f"{metrics['PBR']:.2f}"
            if isinstance(metrics['ROE'], (int, float)):
                metrics['ROE'] = f"{metrics['ROE']*100:.2f}%"
            if isinstance(metrics['배당수익률'], (int, float)):
                metrics['배당수익률'] = f"{metrics['배당수익률']*100:.2f}%"
            if isinstance(metrics['시가총액'], (int, float)):
                metrics['시가총액'] = f"${metrics['시가총액']/1e9:.2f}B" if market == 'US' else f"₩{metrics['시가총액']/1e12:.2f}조"
            if isinstance(metrics['52주 최고가'], (int, float)):
                metrics['52주 최고가'] = f"{metrics['52주 최고가']:.2f}"
            if isinstance(metrics['52주 최저가'], (int, float)):
                metrics['52주 최저가'] = f"{metrics['52주 최저가']:.2f}"
            if isinstance(metrics['베타'], (int, float)):
                metrics['베타'] = f"{metrics['베타']:.2f}"
        except Exception as e:
            # 포맷팅 실패해도 계속 진행
            pass
        
        return metrics
    except Exception as e:
        st.warning(f"재무 지표를 가져올 수 없습니다: {e}")
        return {
            'PER': 'N/A',
            'PBR': 'N/A',
            'ROE': 'N/A',
            '배당수익률': 'N/A',
            '시가총액': 'N/A',
            '52주 최고가': 'N/A',
            '52주 최저가': 'N/A',
            '베타': 'N/A'
        }


def calculate_technical_indicators(df):
    """
    기술적 지표를 계산하는 함수
    
    Args:
        df: 주가 데이터프레임
    
    Returns:
        DataFrame: 기술적 지표가 추가된 데이터프레임
    """
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
    
    # 거래대금 (종가 * 거래량)
    df['Trading_Value'] = df['Close'] * df['Volume']
    
    return df


def detect_pullback(df):
    """
    눌림목(Pullback) 패턴을 탐지하는 함수
    
    눌림목 조건:
    1. 현재가가 20일 이동평균선 상단에 위치 (20일선 위)
    2. 현재가가 20일선에 근접 (3% 이내)
    3. 최근 3~5일 평균 거래량이 이전 10일 평균 거래량보다 낮음 (에너지 응축)
    
    Args:
        df: 기술적 지표가 계산된 데이터프레임
    
    Returns:
        dict: 눌림목 분석 결과
    """
    if len(df) < 20:
        return {
            'is_pullback': False,
            'reason': '데이터 부족 (최소 20일 필요)',
            'details': {}
        }
    
    # 최신 데이터
    latest = df.iloc[-1]
    current_price = latest['Close']
    ma20 = latest['MA20']
    
    # 조건 1: 현재가가 20일 이평선 상단에 위치
    above_ma20 = current_price > ma20
    
    # 조건 2: 20일선에 근접 (3% 이내)
    distance_from_ma20 = ((current_price - ma20) / ma20) * 100
    near_ma20 = 0 <= distance_from_ma20 <= 3
    
    # 조건 3: 거래량 분석 (에너지 응축)
    # 최근 3~5일 평균 거래량
    recent_volume = df['Volume'].iloc[-5:-1].mean()  # 최근 5일 중 4일
    # 이전 10일 평균 거래량 (상승장 거래량)
    previous_volume = df['Volume'].iloc[-15:-5].mean()  # 6~15일 전
    
    volume_decreasing = recent_volume < previous_volume
    volume_ratio = (recent_volume / previous_volume) * 100 if previous_volume > 0 else 100
    
    # 종합 판단
    is_pullback = above_ma20 and near_ma20 and volume_decreasing
    
    details = {
        '현재가': f"{current_price:.2f}",
        '20일선': f"{ma20:.2f}",
        '20일선 대비 거리': f"{distance_from_ma20:.2f}%",
        '최근5일 평균거래량': f"{recent_volume:,.0f}",
        '이전10일 평균거래량': f"{previous_volume:,.0f}",
        '거래량 비율': f"{volume_ratio:.1f}%",
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
    
    return {
        'is_pullback': is_pullback,
        'reason': reason,
        'details': details
    }


def get_macro_indicators():
    try:
        # 기간을 1개월로 늘려 데이터 확보 안정성 강화
        tnx_data = yf.Ticker("^TNX").history(period='1mo')
        krw_data = yf.Ticker("KRW=X").history(period='1mo')
        
        res = {}
        
        # 금리 처리
        if len(tnx_data) >= 2:
            curr, prev = tnx_data['Close'].iloc[-1], tnx_data['Close'].iloc[-2]
            res['미국10년물금리'] = {'현재': f"{curr:.2f}%", '변화': f"{(curr-prev)/prev*100:+.2f}%"}
        else:
            res['미국10년물금리'] = {'현재': 'N/A', '변화': 'N/A'}
            
        # 환율 처리 (동일 로직)
        if len(krw_data) >= 2:
            curr, prev = krw_data['Close'].iloc[-1], krw_data['Close'].iloc[-2]
            res['원달러환율'] = {'현재': f"{curr:.2f}", '변화': f"{(curr-prev)/prev*100:+.2f}%"}
        else:
            res['원달러환율'] = {'현재': 'N/A', '변화': 'N/A'}
            
        return res
    except:
        return {'미국10년물금리': {'현재': 'N/A', '변화': 'N/A'}, '원달러환율': {'현재': 'N/A', '변화': 'N/A'}}


def create_candlestick_chart(df):
    """
    Plotly를 사용한 인터랙티브 캔들스틱 차트 생성
    
    Args:
        df: 기술적 지표가 포함된 데이터프레임
    
    Returns:
        plotly figure
    """
    # 서브플롯 생성 (차트 2개: 가격/거래량)
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=('주가 및 이동평균선', '거래량'),
        row_heights=[0.7, 0.3]
    )
    
    # 캔들스틱
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='주가',
            increasing_line_color='#FF6B6B',
            decreasing_line_color='#4ECDC4'
        ),
        row=1, col=1
    )
    
    # 이동평균선들
    ma_colors = {
        'MA5': '#FF6B6B',
        'MA20': '#4ECDC4',
        'MA60': '#FFD93D',
        'MA120': '#95E1D3'
    }
    
    for ma, color in ma_colors.items():
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[ma],
                name=ma,
                line=dict(color=color, width=2),
                opacity=0.7
            ),
            row=1, col=1
        )
    
    # 거래량
    colors = ['#FF6B6B' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#4ECDC4' 
              for i in range(len(df))]
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['Volume'],
            name='거래량',
            marker_color=colors,
            opacity=0.5
        ),
        row=2, col=1
    )
    
    # 레이아웃 설정
    fig.update_layout(
        title='주가 차트 분석',
        yaxis_title='주가',
        yaxis2_title='거래량',
        xaxis_rangeslider_visible=False,
        height=700,
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig


def generate_ai_analysis(ticker, financial_metrics, pullback_info, df, macro_indicators, api_key):
    """
    Google Gemini API를 사용하여 AI 종합 분석 리포트 생성
    
    Args:
        ticker: 종목 코드
        financial_metrics: 재무 지표
        pullback_info: 눌림목 분석 결과
        df: 기술적 지표가 포함된 데이터프레임
        macro_indicators: 거시 경제 지표
        api_key: Google AI Studio API 키
    
    Returns:
        str: AI 분석 리포트
    """
    # 최신 데이터
    latest = df.iloc[-1]
    
    # 기술적 지표 요약
    technical_summary = f"""
    [기술적 지표]
    - 현재가: {latest['Close']:.2f}
    - RSI(14): {latest['RSI']:.2f}
    - MACD: {latest['MACD']:.2f}
    - MACD Signal: {latest['MACD_Signal']:.2f}
    - 당일 거래대금: {latest['Trading_Value']:,.0f}
    - MA5: {latest['MA5']:.2f}
    - MA20: {latest['MA20']:.2f}
    - MA60: {latest['MA60']:.2f}
    - MA120: {latest['MA120']:.2f}
    """
    
    # 프롬프트 구성
    prompt = f"""
당신은 전문 금융 애널리스트입니다. 다음 정보를 바탕으로 '{ticker}' 종목에 대한 종합 투자 의견을 제시해주세요.

## 1. 재무 지표
{chr(10).join([f'- {k}: {v}' for k, v in financial_metrics.items()])}

## 2. 눌림목(Pullback) 분석
- 눌림목 여부: {'✓ 감지됨' if pullback_info['is_pullback'] else '✗ 미감지'}
- 분석: {pullback_info['reason']}
- 세부사항:
{chr(10).join([f'  - {k}: {v}' for k, v in pullback_info['details'].items()])}

## 3. 기술적 지표
{technical_summary}

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

전문적이지만 이해하기 쉽게 작성해주세요.
"""
    
    try:
        # Gemini API 설정
        genai.configure(api_key=api_key)
        
        # Gemini Pro 모델 사용 (무료, 안정적)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 응답 생성
        response = model.generate_content(prompt)
        
        return response.text
    except Exception as e:
        return f"AI 분석 생성 실패: {str(e)}\n\n[참고] Google AI Studio API 키를 확인해주세요."


# 메인 앱
def main():
    # 사이드바 설정
    st.sidebar.header("🔧 설정")
    
    # 시장 선택
    market = st.sidebar.selectbox(
        "시장 선택",
        ["US", "KR"],
        help="US: 미국 주식, KR: 한국 주식"
    )
    
    # 종목 코드 입력
    if market == "KR":
        ticker = st.sidebar.text_input(
            "종목 코드 입력",
            value="005930",
            help="예: 삼성전자 = 005930"
        )
    else:
        ticker = st.sidebar.text_input(
            "종목 코드 입력",
            value="AAPL",
            help="예: Apple = AAPL"
        )
    
    # API 키 입력 - secrets 파일 또는 기본값 사용
    default_api_key = st.secrets.get("GOOGLE_API_KEY", "AIzaSyCosexnKOcAanGf_pSx8ZzhOHi6_hFByV0")
    
    api_key = st.sidebar.text_input(
        "Google AI Studio API Key",
        value=default_api_key,
        type="password",
        help="Gemini API를 사용하기 위한 키 (무료)"
    )
    
    # 분석 실행 버튼
    analyze_button = st.sidebar.button("📊 분석 실행", type="primary", use_container_width=True)
    
    if analyze_button and ticker:
        with st.spinner('데이터를 가져오는 중...'):
            # 1. 주가 데이터 가져오기
            df = get_stock_data(ticker, market)
            
            if df is None or len(df) == 0:
                st.error("데이터를 가져올 수 없습니다. 종목 코드를 확인해주세요.")
                return
            
            # 2. 재무 지표 가져오기
            financial_metrics = get_financial_metrics(ticker, market)
            
            # 3. 기술적 지표 계산
            df = calculate_technical_indicators(df)
            
            # 4. 눌림목 분석
            pullback_info = detect_pullback(df)
            
            # 5. 거시 경제 지표
            macro_indicators = get_macro_indicators()
        
        # === UI 렌더링 ===
        
        # 상단: 재무 지표
        st.subheader("📊 주요 재무 지표")
        
        cols = st.columns(4)
        metrics_items = list(financial_metrics.items())
        
        for idx, (key, value) in enumerate(metrics_items[:4]):
            with cols[idx % 4]:
                st.metric(label=key, value=value)
        
        cols2 = st.columns(4)
        for idx, (key, value) in enumerate(metrics_items[4:]):
            with cols2[idx % 4]:
                st.metric(label=key, value=value)
        
        st.divider()
        
        # 중단: 차트 및 눌림목 분석
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📈 주가 차트")
            fig = create_candlestick_chart(df)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🎯 눌림목 분석")
            
            if pullback_info['is_pullback']:
                st.success(pullback_info['reason'])
            else:
                st.info(pullback_info['reason'])
            
            st.write("**세부 분석**")
            for key, value in pullback_info['details'].items():
                st.text(f"{key}: {value}")
            
            st.divider()
            
            st.subheader("🌍 거시 경제 지표")
            st.metric(
                "미국 10년물 금리",
                macro_indicators['미국10년물금리']['현재'],
                macro_indicators['미국10년물금리']['변화']
            )
            st.metric(
                "원/달러 환율",
                macro_indicators['원달러환율']['현재'],
                macro_indicators['원달러환율']['변화']
            )
        
        st.divider()
        
        # 하단: AI 분석 리포트
        st.subheader("🤖 AI 종합 투자 분석")
        
        if api_key:
            with st.spinner('AI 분석을 생성하는 중...'):
                analysis = generate_ai_analysis(
                    ticker,
                    financial_metrics,
                    pullback_info,
                    df,
                    macro_indicators,
                    api_key
                )
            
            st.markdown(analysis)
        else:
            st.warning("⚠️ Google AI Studio API 키를 입력하면 AI 분석을 확인할 수 있습니다.")
            st.info("""
            **AI 분석 기능 안내**
            
            왼쪽 사이드바에 Google AI Studio API 키를 입력하면 Gemini AI가 다음 항목을 종합 분석합니다:
            - 재무 지표 분석
            - 눌림목 패턴 해석
            - 기술적 지표 종합
            - 거시 경제 환경 영향
            - 투자 의견 (매수/매도/보유)
            - 목표가 및 손절가 제시
            
            **API 키 발급 방법 (무료)**:
            1. https://aistudio.google.com/app/apikey 접속
            2. Google 계정으로 로그인
            3. 'Create API Key' 클릭
            4. 생성된 키를 복사하여 왼쪽에 입력
            
            ✅ 무료로 사용 가능합니다!
            """)
    
    else:
        # 초기 화면
        st.info("👈 왼쪽 사이드바에서 종목을 선택하고 '분석 실행' 버튼을 클릭하세요.")
        
        st.markdown("""
        ### 📌 주요 기능
        
        1. **재무 지표 분석**: PER, PBR, ROE 등 핵심 재무 수치 제공
        2. **눌림목 탐색**: 20일 이평선 근처에서 에너지 응축 패턴 감지
        3. **기술적 지표**: 이동평균선, RSI, MACD 등 차트 분석
        4. **거시 경제 연동**: 미국 금리와 환율 동향 파악
        5. **AI 투자 의견**: Google Gemini AI의 종합 분석 및 투자 전략 제시
        
        ### 🎯 눌림목(Pullback) 판별 기준
        
        - ✅ 주가가 20일 이동평균선 **상단**에 위치
        - ✅ 20일선과의 거리가 **3% 이내**로 근접
        - ✅ 최근 거래량이 **감소** (에너지 응축 신호)
        
        → 위 3가지 조건을 모두 충족하면 눌림목으로 판단합니다.
        
        ### 🆓 Google AI Studio API 키 발급
        
        1. https://aistudio.google.com/app/apikey 접속
        2. 'Create API Key' 버튼 클릭
        3. 생성된 키를 복사하여 사이드바에 입력
        
        **완전 무료**로 사용 가능합니다!
        """)


if __name__ == "__main__":
    main()
