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
"테스": "095610",
"ISC": "095340",
"테크윙": "089030",
"에스티아이": "039440",
"이수페타시스": "007660",
"HPSP": "403870",
"하나마이크론": "067310",
"주성엔지니어링": "036930",
"고영": "098460",
"피에스케이": "319660",
"GST": "083450",

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
"신한지주": "055550",
"하나금융지주": "086790",
"우리금융지주": "316140",
"삼성생명": "032830",
"삼성화재": "000810",
"미래에셋증권": "006800",
"NH투자증권": "005940",
"한국금융지주": "071050",
"키움증권": "039490",
"삼성증권": "016360",
"KB증권": "105560", 
"메리츠금융지주": "138040",
"유안타증권": "003470",
"대신증권": "003540",
"한화투자증권": "003530",

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
"한전기술": "052690",

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
"산일전기": "062040",
"두산퓨얼셀": "336260",

# ======================
# 바이오 (확장)
# ======================
"알테오젠": "196170",
"HLB": "028300",
"HLB생명과학": "067630",
"에이비엘바이오": "298380",
"리가켐바이오": "141080",
"지아이이노베이션": "358570",
"유바이오로직스": "206650",
"보로노이": "310210",
"큐리언트": "115180",
"차바이오텍": "085660",
"디앤디파마텍": "347850",
"SK바이오팜": "326030",
"동국제약": "086450",
"인투셀": "287840",

# ======================
# 반도체 소부장
# ======================
"한솔케미칼": "014680",
"동진쎄미켐": "005290",
"SK머티리얼즈": "036490",
"원익머트리얼즈": "104830",
"솔브레인": "357780",
"유진테크": "084370",
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
# 데이터 가져오기
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
# 시장 추세
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
    if len(df) < 20:
        return 0, "확인불가"
    latest = df.iloc[-1]
    ret20 = (latest['Close'] / df['Close'].iloc[-20] - 1) * 100
    vol_recent = df['Volume'].iloc[-5:].mean()
    vol_prev = df['Volume'].iloc[-20:-5].mean()
    volume = "증가" if vol_recent > vol_prev else "감소"
    return ret20, volume

# -----------------------------
# 수급 분석 (한국만)
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
# 기술적 지표 계산
# -----------------------------
def calc_indicators(df):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    df['MA120'] = df['Close'].rolling(120).mean()
    df['RSI'] = RSIIndicator(df['Close']).rsi()
    macd = MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    atr = AverageTrueRange(df['High'], df['Low'], df['Close'])
    df['ATR'] = atr.average_true_range()
    return df.dropna()  # NaN 제거 (중요)

# -----------------------------
# 패턴 감지 함수들 (기존 + 개선)
# -----------------------------
def detect_pullback(df):
    if len(df) < 5: return False
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    cond1 = latest['Close'] > latest['MA60']
    cond2 = latest['MA20'] > latest['MA60']
    cond3 = prev['Close'] > latest['Close']
    cond4 = abs((latest['Close'] - latest['MA20']) / latest['MA20']) < 0.03
    cond5 = latest['Volume'] < df['Volume'].iloc[-20:-1].mean()
    return cond1 and cond2 and cond3 and cond4 and cond5

def pattern_pullback_reversal(df):
    if len(df) < 5: return False
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    cond1 = latest['Close'] > latest['MA60']
    cond2 = latest['MA20'] > latest['MA60']
    cond3 = prev['Close'] > latest['Close']
    cond4 = latest['Close'] > latest['MA20'] * 0.97
    cond5 = latest['Volume'] > df['Volume'].iloc[-5:].mean()
    return cond1 and cond2 and cond3 and cond4 and cond5

def detect_breakout(df):
    if len(df) < 20: return False
    latest = df.iloc[-1]
    high = df['High'].iloc[-20:-1].max()
    avg_vol = df['Volume'].iloc[-20:-1].mean()
    cond1 = latest['Close'] > high
    cond2 = latest['Volume'] > avg_vol * 1.5
    cond3 = latest['Close'] > latest['Open']
    return cond1 and cond2 and cond3

def pattern_trend_reversal(df):
    if len(df) < 5: return False
    latest = df.iloc[-1]
    cond1 = latest['MA20'] > latest['MA60']
    cond2 = df['MA20'].iloc[-2] < df['MA60'].iloc[-2]
    cond3 = latest['RSI'] > 50
    return cond1 and cond2 and cond3

def pattern_volume_surge(df):
    if len(df) < 20: return False
    latest = df.iloc[-1]
    avg_vol = df['Volume'].iloc[-20:-1].mean()
    cond1 = latest['Volume'] > avg_vol * 2
    cond2 = latest['Close'] > latest['Open']
    cond3 = (latest['Close'] - latest['Open']) / latest['Open'] > 0.03
    return cond1 and cond2 and cond3

def pattern_trend_continuation(df):
    if len(df) < 5: return False
    latest = df.iloc[-1]
    cond1 = latest['Close'] > latest['MA20'] > latest['MA60']
    cond2 = 45 < latest['RSI'] < 65
    cond3 = abs(latest['Close'] - latest['MA20']) / latest['MA20'] < 0.02
    return cond1 and cond2 and cond3

