import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
from ta.momentum import RSIIndicator
from ta.trend import MACD

st.set_page_config(page_title="AI 주식 통합 진단", layout="wide")
st.title("📈 AI 주식 통합 진단")

# -----------------------------
# 🇰🇷 한국 종목 (섹터)
# -----------------------------
KR_TICKER_MAP = {

# ======================
# 반도체 / IT
# ======================
"삼성전자": "005930",
"SK하이닉스": "000660",
"삼성전자우": "005935",
"DB하이텍": "000990",
"한미반도체": "042700",
"리노공업": "058470",
"원익IPS": "240810",
"주성엔지니어링": "036930",
"테스": "095610",
"ISC": "095340",

# ======================
# 2차전지 / 소재
# ======================
"LG에너지솔루션": "373220",
"삼성SDI": "006400",
"에코프로": "086520",
"에코프로비엠": "247540",
"포스코퓨처엠": "003670",
"엘앤에프": "066970",
"SK이노베이션": "096770",
"금양": "001570",
"코스모신소재": "005070",
"천보": "278280",

# ======================
# 자동차
# ======================
"현대차": "005380",
"기아": "000270",
"현대모비스": "012330",
"현대위아": "011210",
"HL만도": "204320",

# ======================
# 바이오 / 제약
# ======================
"삼성바이오로직스": "207940",
"셀트리온": "068270",
"셀트리온헬스케어": "091990",
"유한양행": "000100",
"한미약품": "128940",
"녹십자": "006280",
"종근당": "185750",
"대웅제약": "069620",
"메디톡스": "086900",
"휴젤": "145020",

# ======================
# 인터넷 / 플랫폼
# ======================
"네이버": "035420",
"카카오": "035720",
"카카오뱅크": "323410",
"카카오페이": "377300",
"NHN": "181710",

# ======================
# 게임
# ======================
"엔씨소프트": "036570",
"크래프톤": "259960",
"넷마블": "251270",
"펄어비스": "263750",
"위메이드": "112040",

# ======================
# 금융
# ======================
"KB금융": "105560",
"신한지주": "055550",
"하나금융지주": "086790",
"우리금융지주": "316140",
"삼성생명": "032830",
"삼성화재": "000810",

# ======================
# 소비재
# ======================
"아모레퍼시픽": "090430",
"LG생활건강": "051900",
"호텔신라": "008770",
"CJ제일제당": "097950",
"농심": "004370",
"오리온": "271560",

# ======================
# 유통 / 플랫폼
# ======================
"이마트": "139480",
"롯데쇼핑": "023530",
"BGF리테일": "282330",
"GS리테일": "007070",

# ======================
# 건설 / 인프라
# ======================
"현대건설": "000720",
"삼성물산": "028260",
"DL이앤씨": "375500",
"GS건설": "006360",
"대우건설": "047040",

# ======================
# 철강 / 소재
# ======================
"POSCO홀딩스": "005490",
"현대제철": "004020",
"동국제강": "001230",
"KG스틸": "016380",

# ======================
# 통신
# ======================
"SK텔레콤": "017670",
"KT": "030200",
"LG유플러스": "032640",

# ======================
# 에너지
# ======================
"한국전력": "015760",
"한국가스공사": "036460",
"S-Oil": "010950",

# ======================
# 항공 / 여행
# ======================
"대한항공": "003490",
"아시아나항공": "020560",
"하나투어": "039130",
"모두투어": "080160",

# ======================
# 엔터 / 미디어
# ======================
"하이브": "352820",
"JYP Ent.": "035900",
"SM": "041510",
"YG엔터테인먼트": "122870",

# ======================
# 기타 성장주
# ======================
"두산에너빌리티": "034020",
"한화에어로스페이스": "012450",
"LIG넥스원": "079550",
"현대로템": "064350",

# ======================
# 전력기기 / 전력 인프라
# ======================
"LS": "006260",
"LS ELECTRIC": "010120",
"효성중공업": "298040",
"HD현대일렉트릭": "267260",
"일진전기": "103590",
"대한전선": "001440",
"가온전선": "000500",
"제룡전기": "033100",
"대원전선": "006340",
"비츠로테크": "042370",

# ======================
# 바이오 (확장)
# ======================
"알테오젠": "196170",
"HLB": "028300",
"HLB생명과학": "067630",
"에이비엘바이오": "298380",
"레고켐바이오": "141080",
"지아이이노베이션": "358570",
"유바이오로직스": "206650",
"보로노이": "310210",
"큐리언트": "115180",
"차바이오텍": "085660",

# ======================
# 반도체 소부장
# ======================
"한솔케미칼": "014680",
"동진쎄미켐": "005290",
"SK머티리얼즈": "036490",
"원익머트리얼즈": "104830",
"솔브레인": "357780",
"피에스케이": "319660",
"유진테크": "084370",
"주성엔지니어링": "036930",
"테스나": "131970",
"네패스": "033640"    
}

