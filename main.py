import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
import json, re, time, requests
from bs4 import BeautifulSoup

# -----------------------------
# 설정
# -----------------------------
st.set_page_config(page_title="AI 투자 분석", layout="wide")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# -----------------------------
# 스타일
# -----------------------------
st.markdown("""
<style>
.stApp { background-color: #F2F4F6; }
.card { background:white; padding:24px; border-radius:20px; margin-bottom:16px;}
.buy { color:#3182F6; font-weight:700;}
.hold { color:#FFBB00; font-weight:700;}
.sell { color:#F04452; font-weight:700;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# JSON 안정화
# -----------------------------
def safe_json_parse(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group(0))
    return None

# -----------------------------
# KRX 리스트
# -----------------------------
@st.cache_data(ttl=86400)
def get_krx_list():
    try:
        url = "https://kind.krx.co.kr/corplist.do?method=download&searchType=13"
        df = pd.read_html(url, header=0)[0]
        df = df[['회사명','종목코드']]
        df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
        return df
    except:
        return pd.DataFrame([
            ["삼성전자","005930"],
            ["SK하이닉스","000660"]
        ], columns=["회사명","종목코드"])

# -----------------------------
# 네이버 가격
# -----------------------------
def get_kr_price_naver(code):
    try:
        url = f"https://finance.naver.com/item/main.nhn?code={code}"
        headers = {"User-Agent":"Mozilla/5.0","Referer":"https://finance.naver.com/"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "lxml")

        tag = soup.select_one("p.no_today span.blind")
        if tag:
            return float(tag.text.replace(",", ""))
    except:
        pass
    return None

# -----------------------------
# 네이버 차트
# -----------------------------
def get_kr_chart_naver(code):
    try:
        url = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count=180&requestType=0"
        headers = {"User-Agent":"Mozilla/5.0"}

        res = requests.get(url, headers=headers, timeout=5)
        lines = res.text.strip().split("\n")

        rows = []
        for line in lines:
            parts = line.split("|")
            if len(parts) > 5:
                rows.append([parts[0], parts[4]])

        df = pd.DataFrame(rows, columns=["date","close"])
        df["date"] = pd.to_datetime(df["date"])
        df["close"] = pd.to_numeric(df["close"])

        return df
    except:
        return pd.DataFrame()

# -----------------------------
# 미국 주식
# -----------------------------
def get_us_data(ticker):
    for _ in range(3):
        try:
            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            if not df.empty:
                df.columns = df.columns.get_level_values(0)
                return df
        except:
            pass
        time.sleep(1)
    return pd.DataFrame()

# -----------------------------
# 🔥 핵심: 통합 데이터 함수
# -----------------------------
def get_kr_data_safe_full(code):
    df = get_kr_chart_naver(code)
    price = get_kr_price_naver(code)

    # fallback → yfinance
    if df.empty or price is None:
        df_yf = get_us_data(code + ".KS")
        if not df_yf.empty:
            df_yf = df_yf.reset_index()
            df_yf.rename(columns={"Date":"date","Close":"close"}, inplace=True)
            df = df_yf[["date","close"]]
            price = float(df["close"].iloc[-1])

    return df, price

# -----------------------------
# 환율
# -----------------------------
def get_exchange_rate():
    df = get_us_data("USDKRW=X")
    if not df.empty:
        return float(df["Close"].iloc[-1])
    return 1380

# -----------------------------
# AI 프롬프트
# -----------------------------
def build_prompt(stock, price, rate, monthly, rsi):
    return f"""
너는 전문 애널리스트다. JSON만 출력.

종목:{stock}
현재가:{price}
환율:{rate}
RSI:{rsi}
데이터:{monthly}

{{
"opinion":"BUY|HOLD|SELL",
"confidence":0.0,
"summary":"",
"price":{{"target":0}},
"reason":[],
"risks":[],
"strategy":{{"buy":[],"stop_loss":0}}
}}
"""

# -----------------------------
# UI
# -----------------------------
st.title("📈 AI 투자 분석")

market = st.sidebar.selectbox("시장", ["KR","US"])

if market == "KR":
    df_krx = get_krx_list()
    keyword = st.sidebar.text_input("종목 검색")
    filtered = df_krx[df_krx["회사명"].str.contains(keyword, case=False, na=False)] if keyword else df_krx
    ticker_input = st.sidebar.selectbox("종목 선택", filtered["회사명"])
else:
    ticker_input = st.sidebar.text_input("티커", "AAPL")

# -----------------------------
# 실행
# -----------------------------
if st.sidebar.button("분석 실행"):

    if market == "KR":
        row = df_krx[df_krx["회사명"] == ticker_input]
        if row.empty:
            st.error("종목 없음")
            st.stop()

        code = row.iloc[0]["종목코드"]
        df, price = get_kr_data_safe_full(code)

    else:
        df = get_us_data(ticker_input)
        price = float(df["Close"].iloc[-1]) if not df.empty else None

    if df.empty or price is None:
        st.error("데이터 불러오기 실패 (네트워크 / 데이터소스 문제)")
        st.stop()

    # RSI
    if market == "KR":
        df["rsi"] = RSIIndicator(df["close"]).rsi()
        close_col = "close"
        df = df.set_index("date")
    else:
        df["rsi"] = RSIIndicator(df["Close"]).rsi()
        close_col = "Close"

    rsi = float(df["rsi"].iloc[-1])

    monthly = df[close_col].resample("ME").last().tail(6)
    monthly_data = [{"date":d.strftime("%m"),"price":float(p)} for d,p in zip(monthly.index, monthly)]

    rate = get_exchange_rate()

    # AI
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    res = model.generate_content(build_prompt(ticker_input, price, rate, monthly_data, rsi))
    data = safe_json_parse(res.text) or {}

    # -----------------------------
    # 출력
    # -----------------------------
    st.subheader(ticker_input)

    st.markdown(f"""
    <div class="card">
        <div class="{data.get('opinion','hold').lower()}">
        {data.get('opinion','HOLD')} ({data.get('confidence',0)*100:.0f}%)
        </div>
        <p>{data.get('summary','')}</p>
    </div>
    """, unsafe_allow_html=True)

    col1,col2,col3 = st.columns(3)

    col1.metric("현재가", f"{price:,.0f}원" if market=="KR" else f"${price:,.2f}")
    col2.metric("목표가", data.get("price",{}).get("target",0))
    col3.metric("RSI", f"{rsi:.1f}")

    # 차트
    chart_df = pd.DataFrame(monthly_data)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=chart_df["date"], y=chart_df["price"], mode="lines+markers"))
    st.plotly_chart(fig, use_container_width=True)

    st.caption("※ 투자 책임은 본인에게 있습니다.")
