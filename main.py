import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange

st.set_page_config(page_title="AI 주식 통합 진단", layout="wide")
st.title("📈 AI 주식 통합 진단")

# -----------------------------
# 종목 리스트 (샘플)
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
@st.cache_data(ttl=600)
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
# 시장
# -----------------------------
def get_market_trend(market):
    try:
        index = "^KS11" if market == "KR" else "^GSPC"
        df = yf.Ticker(index).history(period="3mo")
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        latest = df['Close'].iloc[-1]
        return "상승" if latest > ma20 else "하락"
    except:
        return "중립"

# -----------------------------
# 모멘텀
# -----------------------------
def get_momentum(df):
    latest = df.iloc[-1]
    ret20 = (latest['Close'] / df['Close'].iloc[-20] - 1) * 100

    vol_recent = df['Volume'].iloc[-5:].mean()
    vol_prev = df['Volume'].iloc[-20:-5].mean()
    volume = "증가" if vol_recent > vol_prev else "감소"

    return ret20, volume

# -----------------------------
# 수급
# -----------------------------
def get_supply_trend(ticker, market):
    try:
        if market == "KR":
            df = fdr.DataReader(ticker)
            df = df.tail(20)

            foreign = df['Foreign'].sum() if 'Foreign' in df.columns else 0
            inst = df['Institution'].sum() if 'Institution' in df.columns else 0

            if foreign > 0 and inst > 0:
                return "강한 매수", 2
            elif foreign > 0 or inst > 0:
                return "순매수", 1
            else:
                return "매도", -1
        else:
            return "중립", 0
    except:
        return "확인불가", 0

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

    atr = AverageTrueRange(df['High'], df['Low'], df['Close'])
    df['ATR'] = atr.average_true_range()

    return df

# -----------------------------
# 신호
# -----------------------------
def detect_pullback(df):
    latest = df.iloc[-1]
    return (
        latest['Close'] > latest['MA60'] and
        abs((latest['Close'] - latest['MA20']) / latest['MA20']) < 0.03
    )

def detect_breakout(df):
    latest = df.iloc[-1]
    high = df['High'].iloc[-20:-1].max()
    return latest['Close'] > high

def detect_volume_spike(df):
    return df['Volume'].iloc[-1] > df['Volume'].iloc[-20:-1].mean() * 2

# -----------------------------
# 분석
# -----------------------------
def analyze(df):
    latest = df.iloc[-1]
    score = 0
    reasons = []

    if latest['Close'] > latest['MA20'] > latest['MA60'] > latest['MA120']:
        score += 3
        reasons.append("중장기 상승 추세")

    if latest['RSI'] < 30:
        score += 2
        reasons.append("과매도")
    elif latest['RSI'] > 70:
        score -= 2
        reasons.append("과매수")

    if latest['MACD'] > latest['MACD_Signal']:
        score += 1
        reasons.append("MACD 상승")

    if detect_pullback(df):
        score += 2
        reasons.append("눌림목")

    if detect_breakout(df):
        score += 3
        reasons.append("돌파")

    if detect_volume_spike(df):
        score += 1
        reasons.append("거래량 급증")

    if score >= 5:
        opinion = "🟢 강력 매수"
    elif score >= 3:
        opinion = "🟢 매수"
    elif score >= 1:
        opinion = "🟡 관망"
    else:
        opinion = "🔴 매도"

    return opinion, reasons, latest, score

# -----------------------------
# 판단근거
# -----------------------------
def build_detailed_reasons(df, reasons, market, supply_status):
    latest = df.iloc[-1]

    explanations = []

    # 1. 추세 해석
    if "중장기 상승 추세" in reasons:
        explanations.append("이동평균선이 MA20 > MA60 > MA120 순으로 정렬된 중장기 상승 추세로, 기관/외국인 매수 시 강한 추세 지속 가능성이 높습니다.")

    if "역배열" in reasons:
        explanations.append("이동평균선이 역배열 상태로 하락 추세가 지속되고 있으며, 단기 반등은 기술적 반등일 가능성이 큽니다.")

    # 2. RSI 해석
    if latest['RSI'] < 30:
        explanations.append(f"RSI {latest['RSI']:.1f}로 과매도 구간이며, 단기 반등 가능성이 존재합니다.")
    elif latest['RSI'] > 70:
        explanations.append(f"RSI {latest['RSI']:.1f}로 과매수 상태이며, 단기 조정 가능성에 유의해야 합니다.")
    else:
        explanations.append(f"RSI {latest['RSI']:.1f}로 중립 구간이며 방향성 결정 구간입니다.")

    # 3. MACD 해석
    if latest['MACD'] > latest['MACD_Signal']:
        explanations.append("MACD가 시그널선을 상향 돌파한 상태로 상승 모멘텀이 유입되고 있습니다.")
    else:
        explanations.append("MACD가 하락 상태로 모멘텀이 약화되고 있습니다.")

    # 4. 거래량 해석
    vol_recent = df['Volume'].iloc[-5:].mean()
    vol_prev = df['Volume'].iloc[-20:-5].mean()

    if vol_recent > vol_prev:
        explanations.append("최근 거래량이 증가하며 수급 유입 신호가 나타나고 있습니다.")
    else:
        explanations.append("거래량이 감소하며 관망세가 이어지고 있습니다.")

    # 5. 시장 환경
    market_trend = get_market_trend(market)

    if market_trend == "상승":
        explanations.append("현재 시장 전체가 상승 흐름으로 개별 종목 상승 확률이 우호적인 환경입니다.")
    else:
        explanations.append("시장 전체가 약세 흐름으로 종목 상승 시에도 변동성 리스크가 존재합니다.")

    # 6. 수급 해석
    if supply_status == "매수":
        explanations.append("외국인/기관 수급이 순매수로 전환되며 상승 추세 강화 가능성이 있습니다.")
    elif supply_status == "매도":
        explanations.append("외국인/기관 수급이 순매도 상태로 상승 시 저항 요인으로 작용할 수 있습니다.")
    else:
        explanations.append("수급 방향성이 뚜렷하지 않은 중립 상태입니다.")

    return explanations