# -----------------------------
# 🇺🇸 미국 종목 (섹터)
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
# 데이터
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
# 지표
# -----------------------------
def calc_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    df['MA120'] = df['Close'].rolling(120).mean()

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

    cond1 = latest['Close'] > latest['MA60']
    cond2 = abs((latest['Close'] - latest['MA20']) / latest['MA20']) < 0.03

    vol_recent = df['Volume'].iloc[-5:].mean()
    vol_prev = df['Volume'].iloc[-20:-5].mean()

    return cond1 and cond2 and vol_recent < vol_prev

# -----------------------------
# 돌파
# -----------------------------
def detect_breakout(df):
    latest = df.iloc[-1]
    high_20 = df['High'].iloc[-20:-1].max()

    vol_recent = df['Volume'].iloc[-3:].mean()
    vol_prev = df['Volume'].iloc[-20:-3].mean()

    return (latest['Close'] > high_20) and (vol_recent > vol_prev * 1.5)

# -----------------------------
# 거래량 급증
# -----------------------------
def detect_volume_spike(df):
    return df['Volume'].iloc[-1] > df['Volume'].iloc[-20:-1].mean() * 2

# -----------------------------
# 분석
# -----------------------------
def analyze(df):

    latest = df.iloc[-1]

    score = 0
    reasons = []

    close = latest['Close']
    ma20 = latest['MA20']
    ma60 = latest['MA60']
    ma120 = latest['MA120']

    # 추세
    if close > ma20 > ma60 > ma120:
        score += 3
        reasons.append("정배열")
    elif close < ma20 < ma60 < ma120:
        score -= 3
        reasons.append("역배열")

    # RSI
    if latest['RSI'] < 30:
        score += 2
        reasons.append("과매도")
    elif latest['RSI'] > 70:
        score -= 2
        reasons.append("과매수")

    # MACD
    if latest['MACD'] > latest['MACD_Signal']:
        score += 1
        reasons.append("MACD 상승")
    else:
        score -= 1
        reasons.append("MACD 하락")

    # 실전 신호
    pullback = detect_pullback(df)
    breakout = detect_breakout(df)
    volume_spike = detect_volume_spike(df)

    if pullback:
        score += 2
        reasons.append("눌림목")

    if breakout:
        score += 3
        reasons.append("돌파")

    if volume_spike:
        score += 1
        reasons.append("거래량 급증")

    # 판단
    if score >= 5:
        opinion = "🟢 강력 매수"
    elif score >= 3:
        opinion = "🟢 매수"
    elif score >= 1:
        opinion = "🟡 관망"
    else:
        opinion = "🔴 매도"

    return opinion, reasons, latest, pullback, breakout, volume_spike

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
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name="MA60"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA120'], name="MA120"), row=1, col=1)

    fig.add_trace(go.Bar(x=df.index, y=df['Volume']), row=2, col=1)

    return fig

# -----------------------------
# UI
# -----------------------------
market = st.sidebar.selectbox("시장", ["KR", "US"])

if market == "KR":
    stock_dict = KR_TICKER_MAP
else:
    stock_dict = US_TICKER_MAP

search = st.sidebar.text_input("종목 검색")

filtered = [k for k in stock_dict if search in k] if search else list(stock_dict.keys())

selected = st.sidebar.selectbox("종목 선택", filtered)

ticker = stock_dict[selected]

# -----------------------------
# 실행
# -----------------------------
if st.sidebar.button("분석 실행"):

    st.write("DEBUG:", ticker, market)

    df = get_stock_data(ticker, market)

    if df is None or df.empty:
        st.error("❌ 데이터 불러오기 실패 (티커 확인 필요)")
        st.stop()

    df = calc_indicators(df)

        opinion, reasons, latest, pullback, breakout, volume_spike = analyze(df)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("투자 의견", opinion)
        col2.metric("현재가", f"{latest['Close']:.2f}")
        col3.metric("RSI", f"{latest['RSI']:.1f}")
        col4.metric("추세", "상승" if latest['Close'] > latest['MA60'] else "하락")

        st.write("📍 판단 근거:", " / ".join(reasons))

        if pullback:
            st.success("📉 눌림목 구간")
        if breakout:
            st.success("🚀 돌파 발생")
        if volume_spike:
            st.info("📊 거래량 급증")

        st.plotly_chart(create_chart(df), use_container_width=True)
