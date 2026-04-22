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
st.set_page_config(page_title="AI 글로벌 매크로 분석기", page_icon="🌐", layout="wide")

# --- 토스 스타일 CSS (화이트 테마) ---
st.markdown("""
<style>
    .stApp { background-color: #F2F4F6; color: #191F28; }
    .toss-card {
        background-color: #FFFFFF;
        padding: 24px;
        border-radius: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
        margin-bottom: 20px;
    }
    .opinion-buy { color: #3182F6; font-weight: 700; font-size: 1.5rem; }
    .opinion-hold { color: #FFBB00; font-weight: 700; font-size: 1.5rem; }
    .opinion-sell { color: #F04452; font-weight: 700; font-size: 1.5rem; }
    .stMetric label { color: #4E5968 !important; }
    .ai-summary { font-size: 1.15rem; color: #333D4B; font-weight: 600; line-height: 1.6; }
    .stButton>button {
        background-color: #3182F6 !important;
        border-radius: 14px;
        padding: 12px;
        font-weight: 700;
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

def get_exchange_rate():
    try:
        data = yf.Ticker("USDKRW=X").history(period="1d")
        return float(data['Close'].iloc[-1]) if not data.empty else 1350.0
    except: return 1350.0

def main():
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    
    st.sidebar.title("💎 Premium 분석")
    market = st.sidebar.selectbox("시장 선택", ["KR", "US"])
    krx_dict = get_krx_list() if market == "KR" else {}
    user_input = st.sidebar.text_input("종목명/코드", value="삼성전자" if market == "KR" else "TSLA")
    api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("API Key", type="password")
    
    rate = get_exchange_rate()

    if st.sidebar.button("분석 실행"):
        ticker = user_input.strip()
        if market == "KR":
            if ticker in krx_dict: ticker = f"{krx_dict[ticker]}.KS"
            elif ticker.isdigit(): ticker = f"{ticker}.KS"

        with st.spinner('글로벌 매크로 데이터 분석 중...'):
            df = yf.download(ticker, period='1y', progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                latest = df.iloc[-1]
                
                # 6개월 월별 데이터 요약 (AI 참고용)
                monthly_data = df.resample('M').last().tail(6)
                monthly_summary = [{"date": d.strftime("%Y-%m"), "price": round(p, 2)} for d, p in zip(monthly_data.index, monthly_data['Close'])]

                if api_key:
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-3-flash-preview')
                        
                        prompt = f"""
                        너는 전문 주식 애널리스트이자 글로벌 매크로 분석가다.
                        설명 없이 오직 JSON으로만 응답하라.

                        [입력 정보]
                        - 기준 날짜: {current_date}
                        - 환율: 1 USD = {rate:,.1f} KRW
                        - 종목: {user_input} ({ticker})
                        - 현재가: {latest['Close']:.2f}
                        - 최근 6개월 데이터: {monthly_summary}

                        [출력 JSON 구조]
                        {{
                          "stock_name": "{user_input}",
                          "stock_code": "{ticker}",
                          "market": "{market}",
                          "opinion": "BUY | HOLD | SELL",
                          "confidence": 0.85,
                          "summary": "20~40자 내외 핵심 요약",
                          "price": {{
                            "currency": "{'KRW' if market=='KR' else 'USD'}",
                            "current": {latest['Close']:.2f},
                            "target": 0.0,
                            "upside": 0.0,
                            "current_krw": {latest['Close']*rate if market=='US' else latest['Close']:.0f},
                            "target_krw": 0
                          }},
                          "chart_6m": {monthly_summary},
                          "risks": ["리스크1", "리스크2"],
                          "strategy": {{
                            "buy": [ {{"price": 0, "ratio": 0.4}}, {{"price": 0, "ratio": 0.6}} ],
                            "stop_loss": 0
                          }},
                          "reason": ["이유1", "이유2", "이유3"],
                          "technical": {{ "trend": "UP | DOWN | SIDEWAYS", "support": 0, "resistance": 0, "signal": "매수권/관망/매도권" }},
                          "change": {{ "previous_opinion": "HOLD", "current_opinion": "BUY", "reason": "추세 반전 확인" }}
                        }}
                        """
                        
                        res = model.generate_content(prompt)
                        data = json.loads(res.text.replace('```json', '').replace('```', '').strip())

                        # --- UI 구성 ---
                        st.markdown(f"## {data['stock_name']} ({data['stock_code']})")
                        
                        # 1. 투자 의견 섹션
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        op = data['opinion']
                        op_color = "opinion-buy" if op == "BUY" else "opinion-sell" if op == "SELL" else "opinion-hold"
                        st.markdown(f"투자 의견: <span class='{op_color}'>{op}</span> &nbsp;&nbsp; | &nbsp;&nbsp; 분석 신뢰도: **{data['confidence']*100:.0f}%**", unsafe_allow_html=True)
                        st.markdown(f"<p class='ai-summary'>\"{data['summary']}\"</p>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

                        # 2. 가격 및 매크로 정보
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                            st.metric("현재가", f"{data['price']['current']:,} {data['price']['currency']}")
                            if market == "US": st.caption(f"약 {data['price']['current_krw']:,} 원")
                            st.markdown('</div>', unsafe_allow_html=True)
                        with c2:
                            st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                            st.metric("목표가", f"{data['price']['target']:,}", f"+{data['price']['upside']}%")
                            st.markdown('</div>', unsafe_allow_html=True)
                        with c3:
                            st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                            st.metric("신호", data['technical']['signal'])
                            st.markdown('</div>', unsafe_allow_html=True)
                        with c4:
                            st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                            st.metric("추세", data['technical']['trend'])
                            st.markdown('</div>', unsafe_allow_html=True)

                        # 3. 6개월 추이 차트
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.write("**📈 최근 6개월 가격 추이**")
                        c_df = pd.DataFrame(data['chart_6m'])
                        fig = go.Figure(data=go.Scatter(x=c_df['date'], y=c_df['price'], mode='lines+markers', line=dict(color='#3182F6', width=3)))
                        fig.update_layout(height=300, margin=dict(t=10,b=10,l=0,r=0), template='plotly_white')
                        st.plotly_chart(fig, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)

                        # 4. 상세 분석 및 전략
                        col_left, col_right = st.columns(2)
                        with col_left:
                            st.markdown('<div class="toss-card" style="height: 350px;">', unsafe_allow_html=True)
                            st.write("**✅ 핵심 근거**")
                            for r in data['reason']: st.write(f"• {r}")
                            st.write("\n**⚠️ 주의 리스크**")
                            for r in data['risks']: st.write(f"• {r}")
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        with col_right:
                            st.markdown('<div class="toss-card" style="height: 350px;">', unsafe_allow_html=True)
                            st.write("**💰 투자 실행 전략**")
                            for b in data['strategy']['buy']:
                                st.write(f"- {b['price']:,} 부근에서 **비중 {b['ratio']*100:.0f}%** 매수")
                            st.markdown(f"<br><h4 style='color:#F04452;'>손절가: {data['strategy']['stop_loss']:,}</h4>", unsafe_allow_html=True)
                            st.write(f"**전망 변화:** {data['change']['reason']}")
                            st.markdown('</div>', unsafe_allow_html=True)

                    except Exception as e:
                        st.error("리포트 생성 중 에러가 발생했습니다.")
                        st.write(e)
            else:
                st.error("데이터를 불러올 수 없습니다.")

if __name__ == "__main__":
    main()