# -----------------------------
# 리포트
# -----------------------------
def generate_report(df, market, opinion, reasons, supply_text, prob):
    latest = df.iloc[-1]

    ret20, volume = get_momentum(df)
    trend = "상승" if latest['Close'] > latest['MA60'] else "하락"

    detailed = build_detailed_reasons(df, reasons, market, supply_text)

    report = f"""
## 📊 AI 종합 분석 리포트

### 🎯 매수 확률
👉 **{prob}%**

---

### 🌍 시장 환경
- 시장 방향: {get_market_trend(market)}

---

### 🚀 모멘텀
- 20일 수익률: {ret20:.2f}%
- 거래량 흐름: {volume}

---

### 📈 기술적 분석
- 추세: {trend}
- RSI: {latest['RSI']:.1f}
- MACD: {"상승" if latest['MACD'] > latest['MACD_Signal'] else "하락"}

---

### 💰 수급 분석
- 상태: {supply_text}

---

### 📍 상세 판단 근거
"""
    for r in detailed:
        report += f"- {r}\n"

    report += f"""

---

### ✅ 최종 결론
👉 **{opinion}**
"""
    return report

# -----------------------------
# 확률 계산
# -----------------------------
def calculate_probability(df, market, score, ticker):

    tech = min(score * 10, 50)

    market_trend = get_market_trend(market)
    market_score = 25 if market_trend == "상승" else 10

    ret20, vol = get_momentum(df)
    momentum = 10 if ret20 > 5 else 5 if ret20 > 0 else 0
    if vol == "증가":
        momentum += 5

    supply_text, s = get_supply_trend(ticker, market)
    supply = (s + 1) * 5

    total = tech + market_score + momentum + supply

    return min(int(total), 100), supply_text

# -----------------------------
# ATR 가격
# -----------------------------
def calc_trade_levels(df):
    latest = df.iloc[-1]
    price = latest['Close']
    atr = latest['ATR']

    stop = price - atr * 1.5
    target = price + atr * 2.5

    return price, stop, target

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

    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name="MA20"))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name="MA60"))

    fig.add_trace(go.Bar(x=df.index, y=df['Volume']), row=2, col=1)

    return fig

# -----------------------------
# UI
# -----------------------------
market = st.sidebar.selectbox("시장", ["KR", "US"])
stock_dict = KR_TICKER_MAP if market == "KR" else US_TICKER_MAP

selected = st.sidebar.selectbox("종목 선택", list(stock_dict.keys()))
ticker = stock_dict[selected]

# -----------------------------
# 단일 분석
# -----------------------------
if st.sidebar.button("📊 종목 분석"):

    df = get_stock_data(ticker, market)

    if df is None or df.empty:
        st.error("데이터 없음")
        st.stop()

    df = calc_indicators(df)

    opinion, reasons, latest, score = analyze(df)
    prob, supply_text = calculate_probability(df, market, score, ticker)
    price, stop, target = calc_trade_levels(df)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("의견", opinion)
    col2.metric("확률", f"{prob}%")
    col3.metric("현재가", f"{price:.2f}")
    col4.metric("손절가", f"{stop:.2f}")
    col5.metric("목표가", f"{target:.2f}")

    st.markdown(generate_report(df, market, opinion, reasons, supply_text, prob))

    st.plotly_chart(create_chart(df), use_container_width=True)

# -----------------------------
# 스캐너
# -----------------------------
if st.sidebar.button("🔥 매수 후보 스캔"):

    results = []

    for name, ticker in stock_dict.items():
        df = get_stock_data(ticker, market)
        if df is None or len(df) < 120:
            continue

        df = calc_indicators(df)

        try:
            opinion, reasons, latest, score = analyze(df)
            prob, _ = calculate_probability(df, market, score, ticker)

            if prob >= 60:
                price, stop, target = calc_trade_levels(df)

                results.append({
                    "종목": name,
                    "확률": prob,
                    "현재가": round(price, 2),
                    "손절가": round(stop, 2),
                    "목표가": round(target, 2),
                    "근거": ", ".join(reasons)
                })
        except:
            continue

    df_result = pd.DataFrame(results).sort_values(by="확률", ascending=False)

    if df_result.empty:
        st.warning("후보 없음")
    else:
        st.dataframe(df_result, use_container_width=True)
