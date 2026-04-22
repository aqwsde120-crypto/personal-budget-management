import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
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
# JSON 파싱 안정화
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
# 환율
# -----------------------------
@st.cache_data(ttl=300)
def get_exchange_rate():
    try:
        df = yf.download("USDKRW=X", period="5d", progress=False)

        if df is None or df.empty:
            return 1380.0

        if 'Close' not in df.columns:
            return 1380.0

        val = df['Close'].dropna()
        if val.empty:
            return 1380.0

        return float(val.iloc[-1])
    except:
        return 1380.0

# -----------------------------
# 주가 데이터
# -----------------------------
@st.cache_data(ttl=300)
def get_stock_data(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)

        if df is None or df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df
    except:
        return pd.DataFrame()

# -----------------------------
# KRX 종목명 → 코드 변환
# -----------------------------
@st.cache_data(ttl=86400)
def get_krx_list():
    try:
        url = "http://kind.krx.co.kr/corpoide/corpList.do?method=download"
        df = pd.read_html(url, header=0)[0]
        df['종목코드'] = df['종목코드'].apply(lambda x: str(x).zfill(6))
        return dict(zip(df['회사명'], df['종목코드']))
    except:
        return {}

# -----------------------------
# 프롬프트
# -----------------------------
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
# API KEY
# -----------------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# -----------------------------
# UI
# -----------------------------
st.title("📈 AI 투자 분석")

market = st.sidebar.selectbox("시장", ["KR", "US"])
ticker_input = st.sidebar.text_input("종목 입력", "삼성전자" if market=="KR" else "AAPL")

# -----------------------------
# 실행
# -----------------------------
if st.sidebar.button("분석 실행"):

    ticker = ticker_input.strip()

    # ✅ 한국 주식 변환
    if market == "KR":
        krx_dict = get_krx_list()

        if ticker in krx_dict:
            ticker = krx_dict[ticker] + ".KS"
        elif ticker.isdigit():
            ticker = ticker.zfill(6) + ".KS"
        else:
            st.error("종목명을 찾을 수 없습니다.")
            st.stop()

    # 데이터 로드
    df = get_stock_data(ticker)

    if df.empty:
        st.error(f"'{ticker_input}' 데이터를 찾을 수 없습니다. (티커: {ticker})")
        st.stop()

    price = float(df['Close'].iloc[-1])

    # RSI
    df['rsi'] = RSIIndicator(df['Close']).rsi()
    rsi = float(df['rsi'].iloc[-1])

    # 6개월 데이터
    monthly = df['Close'].resample('ME').last().tail(6)
    monthly_data = [{"date": d.strftime("%m"), "price": float(p)} for d, p in zip(monthly.index, monthly)]

    rate = get_exchange_rate()

    # Gemini 최신
    model = genai.GenerativeModel("gemini-1.5-flash-latest")

    prompt = build_prompt(ticker_input, price, rate, monthly_data, rsi)

    with st.spinner("AI 분석 중..."):
        res = model.generate_content(prompt)

    data = safe_json_parse(res.text)

    # fallback
    if not data:
        st.warning("AI 응답 오류 → 기본값 사용")
        data = {
            "opinion": "HOLD",
            "confidence": 0.5,
            "summary": "데이터 부족으로 보수적 접근 필요",
            "price": {"target": 0},
            "reason": [],
            "risks": [],
            "strategy": {"buy": [], "stop_loss": 0},
            "technical": {}
        }

    # -----------------------------
    # UI 출력
    # -----------------------------
    st.markdown(f"## {data.get('stock_name', ticker_input)}")

    op = data.get("opinion", "HOLD").lower()

    st.markdown(f"""
    <div class="card">
        <div class="{op}">{data.get("opinion")} ({data.get("confidence",0)*100:.0f}%)</div>
        <p>{data.get("summary")}</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if market == "KR":
            st.metric("현재가", f"{price:,.0f}원")
        else:
            st.metric("현재가", f"${price:,.2f}")
            st.caption(f"약 {price*rate:,.0f}원")

    with col2:
        st.metric("목표가", data["price"].get("target", 0))

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

    fig.update_layout(height=300, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # 상세
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ✅ 근거")
        for r in data.get("reason", []):
            st.write(f"- {r}")

        st.markdown("### ⚠️ 리스크")
        for r in data.get("risks", []):
            st.write(f"- {r}")

    with col2:
        st.markdown("### 💰 투자 전략")
        for b in data["strategy"].get("buy", []):
            st.write(f"- {b['price']} ({b['ratio']*100:.0f}%)")

        st.write(f"손절가: {data['strategy'].get('stop_loss', 0)}")

    st.caption("※ 본 정보는 투자 참고용이며 투자 책임은 본인에게 있습니다.")
