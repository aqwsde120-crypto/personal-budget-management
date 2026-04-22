import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
import fear_and_greed
from datetime import datetime, timedelta
import json

# 페이지 설정
st.set_page_config(page_title="AI Pro 주식 진단", page_icon="📈", layout="wide")

# --- Toss Style CSS (White Theme) ---
st.markdown("""
<style>
    .stApp { background-color: #F2F4F6; color: #191F28; }
    section[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E5E8EB; }
    .toss-card {
        background-color: #FFFFFF;
        padding: 24px;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    .opinion-buy { color: #3182F6; font-weight: 700; }
    .opinion-hold { color: #FFBB00; font-weight: 700; }
    .opinion-sell { color: #F04452; font-weight: 700; }
    .ai-summary { font-size: 1.2rem; font-weight: 600; color: #333D4B; margin-bottom: 15px; }
    .stButton>button {
        background-color: #3182F6 !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: 600;
        padding: 10px 20px;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def get_krx_list():
    try:
        url = 'http://kind.krx.co.kr/corpoide/corpList.do?method=download'
        df = pd.read_html(url, header=0)[0]
        return {name.strip(): f"{code:06d}" for name, code in zip(df['회사명'], df['종목코드'])}
    except: return {}

def main():
    now = datetime.now()
    current_date_str = now.strftime("%Y-%m-%d")

    st.sidebar.title("설정")
    market = st.sidebar.selectbox("시장", ["KR", "US"])
    krx_dict = get_krx_list() if market == "KR" else {}
    user_input = st.sidebar.text_input("종목명 또는 코드", value="삼성전자" if market == "KR" else "AAPL")
    api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password")

    if st.sidebar.button("분석하기"):
        ticker = user_input.strip()
        if market == "KR":
            if ticker in krx_dict: ticker = f"{krx_dict[ticker]}.KS"
            elif ticker.isdigit(): ticker = f"{ticker}.KS"

        with st.spinner('AI 애널리스트가 리포트를 작성 중입니다...'):
            df = yf.download(ticker, period='1y', progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
                latest = df.iloc[-1]
                
                # --- 차트 출력 ---
                st.markdown(f"## {user_input} 분석 리포트")
                st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.update_layout(xaxis_rangeslider_visible=False, template='plotly_white', height=400, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # --- AI 분석 (JSON 모드) ---
                if api_key:
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-3-flash-preview')
                        
                        prompt = f"""
                        너는 전문 주식 애널리스트이자 리스크 관리 전문가다.
                        
                        [시스템 정보]
                        - 기준 날짜: {current_date_str}
                        - 입력 종목: {user_input} ({ticker})
                        - 현재가: {latest['Close']:.2f}
                        - RSI: {latest['RSI']:.2f}

                        [분석 목표]
                        사용자가 3초 안에 투자 판단을 내릴 수 있도록 간결하고 신뢰성 있는 JSON 데이터를 생성하라.
                        설명 문장은 포함하지 말고 반드시 JSON 형식만 출력하라.

                        [출력 구조]
                        {{
                          "stock_name": "{user_input}",
                          "stock_code": "{ticker}",
                          "opinion": "BUY | HOLD | SELL",
                          "confidence": 0.0,
                          "summary": "한 문장 요약 (20~40자)",
                          "price": {{ "current": {latest['Close']:.0f}, "target": 0, "upside": 0.0 }},
                          "risks": ["", ""],
                          "strategy": {{ "buy": [ {{"price": 0, "ratio": 0.4}}, {{"price": 0, "ratio": 0.6}} ], "stop_loss": 0 }},
                          "reason": ["근거1", "근거2", "근거3"],
                          "technical": {{ "trend": "UP | DOWN | SIDEWAYS", "support": 0, "resistance": 0, "signal": "" }}
                        }}
                        """
                        
                        response = model.generate_content(prompt)
                        # JSON 파싱 시 발생할 수 있는 텍스트 정제
                        json_str = response.text.replace('```json', '').replace('```', '').strip()
                        data = json.loads(json_str)

                        # --- AI 리포트 UI 구성 ---
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        
                        # 의견 및 요약
                        op_class = f"opinion-{data['opinion'].lower()}"
                        st.markdown(f"### 투자 의견: <span class='{op_class}'>{data['opinion']}</span> (신뢰도: {data['confidence']*100:.0f}%)", unsafe_allow_html=True)
                        st.markdown(f"<p class='ai-summary'>\"{data['summary']}\"</p>", unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**🎯 핵심 근거**")
                            for r in data['reason']: st.write(f"- {r}")
                            st.write("**⚠️ 주요 리스크**")
                            for r in data['risks']: st.write(f"- {r}")
                        
                        with col2:
                            st.write("**📊 기술적 지표**")
                            st.write(f"- 추세: {data['technical']['trend']}")
                            st.write(f"- 지지선: {data['technical']['support']:,}원")
                            st.write(f"- 저항선: {data['technical']['resistance']:,}원")
                            st.write(f"- 신호: {data['technical']['signal']}")

                        st.divider()
                        st.write("**💰 분할 매수 전략**")
                        cols = st.columns(len(data['strategy']['buy']))
                        for i, s in enumerate(data['strategy']['buy']):
                            cols[i].metric(f"매수 {i+1}", f"{s['price']:,}원", f"비중 {s['ratio']*100:.0f}%")
                        
                        st.error(f"🚫 손절가(Stop Loss): {data['strategy']['stop_loss']:,}원")
                        st.markdown('</div>', unsafe_allow_html=True)

                    except Exception as e:
                        st.error(f"AI 분석 중 오류가 발생했습니다. (JSON 파싱 실패 가능성)")
                        st.expander("Raw 데이터 보기").write(response.text if 'response' in locals() else e)
            else:
                st.error("데이터를 불러올 수 없습니다.")

if __name__ == "__main__":
    main()
