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
# KRX 종목 리스트
# -----------------------------
@st.cache_data(ttl=86400)
@st.cache_data(ttl=86400)
def get_krx_list():
    try:
        # 방법 1: 가장 안정적인 최신 URL (2025~2026 기준)
        url = "https://kind.krx.co.kr/corplist.do?method=download&searchType=13"
        df = pd.read_html(url, header=0)[0]
        
        df = df[['회사명', '종목코드']].copy()
        df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
        return dict(zip(df['회사명'], df['종목코드']))
        
    except Exception as e:
        st.warning(f"KRX 리스트 로드 실패: {str(e)[:100]}... 대체 리스트 사용")
        
        # 방법 2: 실패 시 대체 (상위 종목만이라도)
        fallback = {
            "삼성전자": "005930", "SK하이닉스": "000660", "LG에너지솔루션": "373220",
            "삼성바이오로직스": "207940", "현대차": "005380", "카카오": "035720",
            "네이버": "035420", "삼성전자우": "005935", "POSCO홀딩스": "005490",
            # 자주 쓰는 종목 30~50개 정도 미리 넣어두는 게 좋음
        }
        return fallback

# -----------------------------
# yfinance 안정화
# -----------------------------
@st.cache_data(ttl=60)
def get_stock_data_safe(ticker):
    for i in range(3):
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

# -----------------------------
# 한국 주식 (fallback 포함)
# -----------------------------
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
# 프롬프트
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

  "price": {{
    "target": 0
  }},

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

설명 금지
"""

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

    # 한국 주식 변환
    if market == "KR":
        krx_dict = get_krx_list()

        if ticker in krx_dict:
            code = krx_dict[ticker]
        elif ticker.isdigit():
            code = ticker.zfill(6)
        else:
            st.error("종목명을 찾을 수 없습니다.")
            st.stop()

        df = get_kr_data_safe(code)

    else:
        df = get_stock_data_safe(ticker)

    # 데이터 실패 처리
    if df.empty:
        st.error("현재 데이터 제공이 원활하지 않습니다. 잠시 후 다시 시도해주세요.")
        st.stop()

    price = float(df['Close'].iloc[-1])

    # RSI
    df['rsi'] = RSIIndicator(df['Close']).rsi()
    rsi = float(df['rsi'].iloc[-1])

    # 6개월 데이터
    monthly = df['Close'].resample('ME').last().tail(6)
    monthly_data = [{"date": d.strftime("%m"), "price": float(p)} for d, p in zip(monthly.index, monthly)]

    rate = get_exchange_rate()

    # AI
    model = genai.GenerativeModel("gemini-1.5-flash-latest")

    prompt = build_prompt(ticker_input, price, rate, monthly_data, rsi)

    with st.spinner("AI 분석 중..."):
        res = model.generate_content(prompt)

    data = safe_json_parse(res.text)

    # fallback
    if not data:
        data = {
            "opinion": "HOLD",
            "confidence": 0.5,
            "summary": "데이터 부족으로 보수적 접근 필요",
            "price": {"target": 0},
            "reason": [],
            "risks": [],
            "strategy": {"buy": [], "stop_loss": 0}
        }

    # -----------------------------
    # UI 출력
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
