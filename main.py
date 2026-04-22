import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
import json, re

# -----------------------------
# 설정
# -----------------------------
st.set_page_config(page_title="AI 투자 분석", layout="wide")

API_URL = "https://stock-api-qogp.onrender.com"

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# -----------------------------
# 스타일
# -----------------------------
st.markdown("""
<style>
.stApp { background-color: #F2F4F6; }
.card {
    background: white;
    padding: 24px;
    border-radius: 20px;
    margin-bottom: 16px;
}
.buy { color: #3182F6; font-weight: 700; }
.hold { color: #FFBB00; font-weight: 700; }
.sell { color: #F04452; font-weight: 700; }
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
    return {}

# -----------------------------
# KRX 리스트 (검색용)
# -----------------------------
@st.cache_data(ttl=86400)
def get_krx_list():
    try:
        df = pd.read_html("https://kind.krx.co.kr/corplist.do?method=download&searchType=13")[0]
        df = df[['회사명','종목코드']]
        df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
        return df
    except:
        return pd.DataFrame([
            ["삼성전자","005930"],
            ["SK하이닉스","000660"]
        ], columns=["회사명","종목코드"])

# -----------------------------
# API 호출
# -----------------------------
def fetch_data(market, code):
    try:
        if market == "KR":
            url = f"{API_URL}/kr/{code}"
        else:
            url = f"{API_URL}/us/{code}"

        res = requests.get(url, timeout=10).json()

        if not res.get("success"):
            return pd.DataFrame()

        df = pd.DataFrame(res["data"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        return df

    except:
        return pd.DataFrame()

# -----------------------------
# AI 프롬프트
# -----------------------------
def build_prompt(stock, price, monthly, rsi):
    return f"""
너는 전문 주식 애널리스트다.
JSON만 출력하라.

종목: {stock}
현재가: {price}
RSI: {rsi}
데이터: {monthly}

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

    ticker_name = st.sidebar.selectbox("종목 선택", filtered["회사명"])

    code = filtered[filtered["회사명"] == ticker_name]["종목코드"].values[0]

else:
    code = st.sidebar.text_input("티커 입력", "AAPL")
    ticker_name = code

# -----------------------------
# 실행
# -----------------------------
if st.sidebar.button("분석 실행"):

    df = fetch_data(market, code)

    if df.empty:
        st.error("데이터 불러오기 실패 (API 서버 또는 네트워크 문제)")
        st.stop()

    # 컬럼 통일
    if "close" not in df.columns:
        df.rename(columns={"Close":"close"}, inplace=True)

    # RSI
    df["rsi"] = RSIIndicator(df["close"]).rsi()
    rsi = float(df["rsi"].iloc[-1])

    price = float(df["close"].iloc[-1])

    # 월별 데이터
    monthly = df["close"].resample("ME").last().tail(6)
    monthly_data = [
        {"date": d.strftime("%m"), "price": float(p)}
        for d, p in zip(monthly.index, monthly)
    ]

    # AI 분석
    model = genai.GenerativeModel("gemini-1.5-flash-latest")

    with st.spinner("AI 분석 중..."):
        res = model.generate_content(build_prompt(ticker_name, price, monthly_data, rsi))

    data = safe_json_parse(res.text)

    # -----------------------------
    # 출력
    # -----------------------------
    st.subheader(f"{ticker_name} ({code})")

    op = data.get("opinion", "HOLD").lower()

    st.markdown(f"""
    <div class="card">
        <div class="{op}">
        {data.get("opinion","HOLD")} ({data.get("confidence",0)*100:.0f}%)
        </div>
        <p>{data.get("summary","")}</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    col1.metric("현재가", f"{price:,.0f}원" if market=="KR" else f"${price:.2f}")
    col2.metric("목표가", data.get("price",{}).get("target",0))
    col3.metric("RSI", f"{rsi:.1f}")

    # 차트
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly.index,
        y=monthly.values,
        mode='lines+markers'
    ))

    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

    # 상세
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 근거")
        for r in data.get("reason", []):
            st.write(f"- {r}")

        st.markdown("### 리스크")
        for r in data.get("risks", []):
            st.write(f"- {r}")

    with col2:
        st.markdown("### 전략")
        for b in data.get("strategy", {}).get("buy", []):
            st.write(f"- {b.get('price')} ({b.get('ratio',0)*100:.0f}%)")

        st.write(f"손절가: {data.get('strategy', {}).get('stop_loss', 0)}")

    st.caption("※ 투자 책임은 본인에게 있습니다.")
