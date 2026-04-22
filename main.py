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
st.set_page_config(page_title="AI 애널리스트", page_icon="🌐", layout="wide")

# --- Toss Style CSS ---
st.markdown("""
<style>
    .stApp { background-color: #F2F4F6; color: #191F28; }
    .toss-card { background-color: #FFFFFF; padding: 24px; border-radius: 24px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04); margin-bottom: 20px; }
    .opinion-buy { color: #3182F6; font-weight: 700; font-size: 1.5rem; }
    .opinion-hold { color: #FFBB00; font-weight: 700; font-size: 1.5rem; }
    .opinion-sell { color: #F04452; font-weight: 700; font-size: 1.5rem; }
    .ai-summary { font-size: 1.15rem; color: #333D4B; font-weight: 600; line-height: 1.6; }
    .stButton>button { background-color: #3182F6 !important; border-radius: 14px; padding: 12px; font-weight: 700; width: 100%; color: white !important; }
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
        data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(data['Close'].iloc[-1]) if not data.empty else 1380.0
    except: return 1380.0

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
            # 1. 데이터 로드 및 에러 방지
            df = yf.download(ticker, period='1y', progress=False)
            if df.empty:
                st.error("종목 데이터를 가져오지 못했습니다. 티커를 확인해 주세요.")
                return

            # 데이터 정제 (MultiIndex 제거 및 시간 형식 변환)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df.index = pd.to_datetime(df.index)
            
            # 2. 6개월 월별 데이터 생성 (에러 수정 포인트)
            try:
                monthly_data = df['Close'].resample('ME').last().tail(6) # 'M' 대신 'ME' 사용(최신 판다스 권장)
                monthly_summary = [{"date": d.strftime("%Y-%m"), "price": round(float(p), 2)} for d, p in zip(monthly_data.index, monthly_data)]
            except:
                monthly_summary = [{"date": "N/A", "price": 0}]

            latest = df.iloc[-1]
            
            # 3. AI 분석 실행
            if api_key:
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-3-flash-preview')
                    
                    prompt = f"""
                    너는 전문 주식 애널리스트이자 글로벌 매크로 분석가다. 오직 JSON으로만 응답하라.
                    [정보] 날짜:{current_date}, 환율:{rate}, 종목:{user_input}, 현재가:{latest['Close']:.2f}
                    최근 6개월 흐름: {monthly_summary}
                    규칙: 사용자가 3초 내 판단하도록 간결하게. 미국 주식은 원화(KRW) 환산 필수.
                    """
                    
                    res = model.generate_content(prompt)
                    data = json.loads(res.text.replace('```json', '').replace('```', '').strip())

                    # --- UI 출력 ---
                    st.markdown(f"## {data['stock_name']} ({data['stock_code']})")
                    
                    # 투자 의견 카드
                    st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                    op_color = f"opinion-{data['opinion'].lower()}"
                    st.markdown(f"의견: <span class='{op_color}'>{data['opinion']}</span> | 신뢰도: **{data['confidence']*100:.0f}%**", unsafe_allow_html=True)
                    st.markdown(f"<p class='ai-summary'>\"{data['summary']}\"</p>", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    # 지표 카드 4열
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.metric("현재가", f"{data['price']['current']:,} {data['price']['currency']}")
                        if market == "US": st.caption(f"약 {data['price']['current_krw']:,} 원")
                        st.markdown('</div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.metric("목표가", f"{data['price']['target']:,}", f"{data['price']['upside']}%")
                        st.markdown('</div>', unsafe_allow_html=True)
                    with c3:
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.metric("신호", data['technical']['signal'])
                        st.markdown('</div>', unsafe_allow_html=True)
                    with c4:
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.metric("추세", data['technical']['trend'])
                        st.markdown('</div>', unsafe_allow_html=True)

                    # 전략 및 근거
                    col_l, col_r = st.columns(2)
                    with col_l:
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.write("**✅ 핵심 근거**")
                        for r in data['reason']: st.write(f"• {r}")
                        st.write("\n**⚠️ 주의 리스크**")
                        for r in data['risks']: st.write(f"• {r}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    with col_r:
                        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
                        st.write("**💰 투자 전략**")
                        for b in data['strategy']['buy']: st.write(f"- {b['price']:,}원 ({b['ratio']*100:.0f}%)")
                        st.error(f"손절가: {data['strategy']['stop_loss']:,}원")
                        st.markdown('</div>', unsafe_allow_html=True)

                except Exception as e:
                    st.error("AI 분석 중 JSON 파싱 에러가 발생했습니다.")
                    st.info("사이드바에서 다시 한번 '분석 실행'을 눌러주세요.")

if __name__ == "__main__":
    main()