# -----------------------------
# 모든 패턴 종합 감지 (★ 핵심 추가)
# -----------------------------
def detect_all_patterns(df):
    patterns = []
    if detect_pullback(df) or pattern_pullback_reversal(df):
        patterns.append("📉 눌림목 반등")
    if detect_breakout(df):
        patterns.append("🚀 박스 돌파")
    if pattern_trend_reversal(df):
        patterns.append("🎯 추세 전환")
    if pattern_volume_surge(df):
        patterns.append("🔥 거래량 폭발")
    if pattern_trend_continuation(df):
        patterns.append("📈 추세 지속")
    return patterns

# -----------------------------
# 기본 분석 (점수 + 이유)
# -----------------------------
def analyze(df):
    if len(df) < 20:
        return "데이터 부족", [], df.iloc[-1], 0
    
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

    if detect_pullback(df) or pattern_pullback_reversal(df):
        score += 2
        reasons.append("눌림목")
    if detect_breakout(df):
        score += 3
        reasons.append("돌파")
    if pattern_volume_surge(df):
        score += 2
        reasons.append("거래량 급증")

    if score >= 6:
        opinion = "🟢 강력 매수"
    elif score >= 3:
        opinion = "🟢 매수"
    elif score >= 1:
        opinion = "🟡 관망"
    else:
        opinion = "🔴 매도"

    return opinion, reasons, latest, score

# -----------------------------
# 상세 판단 근거 (★ 가장 많이 개선된 부분)
# -----------------------------
def build_detailed_reasons(df, reasons, patterns, market, supply_text):
    latest = df.iloc[-1]
    explanations = []

    # 1. 추세
    if latest['Close'] > latest.get('MA20', 0) > latest.get('MA60', 0) > latest.get('MA120', 0):
        explanations.append("이동평균선이 정배열(MA20 > MA60 > MA120) 상태로 **중장기 상승 추세**가 강하게 유지되고 있습니다.")

    # 2. RSI
    rsi = latest['RSI']
    if rsi < 30:
        explanations.append(f"RSI {rsi:.1f} → **과매도 구간** (강한 반등 가능성)")
    elif rsi > 70:
        explanations.append(f"RSI {rsi:.1f} → **과매수 구간** (단기 조정 위험)")
    else:
        explanations.append(f"RSI {rsi:.1f} → 중립 구간")

    # 3. MACD
    if latest['MACD'] > latest['MACD_Signal']:
        explanations.append("MACD가 시그널선을 상향 돌파 → **모멘텀 강화** 중")
    else:
        explanations.append("MACD가 약세를 보이고 있습니다.")

    # 4. 거래량
    vol_recent = df['Volume'].iloc[-5:].mean()
    vol_prev = df['Volume'].iloc[-20:-5].mean() if len(df) > 20 else vol_recent
    if vol_recent > vol_prev * 1.2:
        explanations.append("최근 거래량이 증가 → **수급 유입** 신호")
    else:
        explanations.append("거래량이 다소 정체되거나 감소 중")

    # 5. 패턴 기반 설명
    for p in patterns:
        if "눌림목" in p:
            explanations.append("상승 추세 중 **단기 눌림목**이 발생했습니다. 저점 매수 기회로 판단됩니다.")
        elif "박스 돌파" in p:
            explanations.append("**박스권 상단 돌파**가 확인되었습니다. 강한 상승 동력이 생길 가능성이 높습니다.")
        elif "추세 전환" in p:
            explanations.append("**추세 전환 신호**가 포착되었습니다. 상승 전환 초입 단계로 보입니다.")
        elif "거래량 폭발" in p:
            explanations.append("**거래량 급증**이 동반되고 있습니다. 세력 진입 또는 수급 폭발 신호입니다.")
        elif "추세 지속" in p:
            explanations.append("추세가 안정적으로 유지되고 있어 **추가 상승 여력**이 있습니다.")

    # 6. 시장 환경
    market_trend = get_market_trend(market)
    if market_trend == "상승":
        explanations.append("전반적인 시장이 상승 추세 → 종목 상승 확률이 높아지는 환경입니다.")
    else:
        explanations.append("시장 전체가 약세 또는 조정 국면 → 변동성에 유의해야 합니다.")

    # 7. 수급
    if supply_text == "강한 매수":
        explanations.append("기관·외국인 **강한 순매수**가 확인되어 상승 지속 가능성이 높습니다.")
    elif supply_text == "순매수":
        explanations.append("수급이 순매수로 유입되는 중입니다.")
    elif supply_text in ["매도", "확인불가"]:
        explanations.append("수급이 매도 우위 또는 확인이 어려운 상황입니다.")

    return explanations

# -----------------------------
# 확률 계산
# -----------------------------
def calculate_probability(df, market, score, ticker):
    tech = min(score * 10, 50)
    market_trend = get_market_trend(market)
    market_score = 25 if market_trend == "상승" else 10
    ret20, vol = get_momentum(df)
    momentum = 15 if ret20 > 8 else 10 if ret20 > 3 else 5
    if vol == "증가":
        momentum += 5
    supply_text, s = get_supply_trend(ticker, market)
    supply = (s + 1) * 8
    total = tech + market_score + momentum + supply
    return min(int(total), 100), supply_text

