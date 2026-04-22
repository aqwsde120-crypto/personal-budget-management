# 📦 설치 및 실행 가이드

## 빠른 시작 (Quick Start)

```bash
# 1. 라이브러리 설치
pip install -r requirements.txt

# 2. API 키 설정 (아래 상세 설명 참고)
# .streamlit/secrets.toml 파일 생성 또는 코드 수정

# 3. 실행
streamlit run main.py
```

---

## 상세 설치 과정

### 1️⃣ Python 설치 확인

```bash
python --version
```

- Python 3.8 이상 필요
- 없으면 https://www.python.org/downloads/ 에서 설치

### 2️⃣ 프로젝트 다운로드

```bash
# Git으로 클론 (또는 ZIP 다운로드)
git clone <repository-url>
cd ai-stock-dashboard
```

### 3️⃣ 가상환경 생성 (선택사항, 권장)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4️⃣ 라이브러리 설치

```bash
pip install -r requirements.txt
```

설치되는 라이브러리:
- `streamlit`: 웹 대시보드 프레임워크
- `yfinance`: 야후 파이낸스 API
- `finance-datareader`: 한국 주식 데이터
- `plotly`: 인터랙티브 차트
- `google-generativeai`: Gemini AI API
- `pandas`, `numpy`: 데이터 처리
- `ta`: 기술적 지표 계산

### 5️⃣ Google AI Studio API 키 발급

#### API 키 발급
1. https://aistudio.google.com/app/apikey 접속
2. Google 계정 로그인
3. **"Create API Key"** 클릭
4. 프로젝트 선택 (또는 새로 생성)
5. API 키 복사 (예: `AIzaSyC...`)

#### API 키 설정

**방법 A: secrets.toml 사용 (권장) 🌟**

1. 프로젝트 폴더에 `.streamlit` 디렉토리 생성:
```bash
mkdir .streamlit
```

2. `.streamlit/secrets.toml` 파일 생성:
```bash
# Windows
notepad .streamlit\secrets.toml

# Mac/Linux
nano .streamlit/secrets.toml
```

3. 아래 내용 입력 후 저장:
```toml
GOOGLE_API_KEY = "여기에_발급받은_API_키_붙여넣기"
```

**방법 B: 코드 직접 수정**

`main.py` 파일을 열어 104번째 줄 수정:
```python
# 수정 전
default_api_key = st.secrets.get("GOOGLE_API_KEY", "임시키")

# 수정 후
default_api_key = st.secrets.get("GOOGLE_API_KEY", "여기에_발급받은_API_키")
```

> ⚠️ **보안 주의**  
> - secrets.toml 파일은 Git에 커밋하지 마세요!
> - `.gitignore`에 이미 등록되어 있습니다.

### 6️⃣ 실행

```bash
streamlit run main.py
```

브라우저가 자동으로 열리면서 `http://localhost:8501`로 접속됩니다.

---

## 문제 해결 (Troubleshooting)

### ❌ 라이브러리 설치 실패

```bash
# pip 업그레이드
pip install --upgrade pip

# 재시도
pip install -r requirements.txt
```

### ❌ "No module named 'streamlit'" 에러

```bash
# 가상환경 활성화 확인
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# streamlit 설치
pip install streamlit
```

### ❌ API 키 오류

**증상**: "AI 분석 생성 실패" 메시지

**해결**:
1. API 키가 정확한지 확인
2. `.streamlit/secrets.toml` 파일 위치 확인
3. API 키에 따옴표(`"`) 포함 확인:
   ```toml
   GOOGLE_API_KEY = "AIzaSy..."  # ✅ 올바름
   GOOGLE_API_KEY = AIzaSy...    # ❌ 틀림
   ```

### ❌ 재무 지표 "N/A"만 표시

**증상**: PER, PBR 등이 모두 N/A

**원인**: 
- 종목 코드 오류
- 인터넷 연결 문제
- yfinance API 일시적 오류

**해결**:
- 종목 코드 확인 (예: 삼성전자 = 005930, Apple = AAPL)
- 인터넷 연결 확인
- 잠시 후 재시도

### ❌ 차트가 안 보임

**해결**:
```bash
# plotly 재설치
pip uninstall plotly
pip install plotly==5.18.0
```

### ❌ 한국 주식 데이터 안 나옴

**해결**:
```bash
# FinanceDataReader 재설치
pip install --upgrade finance-datareader
```

---

## 🎯 사용 팁

### 종목 코드 찾기

**미국 주식:**
- Apple: `AAPL`
- Tesla: `TSLA`
- NVIDIA: `NVDA`
- Microsoft: `MSFT`
- Amazon: `AMZN`

**한국 주식:**
- 삼성전자: `005930`
- SK하이닉스: `000660`
- 카카오: `035720`
- NAVER: `035420`
- LG화학: `051910`

### 최적의 분석 시점

- 미국 주식: 한국 시간 23:30 ~ 06:00 (장중)
- 한국 주식: 한국 시간 09:00 ~ 15:30 (장중)

### API 할당량 절약

- 하루 1,500회 요청 제한
- 종목당 1~2회 분석 권장
- 과도한 새로고침 자제

---

## 📞 지원

문제가 해결되지 않으면:
1. GitHub Issues 등록
2. README.md 참고
3. 에러 메시지 전체 복사해서 검색

---

**즐거운 투자 되세요! 📈**
