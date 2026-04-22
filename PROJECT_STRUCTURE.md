# 📁 프로젝트 구조

```
ai-stock-dashboard/
│
├── main.py                    # 메인 애플리케이션 코드
├── requirements.txt           # 필요한 라이브러리 목록
├── README.md                  # 프로젝트 설명 및 사용법
├── INSTALL.md                 # 상세 설치 가이드
├── .gitignore                 # Git 무시 파일 목록
│
└── .streamlit/                # Streamlit 설정 폴더
    └── secrets.toml           # API 키 저장 (Git 제외)
```

## 파일 설명

### 📄 main.py (메인 코드)
- **역할**: 전체 애플리케이션의 핵심 로직
- **주요 함수**:
  - `get_stock_data()`: 주가 데이터 수집
  - `get_financial_metrics()`: 재무 지표 계산
  - `calculate_technical_indicators()`: 기술적 지표 (MA, RSI, MACD)
  - `detect_pullback()`: 눌림목 패턴 탐지 ⭐
  - `get_macro_indicators()`: 거시 경제 지표
  - `create_candlestick_chart()`: Plotly 차트 생성
  - `generate_ai_analysis()`: Gemini AI 분석
  - `main()`: UI 구성 및 실행

### 📄 requirements.txt
설치할 라이브러리 목록:
- `streamlit`: 웹 UI
- `yfinance`: 주가 데이터
- `finance-datareader`: 한국 주식
- `plotly`: 차트
- `google-generativeai`: AI 분석
- `pandas`, `numpy`: 데이터 처리
- `ta`: 기술적 지표

### 📄 .streamlit/secrets.toml
API 키 저장:
```toml
GOOGLE_API_KEY = "여기에_API_키"
```

⚠️ **이 파일은 절대 Git에 올리지 마세요!**

### 📄 .gitignore
Git에서 제외할 파일:
- `.streamlit/secrets.toml` (보안)
- `__pycache__/` (Python 캐시)
- `venv/` (가상환경)
- `.DS_Store` (Mac 시스템 파일)

## 🚀 실행 흐름

```
1. 사용자가 종목 코드 입력
   ↓
2. yfinance/FinanceDataReader로 데이터 수집
   ↓
3. 기술적 지표 계산 (MA, RSI, MACD)
   ↓
4. 눌림목 패턴 탐지
   ↓
5. 거시 경제 지표 수집
   ↓
6. Plotly로 차트 렌더링
   ↓
7. Gemini AI에게 분석 요청
   ↓
8. 결과를 대시보드에 표시
```

## 📊 데이터 흐름

```
외부 API
├── yfinance (미국 주식)
├── FinanceDataReader (한국 주식)
├── Yahoo Finance (금리, 환율)
└── Google Gemini API (AI 분석)
    ↓
main.py (데이터 처리 및 분석)
    ↓
Streamlit UI (사용자에게 표시)
```

## 🔧 커스터마이징 포인트

### 눌림목 기준 변경
`main.py` 259번째 줄:
```python
near_ma20 = 0 <= distance_from_ma20 <= 3  # 3% → 원하는 값
```

### 이동평균선 기간 변경
`main.py` 188-191번째 줄:
```python
df['MA5'] = df['Close'].rolling(window=5).mean()    # 5 → 원하는 값
df['MA20'] = df['Close'].rolling(window=20).mean()  # 20 → 원하는 값
```

### AI 모델 변경
`main.py` 377번째 줄:
```python
model = genai.GenerativeModel('gemini-pro')  # 다른 모델로 변경 가능
```

### UI 색상 변경
`main.py` 17-29번째 줄 (CSS 스타일):
```css
.main-title {
    color: #1E88E5;  /* 원하는 색상 */
}
```

## 💡 코드 하이라이트

### 눌림목 탐지 로직 (핵심!)
```python
# 조건 1: 20일선 상단
above_ma20 = current_price > ma20

# 조건 2: 3% 이내 근접
distance = ((current_price - ma20) / ma20) * 100
near_ma20 = 0 <= distance <= 3

# 조건 3: 거래량 감소
recent_vol = df['Volume'].iloc[-5:-1].mean()
prev_vol = df['Volume'].iloc[-15:-5].mean()
volume_decreasing = recent_vol < prev_vol

# 최종 판단
is_pullback = above_ma20 and near_ma20 and volume_decreasing
```

### AI 프롬프트 구조
```python
프롬프트 = f"""
1. 재무 지표: {financial_metrics}
2. 눌림목 분석: {pullback_info}
3. 기술적 지표: {technical_summary}
4. 거시 환경: {macro_indicators}

→ 투자 의견 + 근거 + 목표가 제시
"""
```

## 🎓 학습 포인트

이 프로젝트에서 배울 수 있는 것:
1. **금융 데이터 수집**: API 활용
2. **기술적 분석**: 이동평균선, RSI, MACD
3. **패턴 인식**: 눌림목 알고리즘
4. **데이터 시각화**: Plotly 인터랙티브 차트
5. **AI 통합**: LLM API 프롬프트 엔지니어링
6. **웹 앱 개발**: Streamlit 프레임워크

---

**Happy Coding! 🚀**