# -----------------------------
# 나머지 함수들 (기존 그대로 유지)
# -----------------------------
def evaluate_timing(df, prob):
    patterns = detect_all_patterns(df)
    if "🚀 박스 돌파" in patterns and "🔥 거래량 폭발" in patterns:
        return "🚀🔥 초강력 돌파 매수"
    if "📉 눌림목 반등" in patterns:
        return "📉 최적 눌림목 매수 기회"
    if "🚀 박스 돌파" in patterns:
        return "🚀 강한 돌파 매수"
    if "🎯 추세 전환" in patterns:
        return "🎯 추세 전환 매수"
    if prob >= 70:
        return "⏳ 좋은 종목, 대기 후 매수"
    return "🤔 관망"

def analyze_risk(df, market, supply_text):
    latest = df.iloc[-1]
    risks = []
    if latest['RSI'] > 70:
        risks.append("RSI 과매수로 단기 조정 가능성")
    if get_market_trend(market) == "하락":
        risks.append("시장 전체 약세로 상승 제한 가능")
    if supply_text in ["매도", "확인불가"]:
        risks.append("수급이 불리하거나 확인 어려움")
    if latest['Close'] < latest.get('MA60', 0):
        risks.append("중기 추세(MA60) 이탈 위험")
    return risks[:3]

def generate_report(df, market, opinion, reasons, supply_text, prob):
    latest = df.iloc[-1]
    ret20, volume = get_momentum(df)
    patterns = detect_all_patterns(df)
    detailed = build_detailed_reasons(df, reasons, patterns, market, supply_text)
    timing = evaluate_timing(df, prob)
    risks = analyze_risk(df, market, supply_text)

    report = f"""
## 📊 AI 종합 분석 리포트
### 🎯 매수 확률
**{prob}%**

### ⏰ 진입 타이밍
**{timing}**

### 🌍 시장 환경
- 시장 방향: **{get_market_trend(market)}**

### 🚀 모멘텀
- 20일 수익률: **{ret20:.2f}%**
- 거래량 흐름: **{volume}**

### 📈 기술적 분석
- 추세: **{"상승" if latest['Close'] > latest.get('MA60', 0) else "하락"}**
- RSI: **{latest['RSI']:.1f}**
- MACD: **{"상승" if latest['MACD'] > latest['MACD_Signal'] else "하락"}**

### 💰 수급 분석
- 상태: **{supply_text}**

### 📍 상세 판단 근거
"""
    for r in detailed:
        report += f"- {r}\n"

    report += "\n---\n### ⚠️ 주요 리스크\n"
    if risks:
        for r in risks:
            report += f"- {r}\n"
    else:
        report += "- 현재 특별한 리스크는 감지되지 않았습니다.\n"

    report += f"""
---
### ✅ 최종 결론
**{opinion}**
"""
    return report

def calc_trade_levels(df):
    latest = df.iloc[-1]
    price = latest['Close']
    atr = latest.get('ATR', price * 0.02)
    stop = price - atr * 1.5
    target = price + atr * 2.5
    return price, stop, target

def create_chart(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="캔들"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name="MA20", line=dict(color='orange')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name="MA60", line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="거래량"), row=2, col=1)
    fig.update_layout(height=700)
    return fig

# ======================
# UI
# ======================
market = st.sidebar.selectbox("시장 선택", ["KR", "US"])
stock_dict = KR_TICKER_MAP if market == "KR" else US_TICKER_MAP
selected = st.sidebar.selectbox("종목 선택", list(stock_dict.keys()))
ticker = stock_dict[selected]

if st.sidebar.button("📊 종목 분석", type="primary"):
    df = get_stock_data(ticker, market)
    if df is None or df.empty:
        st.error("데이터를 불러올 수 없습니다.")
        st.stop()

    df = calc_indicators(df)
    opinion, reasons, latest, score = analyze(df)
    prob, supply_text = calculate_probability(df, market, score, ticker)
    timing = evaluate_timing(df, prob)
    price, stop, target = calc_trade_levels(df)
    patterns = detect_all_patterns(df)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("종합 의견", opinion)
    col2.metric("매수 확률", f"{prob}%")
    col3.metric("현재가", f"{price:,.0f}" if market == "KR" else f"{price:.2f}")
    col4.metric("손절가", f"{stop:,.0f}" if market == "KR" else f"{stop:.2f}")
    col5.metric("목표가", f"{target:,.0f}" if market == "KR" else f"{target:.2f}")

    st.markdown("### 📍 감지된 패턴")
    st.write(", ".join(patterns) if patterns else "특별한 패턴 미감지")

    st.markdown(f"### ⏰ 추천 타이밍\n**{timing}**")

    st.plotly_chart(create_chart(df), use_container_width=True)

    st.markdown("---")
    st.markdown(generate_report(df, market, opinion, reasons, supply_text, prob))

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
