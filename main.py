import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from ta.momentum import RSIIndicator
from ta.trend import MACD

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="AI 주식 통합 진단", layout="wide")
st.title("📈 AI 주식 통합 진단")

# -----------------------------
# 한국 종목 리스트
# -----------------------------
@st.cache_data
def load_krx_list():
    return fdr.StockListing('KRX')

def search_kr_ticker(name):
    df = load_krx_list()
    return df[df['Name'].str.contains(name)][['Name', 'Code']].head(10)

# -----------------------------
# 미국 인기 종목 (안정형)
# -----------------------------
US_TICKER_MAP = {
    "애플": "AAPL",
    "마이크로소프트": "MSFT",
    "엔비디아": "NVDA",
    "아마존": "AMZN",
    "테슬라": "TSLA",
    "알파벳A": "GOOGL",
    "알파벳C": "GOOG",
    "메타": "META",
    "넷플릭스": "NFLX",
    "브로드컴": "AVGO",
    "AMD": "AMD",
    "인텔": "INTC",
    "퀄컴": "QCOM",
    "마이크론": "MU",
    "TSMC": "TSM",
    "ASML": "ASML",
    "어도비": "ADBE",
    "세일즈포스": "CRM",
    "오라클": "ORCL",
    "IBM": "IBM",

    # ETF
    "S&P500": "SPY",
    "나스닥100": "QQQ",
    "다우존스": "DIA",
    "러셀2000": "IWM",
    "배당ETF": "VYM",
    "고배당": "SCHD",
    "성장ETF": "VUG",
    "가치ETF": "VTV",
    "전세계": "VT",
    "신흥국": "VWO",

    # 레버리지/인버스
    "나스닥레버리지3배": "TQQQ",
    "나스닥인버스3배": "SQQQ",
    "S&P레버리지3배": "UPRO",
    "S&P인버스3배": "SPXU",
    "반도체3배": "SOXL",
    "반도체인버스3배": "SOXS",

    # 금융/소비재
    "JP모건": "JPM",
    "뱅크오브아메리카": "BAC",
    "골드만삭스": "GS",
    "비자": "V",
    "마스터카드": "MA",
    "코카콜라": "KO",
    "펩시": "PEP",
    "월마트": "WMT",
    "코스트코": "COST",
    "맥도날드": "MCD",
    "스타벅스": "SBUX",
    "나이키": "NKE",

    # 헬스케어
    "존슨앤존슨": "JNJ",
    "화이자": "PFE",
    "머크": "MRK",
    "애브비": "ABBV",
    "일라이릴리": "LLY",
    "모더나": "MRNA",

    # 산업/에너지
    "엑슨모빌": "XOM",
    "셰브론": "CVX",
    "록히드마틴": "LMT",
    "보잉": "BA",
    "캐터필러": "CAT",
    "GE": "GE",

    # 전기차/미래
    "리비안": "RIVN",
    "루시드": "LCID",
    "니오": "NIO",
    "샤오펑": "XPEV",

    # 클라우드/AI
    "스노우플레이크": "SNOW",
    "팔란티어": "PLTR",
    "유니티": "U",
    "로블록스": "RBLX",

    # 반도체 ETF
    "반도체ETF": "SOXX",
    "반도체ETF2": "SMH",

    # ARK ETF
    "ARK혁신": "ARKK",
    "ARK유전자": "ARKG",
    "ARK핀테크": "ARKF",

    # 기타 인기
    "우버": "UBER",
    "에어비앤비": "ABNB",
    "디즈니": "DIS",
    "페이팔": "PYPL",
    "쇼피파이": "SHOP",
    "트위터": "TWTR",  # 참고: 현재 X (비상장 상태 반영 필요)
    "줌": "ZM",

    # 추가 분산
    "3M": "MMM",
    "허니웰": "HON",
    "텍사스인스트루먼트": "TXN",
    "AMD ETF": "XSD",

    # 채권
    "미국채20년": "TLT",
    "미국채7-10년": "IEF",
    "단기채": "SHY",

    # 금/원자재
    "금ETF": "GLD",
    "은ETF": "SLV",
    "원유ETF": "USO",

    # 리츠
    "리얼티인컴": "O",
    "아메리칸타워": "AMT",
    "프로로지스": "PLD",

    # 추가 인기 종목 채우기
    "도어대시": "DASH",
    "크라우드스트라이크": "CRWD",
    "서비스나우": "NOW",
    "줌인포": "ZI",
    "데이터독": "DDOG",
    "허브스팟": "HUBS",
    "워크데이": "WDAY"
}

# -----------------------------
# 데이터 불러오기
# -----------------------------
def get_stock_data(ticker, market):
    try:
        if market == "KR":
            end = datetime.now()
            start = end - timedelta(days=180)
            df = fdr.DataReader(ticker, start, end)
        else:
            df = yf.Ticker(ticker).history(period="6mo")

        return df
    except:
        return None

# -----------------------------
# 환율 변환
# -----------------------------
def convert_to_krw(df, market):
    try:
        if market == "US":
            rate = yf.Ticker("KRW=X").history(period="1mo")['Close'].iloc[-1]
            for col in ['Open','High','Low','Close']:
                df[col] *= rate
        return df
    except:
        return df

