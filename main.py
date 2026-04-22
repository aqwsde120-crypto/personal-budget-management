import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
import google.generativeai as genai
import fear_and_greed
from datetime import datetime, timedelta
import json
import re

# 페이지 설정
st.set_page_config(page_title="AI 글로벌 매크로 분석기", page_icon="📈", layout="wide")

# --- 기존 화이트/토스 스타일 CSS 유지 ---
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
    .ai-summary { font-size: 1.15rem; color: #333D4B; font-weight: 600; line-height: 1.6; }
    .stButton>button {
        background-color: #3182F6 !important;
        border-radius: 14px;
        padding: 12px;
        font-weight: 700;
        width: 100%;
        color: white !important;
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
        # 에러 방지: 데이터가 Series인지 Scalar인지 확인 후 처리
        data = yf.download("USDKRW=X", period="5d", progress=False)
        if not data.empty:
            val = data['Close'].iloc[-1]
            return float(val)
        return 1380.0
    except: return 1380.0

def clean_json(text):
    # AI 응답에서 JSON 데이터만 추출하여 파싱 에러 방지
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return match.group(0) if match else text

def main():
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    
    st.sidebar.title("💎 Premium 분석")
    market = st.sidebar.selectbox("시장 선택", ["KR", "US"])
    krx_dict = get_krx_list() if market == "KR" else {}
    user_input = st.sidebar.text_input("종목명/코드", value="삼성전자" if market == "KR" else "TSLA")
    api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("API Key", type="password")
    
    # 환율 로드 (에러 방지)
    rate = get_exchange_rate()

    if st.sidebar.button("분석 실행"):
        ticker = user_input.strip()
        if market == "KR":
            if ticker in krx_dict: ticker = f"{krx_dict[ticker]}.KS"
            elif ticker.isdigit(): ticker = f"{ticker}.KS"

        with st.spinner('글로벌 매크로 데이터 분석 중...'):
            # 1. 데이터 로드 및 전처리
            df = yf.download(ticker, period='1y', progress=False)
            if df.empty:
                st.error("데이터를 찾을 수 없습니다. 종목명이나 티커를 확인해 주세요.")
                return

            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            # 2. 6개월 월별 요약 (ValueError 해결 핵심 코드)
            try:
                # 'M' 대신 'ME'(Month End)를 사용하고 명시적으로 float 변환
                monthly_data = df['Close'].resample('ME').last().tail(6)
                monthly_summary = [{"date": d.strftime("%m월"), "price": float(p)} for d, p in zip(monthly_data.index, monthly_data)]
            except:
                monthly_summary = [{"date": "N/A", "price": 0}]

            latest_price = float(df['Close'].iloc[-1])
            
            # 3. AI 분석 실행
            if api_key:
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = f"""
                    너는 글로벌 매크로 분석가다. 오직 JSON으로만 응답하라. 설명 문장은 절대 포함하지 마라.
                    [데이터] 날짜:{current_date}, 환율:{rate}, 종목:{user_input}, 현재가:{latest_price}
                    [6개월추이]: {monthly_summary}
                    
                    반드시 요청한 JSON 구조를 지키고, 미국 주식이면 current_krw와 target_krw에 환율을 적용한 원화 가격을 넣어라.
                    """
                    
                    res = model.generate_content(prompt)
                    # JSON 파싱 에러 방지
                    clean_res = clean_json(res.text)
                    data = json.loads(clean_res)

                    # --- UI 구성 (기존 레이아웃 유지) ---
                    st.markdown(f"## {data.get('stock_name', user_input)} ({data.get('stock_code', ticker)})")
                    
                    # 투자 의견 카드
                    st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                    op = data.get('opinion', 'HOLD')
                    op_color = f"opinion-{op.lower()}"
                    st.markdown(f"투자 의견: <span class='{op_color}'>{op}</span> &nbsp;&nbsp; | &nbsp;&nbsp; 분석 신뢰도: **{data.get('confidence', 0)*100:.0f}%**", unsafe_allow_html=True)
                    st.markdown(f"<p class='ai-summary'>\"{data.get('summary', '')}\"</p>", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    # 지표 카드 (4열 배치)
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.metric("현재가", f"{latest_price:,.0f}원" if market=="KR" else f"${latest_price:,.2f}")
                        if market == "US": st.caption(f"약 {latest_price*rate:,.0f} 원")
                        st.markdown('</div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.metric("목표가", f"{data['price'].get('target', 0):,}", f"{data['price'].get('upside', 0)}%")
                        st.markdown('</div>', unsafe_allow_html=True)
                    with c3:
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.metric("신호", data['technical'].get('signal', '-'))
                        st.markdown('</div>', unsafe_allow_html=True)
                    with c4:
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.metric("추세", data['technical'].get('trend', '-'))
                        st.markdown('</div>', unsafe_allow_html=True)

                    # 6개월 추이 차트
                    st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                    st.write("**📈 최근 6개월 가격 추이**")
                    c_df = pd.DataFrame(monthly_summary)
                    fig = go.Figure(data=go.Scatter(x=c_df['date'], y=c_df['price'], mode='lines+markers', line=dict(color='#3182F6', width=3)))
                    fig.update_layout(height=300, margin=dict(t=10,b=10,l=0,r=0), template='plotly_white')
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    # 상세 분석 정보
                    col_l, col_r = st.columns(2)
                    with col_l:
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.write("**✅ 분석 근거**")
                        for r in data.get('reason', []): st.write(f"• {r}")
                        st.write("\n**⚠️ 리스크**")
                        for r in data.get('risks', []): st.write(f"• {r}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    with col_r:
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.write("**💰 투자 실행 전략**")
                        for b in data['strategy'].get('buy', []):
                            st.write(f"- {b['price']:,} 부근 (비중 {b.get('ratio', 0)*100:.0f}%)")
                        st.markdown(f"<br><h4 style='color:#F04452;'>손절가: {data['strategy'].get('stop_loss', 0):,}</h4>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

                except Exception as e:
                    st.error("분석 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")
                    st.expander("에러 상세 정보").write(e)
            else:
                st.info("사이드바에 API Key를 입력해 주세요.")

if __name__ == "__main__":
    main()
