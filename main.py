import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
from datetime import datetime
import json
import re

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="AI 투자 분석", layout="wide")

# -----------------------------
# 스타일 (토스 느낌)
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
# 유틸
# -----------------------------
def safe_json_parse(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group(0))
    return None


@st.cache_data(ttl=300)
def get_exchange_rate():
    df = yf.download("USDKRW=X", period="5d", progress=False)
    if not df.empty:
        return float(df['Close'].iloc[-1])
    return 1380.0


@st.cache_data(ttl=300)
def get_stock_data(ticker):
    df = yf.download(ticker, period="1y", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def build_prompt(stock, price, rate, monthly, rsi):
    return f"""
너는 전문 주식 애널리스트다.
반드시 JSON만 출력하라.

[데이터]
종목: {stock}
현재가: {price}
환율: {rate}
RSI: {rsi}
6개월데이터: {monthly}

[출력 형식]
{{
  "stock_name": "",
  "stock_code": "",
  "market": "KR | US",
  "opinion": "BUY | HOLD | SELL",
  "confidence": 0.0,
  "summary": "",

  "price": {{
    "currency": "KRW | USD",
    "current": 0,
    "target": 0,
    "upside": 0.0,
    "current_krw": 0,
    "target_krw": 0
  }},

  "risks": ["", ""],
  "reason": ["", "", ""],

  "strategy": {{
    "buy": [
      {{"price": 0, "ratio": 0.3}},
      {{"price": 0, "ratio": 0.3}},
      {{"price": 0, "ratio": 0.4}}
    ],
    "stop_loss": 0
  }},

  "technical": {{
    "trend": "UP | DOWN | SIDEWAYS",
    "support": 0,
    "resistance": 0,
    "signal": ""
  }}
}}

설명 문장 절대 금지
"""


# -----------------------------
# UI
# -----------------------------
st.title("📈 AI 투자 분석")

market = st.sidebar.selectbox("시장", ["KR", "US"])
ticker_input = st.sidebar.text_input("종목 입력", "삼성전자" if market=="KR" else "AAPL")

api_key = st.sidebar.text_input("Gemini API Key", type="password")

if st.sidebar.button("분석 실행"):

    if not api_key:
        st.warning("API Key 필요")
        st.stop()

    # -----------------------------
    # 티커 처리
    # -----------------------------
    ticker = ticker_input
    if market == "KR":
        if ticker.isdigit():
            ticker = ticker + ".KS"

    # -----------------------------
    # 데이터 수집
    # -----------------------------
    df = get_stock_data(ticker)

    if df.empty:
        st.error("데이터 없음")
        st.stop()

    price = float(df['Close'].iloc[-1])

    # RSI
    df['rsi'] = RSIIndicator(df['Close']).rsi()
    rsi = float(df['rsi'].iloc[-1])

    # 6개월 데이터
    monthly = df['Close'].resample('ME').last().tail(6)
    monthly_data = [{"date": d.strftime("%m"), "price": float(p)} for d,p in zip(monthly.index, monthly)]

    rate = get_exchange_rate()

    # -----------------------------
    # Gemini 호출
    # -----------------------------
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = build_prompt(ticker_input, price, rate, monthly_data, rsi)

    with st.spinner("AI 분석 중..."):
        res = model.generate_content(prompt)

    data = safe_json_parse(res.text)

    if not data:
        st.error("AI 응답 실패")
        st.stop()

    # -----------------------------
    # UI 출력
    # -----------------------------
    st.markdown(f"## {data.get('stock_name', ticker_input)}")

    # 의견 카드
    op = data.get("opinion", "HOLD").lower()
    st.markdown(f"""
    <div class="card">
        <div class="{op}">{data.get("opinion")} ({data.get("confidence",0)*100:.0f}%)</div>
        <p>{data.get("summary")}</p>
    </div>
    """, unsafe_allow_html=True)

    # 가격
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("현재가", f"{price:,.0f}" if market=="KR" else f"${price:,.2f}")
        if market=="US":
            st.caption(f"약 {price*rate:,.0f}원")

    with col2:
        st.metric("목표가", data["price"].get("target",0))

    with col3:
        st.metric("RSI", f"{rsi:.1f}")

    # 차트
    st.markdown("### 📊 6개월 추이")
    chart_df = pd.DataFrame(monthly_data)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_df['date'],
        y=chart_df['price'],
        mode='lines+markers'
    ))
    st.plotly_chart(fig, use_container_width=True)

    # 근거 & 리스크
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ✅ 근거")
        for r in data.get("reason", []):
            st.write(f"- {r}")

        st.markdown("### ⚠️ 리스크")
        for r in data.get("risks", []):
            st.write(f"- {r}")

    with col2:
        st.markdown("### 💰 전략")
        for b in data["strategy"]["buy"]:
            st.write(f"- {b['price']} ({b['ratio']*100:.0f}%)")

        st.write(f"손절가: {data['strategy']['stop_loss']}")

    # 경고
    st.caption("※ 본 정보는 투자 참고용이며 책임은 본인에게 있습니다.")
