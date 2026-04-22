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

ALPHA_KEY = "여기에_ALPHA_KEY"
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# -----------------------------
# 스타일 (토스 느낌)
# -----------------------------
st.markdown("""
<style>
.stApp { background-color: #F5F6F8; }
.card {
    background: white;
    padding: 24px;
    border-radius: 20px;
    margin-bottom: 16px;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
}
.buy { color: #3182F6; font-weight:800; font-size:22px;}
.hold { color: #FFB020; font-weight:800; font-size:22px;}
.sell { color: #F04452; font-weight:800; font-size:22px;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 한국 주식 (네이버)
# -----------------------------
def get_kr_data(code):
    try:
        url = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count=180&requestType=0"
        headers = {"User-Agent":"Mozilla/5.0"}
        res = requests.get(url, headers=headers)

        rows = []
        for line in res.text.split("\n"):
            p = line.split("|")
            if len(p) > 5:
                rows.append({"date": p[0], "close": float(p[4])})

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        return df

    except:
        return pd.DataFrame()

# -----------------------------
# 미국 주식 (Alpha Vantage)
# -----------------------------
def get_us_data(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_KEY}"
        res = requests.get(url).json()

        if "Time Series (Daily)" not in res:
            return pd.DataFrame()

        df = pd.DataFrame(res["Time Series (Daily)"]).T
        df = df.rename(columns={"4. close":"close"})
        df["close"] = df["close"].astype(float)
        df.index = pd.to_datetime(df.index)

        return df.sort_index()

    except:
        return pd.DataFrame()

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
# AI 프롬프트
# -----------------------------
def build_prompt(name, price, rsi, trend):
    return f"""
너는 전문 투자 애널리스트다.

종목:{name}
현재가:{price}
RSI:{rsi}
추세:{trend}

JSON만 출력:
{{
"opinion":"BUY|HOLD|SELL",
"confidence":0~1,
"summary":"",
"target_price":0,
"reasons":[],
"risks":[],
"strategy":{{
 "entry":"",
 "stop_loss":"",
 "take_profit":""
}}
}}
"""

# -----------------------------
# UI
# -----------------------------
st.title("📈 AI 투자 분석")

market = st.sidebar.selectbox("시장", ["KR","US"])

# 간단 종목 매핑
kr_dict = {
    "삼성전자":"005930",
    "SK하이닉스":"000660",
    "NAVER":"035420"
}

if market == "KR":
    name = st.sidebar.text_input("종목명", "삼성전자")
    code = kr_dict.get(name, name)
    df = get_kr_data(code)
else:
    code = st.sidebar.text_input("티커", "AAPL")
    df = get_us_data(code)

# -----------------------------
# 실행
# -----------------------------
if st.sidebar.button("분석 실행"):

    if df.empty:
        st.error("데이터 불러오기 실패")
        st.stop()

    df["rsi"] = RSIIndicator(df["close"]).rsi()

    price = float(df["close"].iloc[-1])
    rsi = float(df["rsi"].iloc[-1])

    trend = "상승" if df["close"].iloc[-1] > df["close"].iloc[-20] else "하락"

    # AI 분석
    model = genai.GenerativeModel("gemini-1.5-flash-latest")

    with st.spinner("AI 분석 중..."):
        res = model.generate_content(build_prompt(code, price, rsi, trend))

    data = safe_json_parse(res.text)

    op = data.get("opinion","HOLD").lower()

    # 결과 카드
    st.markdown(f"""
    <div class="card">
        <div class="{op}">
            {data.get("opinion","HOLD")} ({data.get("confidence",0)*100:.0f}%)
        </div>
        <p>{data.get("summary","")}</p>
    </div>
    """, unsafe_allow_html=True)

    # 핵심 지표
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"{price:,.0f}" if market=="KR" else f"${price:.2f}")
    col2.metric("RSI", f"{rsi:.1f}")
    col3.metric("목표가", data.get("target_price",0))

    # 차트
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["close"], mode='lines'))
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)

    # 상세
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 투자 근거")
        for r in data.get("reasons", []):
            st.write(f"- {r}")

        st.markdown("### ⚠️ 리스크")
        for r in data.get("risks", []):
            st.write(f"- {r}")

    with col2:
        st.markdown("### 🎯 전략")
        st.write("진입:", data.get("strategy",{}).get("entry",""))
        st.write("손절:", data.get("strategy",{}).get("stop_loss",""))
        st.write("익절:", data.get("strategy",{}).get("take_profit",""))

    st.caption("※ 투자 책임은 본인에게 있습니다.")
