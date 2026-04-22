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

API_KEY = "8VZP06Y0I6WAXW7H"
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

.title {
    font-size: 20px;
    font-weight: 700;
}

.buy { color: #3182F6; font-weight: 800; font-size:22px;}
.hold { color: #FFB020; font-weight: 800; font-size:22px;}
.sell { color: #F04452; font-weight: 800; font-size:22px;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 데이터
# -----------------------------
def get_data(symbol):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}"
    res = requests.get(url).json()

    if "Time Series (Daily)" not in res:
        return pd.DataFrame()

    df = pd.DataFrame(res["Time Series (Daily)"]).T
    df = df.rename(columns={"4. close":"close"})
    df["close"] = df["close"].astype(float)
    df.index = pd.to_datetime(df.index)

    return df.sort_index()

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
# AI 프롬프트 (강화)
# -----------------------------
def build_prompt(symbol, price, rsi, trend):
    return f"""
너는 기관 투자자 수준의 애널리스트다.

종목: {symbol}
현재가: {price}
RSI: {rsi}
추세: {trend}

다음 JSON만 출력:
{{
"opinion":"BUY|HOLD|SELL",
"confidence":0~1,
"summary":"핵심 요약 (1~2줄)",
"target_price":숫자,
"reasons":[
 "기술적 분석 근거",
 "수급/심리 분석",
 "추세 판단"
],
"risks":[
 "리스크1",
 "리스크2"
],
"strategy":{{
 "entry":"진입 전략",
 "stop_loss":"손절 전략",
 "take_profit":"익절 전략"
}}
}}
"""

# -----------------------------
# UI
# -----------------------------
st.title("📈 AI 투자 분석")

ticker = st.sidebar.text_input("티커 입력", "AAPL")

if st.sidebar.button("분석 실행"):

    df = get_data(ticker)

    if df.empty:
        st.error("데이터 불러오기 실패 (API 제한 또는 키 문제)")
        st.stop()

    # 지표
    df["rsi"] = RSIIndicator(df["close"]).rsi()
    price = float(df["close"].iloc[-1])
    rsi = float(df["rsi"].iloc[-1])

    trend = "상승" if df["close"].iloc[-1] > df["close"].iloc[-20] else "하락"

    # AI 분석
    model = genai.GenerativeModel("gemini-1.5-flash-latest")

    with st.spinner("AI 분석 중..."):
        res = model.generate_content(build_prompt(ticker, price, rsi, trend))

    data = safe_json_parse(res.text)

    op = data.get("opinion","HOLD").lower()

    # -----------------------------
    # 결과 카드
    # -----------------------------
    st.markdown(f"""
    <div class="card">
        <div class="{op}">
            {data.get("opinion","HOLD")} ({data.get("confidence",0)*100:.0f}%)
        </div>
        <div class="title">{data.get("summary","")}</div>
    </div>
    """, unsafe_allow_html=True)

    # 핵심 지표
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"${price:.2f}")
    col2.metric("RSI", f"{rsi:.1f}")
    col3.metric("목표가", data.get("target_price",0))

    # 차트
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["close"], mode='lines'))
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)

    # 상세 분석
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
        st.write(f"진입: {data.get('strategy',{}).get('entry','')}")
        st.write(f"손절: {data.get('strategy',{}).get('stop_loss','')}")
        st.write(f"익절: {data.get('strategy',{}).get('take_profit','')}")

    st.caption("※ 투자 책임은 본인에게 있습니다.")
