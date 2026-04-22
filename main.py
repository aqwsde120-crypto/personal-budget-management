import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
import json
import re
import time

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
    return None

# -----------------------------
# KRX 리스트
# -----------------------------
@st.cache_data(ttl=86400)
def get_krx_list():
    try:
        url = "https://kind.krx.co.kr/corplist.do?method=download&searchType=13"
        df = pd.read_html(url, header=0)[0]

        df = df[['회사명', '종목코드']].copy()
        df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)

        return df

    except:
        # fallback
        data = [
            ["삼성전자","005930"],
            ["SK하이닉스","000660"],
            ["LG에너지솔루션","373220"],
            ["삼성바이오로직스","207940"],
            ["현대차","005380"],
            ["카카오","035720"],
            ["네이버","035420"]
        ]
        return pd.DataFrame(data, columns=["회사명","종목코드"])

# -----------------------------
# 데이터 안정화
# -----------------------------
@st.cache_data(ttl=60)
def get_stock_data_safe(ticker):
    for _ in range(3):
        try:
            df = yf.download(
                ticker,
                period="6mo",
                interval="1d",
                progress=False,
                threads=False
            )
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df
        except:
            pass
        time.sleep(1)
    return pd.DataFrame()

def get_kr_data_safe(code):
    df = get_stock_data_safe(code + ".KS")
    if df.empty:
        df = get_stock_data_safe(code + ".KQ")
    return df

# -----------------------------
# 환율
# -----------------------------
@st.cache_data(ttl=300)
def get_exchange_rate():
    df = get_stock_data_safe("USDKRW=X")
    if not df.empty:
        return float(df['Close'].iloc[-1])
    return 1380.0

# -----------------------------
# AI 프롬프트
# -----------------------------
def build_prompt(stock, price, rate, monthly, rsi):
    return f"""
너는 전문 주식 애널리스트다.
반드시 JSON만 출력하라.

종목: {stock}
현재가: {price}
환율: {rate}
RSI: {rsi}
6개월데이터: {monthly}

형식:
{{
  "stock_name": "",
  "stock_code": "",
  "market": "KR | US",
  "opinion": "BUY | HOLD | SELL",
  "confidence": 0.0,
  "summary": "",
  "price": {{"target": 0}},
  "reason": ["", "", ""],
  "risks": ["", ""],
  "strategy": {{
    "buy": [
      {{"price": 0, "ratio": 0.3}},
      {{"price": 0, "ratio": 0.3}},
      {{"price": 0, "ratio": 0.4}}
    ],
    "stop_loss": 0
  }}
}}
"""

# -----------------------------
# UI
# -----------------------------
st.title("📈 AI 투자 분석")

market = st.sidebar.selectbox("시장", ["KR", "US"])

# 🔥 핵심 개선: 검색 + 직접입력 + 코드검색
if market == "KR":
    df_krx = get_krx_list()

    search_mode = st.sidebar.radio("검색 방식", ["검색", "직접 입력"])

    if search_mode == "검색":
        keyword = st.sidebar.text_input("종목명 검색")

        filtered = df_krx[df_krx['회사명'].str.contains(keyword, case=False, na=False)] if keyword else df_krx

        ticker_input = st.sidebar.selectbox(
            "종목 선택",
            filtered['회사명'].tolist()
        )
    else:
        ticker_input = st.sidebar.text_input("종목명 또는 코드", "005930")

else:
    ticker_input = st.sidebar.text_input("티커 입력", "AAPL")

# -----------------------------
# 실행
# -----------------------------
if st.sidebar.button("분석 실행"):

    if market == "KR":
        df_krx = get_krx_list()

        if ticker_input.isdigit():
            code = ticker_input.zfill(6)
        else:
            row = df_krx[df_krx['회사명'] == ticker_input]
            if row.empty:
                st.error("종목을 찾을 수 없습니다.")
                st.stop()
            code = row.iloc[0]['종목코드']

        df = get_kr_data_safe(code)

    else:
        df = get_stock_data_safe(ticker_input)

    if df.empty:
        st.error("데이터 불러오기 실패 (yfinance 한계)")
        st.stop()

    price = float(df['Close'].iloc[-1])

    df['rsi'] = RSIIndicator(df['Close']).rsi()
    rsi = float(df['rsi'].iloc[-1])

    monthly = df['Close'].resample('ME').last().tail(6)
    monthly_data = [{"date": d.strftime("%m"), "price": float(p)} for d, p in zip(monthly.index, monthly)]

    rate = get_exchange_rate()

    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    prompt = build_prompt(ticker_input, price, rate, monthly_data, rsi)

    with st.spinner("AI 분석 중..."):
        res = model.generate_content(prompt)

    data = safe_json_parse(res.text)

    if not data:
        data = {
            "opinion": "HOLD",
            "confidence": 0.5,
            "summary": "데이터 부족",
            "price": {"target": 0},
            "reason": [],
            "risks": [],
            "strategy": {"buy": [], "stop_loss": 0}
        }

    # -----------------------------
    # 출력
    # -----------------------------
    st.subheader(ticker_input)

    op = data.get("opinion", "HOLD").lower()

    st.markdown(f"""
    <div class="card">
        <div class="{op}">{data.get("opinion")} ({data.get("confidence",0)*100:.0f}%)</div>
        <p>{data.get("summary")}</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("현재가", f"{price:,.0f}원" if market=="KR" else f"${price:,.2f}")

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

    fig.update_layout(height=300)
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
        st.markdown("### 💰 전략")
        for b in data["strategy"].get("buy", []):
            st.write(f"- {b['price']} ({b['ratio']*100:.0f}%)")

        st.write(f"손절가: {data['strategy'].get('stop_loss', 0)}")

    st.caption("※ 투자 책임은 본인에게 있습니다.")
