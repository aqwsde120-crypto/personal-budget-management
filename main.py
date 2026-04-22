import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
import json, re
import requests

# -----------------------------
# 설정
# -----------------------------
st.set_page_config(page_title="AI 투자 분석", layout="wide")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 🔥 핵심: yfinance 안정화
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

# -----------------------------
# 스타일
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
# 데이터 (재시도 포함)
# -----------------------------
def get_data(symbol, market):
    for i in range(5):  # 🔥 재시도
        try:
            if market == "KR":
                ticker = symbol + ".KS"
            else:
                ticker = symbol

            df = yf.download(
                ticker,
                period="6mo",
                interval="1d",
                progress=False,
                session=session
            )

            if not df.empty:
                df.columns = df.columns.get_level_values(0)
                df = df.rename(columns={"Close":"close"})
                return df

        except:
            pass

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

if market == "KR":
    code = st.sidebar.text_input("종목코드", "005930")
else:
    code = st.sidebar.text_input("티커", "AAPL")

# -----------------------------
# 실행
# -----------------------------
if st.sidebar.button("분석 실행"):

    with st.spinner("데이터 불러오는 중..."):
        df = get_data(code, market)

    if df.empty:
        st.error("데이터 불러오기 실패 (Yahoo Finance 차단 또는 일시 오류)")
        st.stop()

    df["rsi"] = RSIIndicator(df["close"]).rsi()

    price = float(df["close"].iloc[-1])
    rsi = float(df["rsi"].iloc[-1])

    trend = "상승" if df["close"].iloc[-1] > df["close"].iloc[-20] else "하락"

    # AI
    model = genai.GenerativeModel("gemini-1.5-flash-latest")

    with st.spinner("AI 분석 중..."):
        res = model.generate_content(build_prompt(code, price, rsi, trend))

    data = safe_json_parse(res.text)

    op = data.get("opinion","HOLD").lower()

    st.markdown(f"""
    <div class="card">
        <div class="{op}">
            {data.get("opinion","HOLD")} ({data.get("confidence",0)*100:.0f}%)
        </div>
        <p>{data.get("summary","")}</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"{price:,.0f}" if market=="KR" else f"${price:.2f}")
    col2.metric("RSI", f"{rsi:.1f}")
    col3.metric("목표가", data.get("target_price",0))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["close"]))
    st.plotly_chart(fig)

    st.caption("※ 투자 책임은 본인에게 있습니다.")
