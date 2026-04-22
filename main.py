import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
import json, re, time

# -----------------------------
# 설정
# -----------------------------
st.set_page_config(page_title="AI 투자 분석", layout="wide")

API_URL = "https://stock-api-qogp.onrender.com"

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

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
# 🔥 핵심: 안정화된 API 호출
# -----------------------------
def fetch_data(market, code):

    for attempt in range(5):  # 🔥 5번 재시도 (중요)
        try:
            if market == "KR":
                url = f"{API_URL}/kr/{code}"
            else:
                url = f"{API_URL}/us/{code}"

            res = requests.get(url, timeout=20)

            if res.status_code != 200:
                time.sleep(2)
                continue

            data = res.json()

            if not data.get("success"):
                time.sleep(2)
                continue

            df = pd.DataFrame(data["data"])

            if df.empty:
                time.sleep(2)
                continue

            # 컬럼 처리
            if "close" not in df.columns:
                df.rename(columns={"Close":"close"}, inplace=True)

            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")

            return df

        except Exception as e:
            time.sleep(2)

    return pd.DataFrame()

# -----------------------------
# AI 프롬프트
# -----------------------------
def build_prompt(stock, price, monthly, rsi):
    return f"""
너는 전문 주식 애널리스트다. JSON만 출력.

종목:{stock}
현재가:{price}
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
    code = st.sidebar.text_input("종목코드", "005930")
    ticker_name = code
else:
    code = st.sidebar.text_input("티커", "AAPL")
    ticker_name = code

# -----------------------------
# 실행
# -----------------------------
if st.sidebar.button("분석 실행"):

    with st.spinner("데이터 불러오는 중..."):
        df = fetch_data(market, code)

    if df.empty:
        st.error("데이터 불러오기 실패 (API 응답 지연 또는 Render 슬립)")
        st.stop()

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
        res = model.generate_content(
            build_prompt(ticker_name, price, monthly_data, rsi)
        )

    data = safe_json_parse(res.text)

    # -----------------------------
    # 출력
    # -----------------------------
    st.subheader(f"{ticker_name}")

    st.write(f"현재가: {price:,.0f}" if market=="KR" else f"${price:.2f}")
    st.write(f"RSI: {rsi:.1f}")

    st.write(data)

    # 차트
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly.index,
        y=monthly.values,
        mode='lines+markers'
    ))

    st.plotly_chart(fig, use_container_width=True)

    st.caption("※ 투자 책임은 본인에게 있습니다.")