# -----------------------------
# 기술적 지표
# -----------------------------
def calc_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()

    df['RSI'] = RSIIndicator(df['Close']).rsi()

    macd = MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()

    return df

# -----------------------------
# 눌림목
# -----------------------------
def detect_pullback(df):
    latest = df.iloc[-1]

    cond1 = latest['Close'] > latest['MA20']
    cond2 = abs((latest['Close'] - latest['MA20']) / latest['MA20']) < 0.03

    vol_recent = df['Volume'].iloc[-5:].mean()
    vol_prev = df['Volume'].iloc[-20:-5].mean()

    return cond1 and cond2 and (vol_recent < vol_prev)

# -----------------------------
# 시장 흐름
# -----------------------------
def get_market_trend(market):
    try:
        index = "^GSPC" if market == "US" else "KS11"
        df = yf.Ticker(index).history(period="3mo")

        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        latest = df['Close'].iloc[-1]

        return "상승" if latest > ma20 else "하락"
    except:
        return "N/A"

# -----------------------------
# 모멘텀
# -----------------------------
def get_momentum(df):
    latest = df.iloc[-1]

    ret20 = (latest['Close'] / df['Close'].iloc[-20] - 1) * 100

    vol_recent = df['Volume'].iloc[-5:].mean()
    vol_prev = df['Volume'].iloc[-20:-5].mean()

    return ret20, vol_recent > vol_prev

# -----------------------------
# 분석 엔진
# -----------------------------
def generate_report(df, pullback, market):

    latest = df.iloc[-1]

    close = latest['Close']
    ma20 = latest['MA20']
    ma60 = latest['MA60']
    rsi = latest['RSI']
    macd = latest['MACD']
    macd_signal = latest['MACD_Signal']

    score = 0
    reasons = []

    if close > ma20 > ma60:
        trend = "상승"
        score += 2
        reasons.append("정배열")
    elif close < ma20:
        trend = "하락"
        score -= 2
        reasons.append("MA20 하회")
    else:
        trend = "횡보"

    if rsi < 30:
        score += 2
        reasons.append("과매도")
    elif rsi > 70:
        score -= 2
        reasons.append("과매수")

    if macd > macd_signal:
        score += 1
        reasons.append("MACD 상승")
    else:
        score -= 1
        reasons.append("MACD 하락")

    if pullback:
        score += 2
        reasons.append("눌림목")

    if score >= 4:
        opinion = "🟢 매수"
    elif score >= 1:
        opinion = "🟡 관망"
    else:
        opinion = "🔴 매도"

    buy_price = ma20 if pullback else close * 0.97
    stop_loss = min(ma60, buy_price * 0.95)

    market_trend = get_market_trend(market)
    ret20, vol_up = get_momentum(df)

    report = f"""
### 📊 종합 분석

- 시장: {market_trend}
- 20일 수익률: {ret20:.2f}%
- 거래량: {"증가" if vol_up else "감소"}

💰 현재가: {close:,.0f} 원  
📥 매수가: {buy_price:,.0f} 원  
🛑 손절가: {stop_loss:,.0f} 원  

📈 추세: {trend} / RSI: {rsi:.1f}  
📊 MACD: {"상승" if macd > macd_signal else "하락"}

📍 근거: {" / ".join(reasons)}

👉 최종 의견: **{opinion}**
"""
    return opinion, report, close, buy_price, stop_loss

# -----------------------------
# 차트
# -----------------------------
def create_chart(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name="MA20"), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume']), row=2, col=1)

    return fig

# -----------------------------
# MAIN
# -----------------------------
def main():

    market = st.sidebar.selectbox("시장", ["US", "KR"])

    ticker = None  # 🔥 핵심 (에러 방지)

    # 한국
    if market == "KR":
        name = st.sidebar.text_input("종목명 검색 (예: 삼성전자)")
        if name:
            results = search_kr_ticker(name)
            if not results.empty:
                selected = st.sidebar.selectbox(
                    "종목 선택",
                    results.apply(lambda x: f"{x['Name']} ({x['Code']})", axis=1)
                )
                ticker = selected.split("(")[-1].replace(")", "")

    # 미국
    else:
        selected = st.sidebar.selectbox("미국 인기 종목", list(US_TICKER_MAP.keys()))
        ticker = US_TICKER_MAP[selected]

    # 직접 입력 (override)
    manual = st.sidebar.text_input("티커 직접 입력 (선택)")
    if manual:
        ticker = manual

    # 실행
    if st.sidebar.button("분석 실행"):

        if not ticker:
            st.error("종목을 선택하거나 입력하세요")
            return

        df = get_stock_data(ticker, market)

        if df is None or df.empty:
            st.error("데이터 불러오기 실패 (티커 확인)")
            return

        df = convert_to_krw(df, market)
        df = calc_indicators(df)

        pullback = detect_pullback(df)

        opinion, report, price, buy, stop = generate_report(df, pullback, market)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("투자 의견", opinion)
        col2.metric("현재가", f"{price:,.0f} 원")
        col3.metric("매수", f"{buy:,.0f} 원")
        col4.metric("손절", f"{stop:,.0f} 원")

        st.markdown(report)
        st.plotly_chart(create_chart(df), use_container_width=True)

# 실행
if __name__ == "__main__":
    main()
