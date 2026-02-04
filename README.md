# AI 뉴스 알림 MCP 서버

멀티에이전트 기반의 AI 트렌드 뉴스 수집 및 알림 시스템입니다. 최신 AI 관련 뉴스를 자동으로 수집, 번역, 분석, 분류하여 텔레그램과 이메일로 전송합니다.

## 🏗️ 시스템 아키텍처

### 에이전트 구조
```
Collector → Translator → Analyzer → Categorizer → Senders
   (뉴스 수집)    (번역)      (분석)       (분류)     (전송)
                                            ↓
                                 ┌─────────────────┐
                                 │ Telegram-Sender │
                                 └─────────────────┘
                                            ↓
                                 ┌─────────────────┐
                                 │   Mail-Sender   │
                                 └─────────────────┘
```

### 에이전트 상세 정보

#### 1. Collector Agent (수집기)
- **역할**: 국내외 AI 트렌드 뉴스 수집
- **소스**: 국내 뉴스 포털, 해외 테크 미디어, RSS 피드
- **특징**: AI 관련 키워드 필터링, 중복 제거

#### 2. Translator Agent (번역기)  
- **역할**: 해외 뉴스 한국어 번역
- **지원**: Google Translate API, Papago API
- **특징**: 번역 품질 평가, 신뢰도 측정

#### 3. Analyzer Agent (분석기)
- **역할**: 뉴스 내용 분석 및 요약 (10줄 이내)
- **모델**: 간단 분석, GPT 기반 분석
- **출력**: 요약, 핵심 포인트, 중요도 평가

#### 4. Categorizer Agent (분류기)
- **역할**: 뉴스 카테고리 분류 및 태깅
- **카테고리**: ML, DL, NLP, CV, 생성AI 등 10개 카테고리
- **특징**: 트렌드 레벨 평가 (High/Medium/Low)

#### 5. Telegram-Sender Agent (텔레그램 발신자)
- **역할**: 포맷팅된 뉴스 텔레그램으로 전송
- **기능**: 구독 관리, 커맨드 처리 (/start, /help 등)
- **포맷**: 마크다운 지원, 이모지 활용

#### 6. Mail-Sender Agent (메일 발신자)
- **역할**: HTML/텍스트 이메일로 뉴스 전송
- **기능**: 뉴스 다이제스트, 수신자 관리
- **템플릿**: Jinja2 기반 동적 템플릿

## 🚀 설치 및 설정

### 1. 환경 설정
```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일에 필요한 설정 입력
```

### 2. 필수 설정

#### 텔레그램 설정
1. **BotFather로 봇 생성**: `/newbot` 명령어로 봇 생성 및 토큰 발급
2. **채팅 ID 확인**: @userinfobot으로 채팅 ID 확인
3. **환경 변수 설정**:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ALLOWED_CHAT_IDS=123456789,987654321
   ```

#### 이메일 설정 (Gmail 예시)
1. **앱 비밀번호 생성**: Google 계정 설정 → 보안 → 앱 비밀번호
2. **환경 변수 설정**:
   ```
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password_here
   ```

#### API 키 설정
- **Google Translate**: Google Cloud Console에서 API 키 발급
- **OpenAI**: platform.openai.com에서 API 키 발급  
- **Papago**: Naver Developers에서 클라이언트 ID/시크릿 발급

## 🏃‍♂️ 실행 방법

### MCP 서버 실행
```bash
python main_news_mcp.py
```

### MCP 툴 사용 예시

#### 뉴스 수집 시작
```python
{
  "tool": "start_news_collection",
  "parameters": {
    "force": true
  }
}
```

#### 텔레그램 구독
```python
{
  "tool": "subscribe_telegram", 
  "parameters": {
    "chat_id": 123456789
  }
}
```

#### 이메일 구독
```python
{
  "tool": "subscribe_email",
  "parameters": {
    "email": "user@example.com"
  }
}
```

#### 테스트 알림 전송
```python
{
  "tool": "send_test_notification",
  "parameters": {
    "channel": "all"
  }
}
```

## 📋 MCP 툴 목록

| 툴 이름 | 설명 | 파라미터 |
|--------|------|---------|
| `start_news_collection` | 뉴스 수집 시작 | `force` (boolean) |
| `get_news_summary` | 최신 뉴스 요약 | `limit`, `category`, `trend_level` |
| `subscribe_telegram` | 텔레그램 구독 | `chat_id` (int) |
| `subscribe_email` | 이메일 구독 | `email` (string) |
| `configure_news_sources` | 뉴스 소스 설정 | `enable_domestic`, `enable_international` |
| `get_agent_status` | 에이전트 상태 조회 | 없음 |
| `send_test_notification` | 테스트 알림 전송 | `channel` (telegram/email/all) |

## 📊 데이터 흐름

```
1. Collector Agent
   └─ RSS/API에서 뉴스 수집
   └─ AI 키워드 필터링

2. Translator Agent (해외 뉴스만)
   └─ Google/Papago API로 번역
   └─ 번역 품질 평가

3. Analyzer Agent
   └─ 뉴스 내용 분석
   └─ 10줄 이내 요약 생성
   └─ 중요도 평가

4. Categorizer Agent  
   └─ 10개 카테고리로 분류
   └─ 트렌드 레벨 결정
   └─ 태그 생성

5. Senders
   └─ Telegram: 포맷팅된 메시지 전송
   └─ Email: HTML/텍스트 이메일 전송
```

## 🔧 커스터마이징

### 뉴스 소스 추가
`.env` 파일에 소스 추가:
```bash
DOMESTIC_NEWS_SOURCES=https://new-source.com/rss,...
INTERNATIONAL_NEWS_SOURCES=https://tech-source.com/feed,...
```

### 카테고리 확장
`categorizer_agent.py`의 `categories` 딕셔너리에 새 카테고리 추가

### 텔레그램 커맨드 확장  
`telegram_sender_agent.py`의 `setup_handlers()` 메서드에 새 핸들러 추가

## 🐛 문제 해결

### 일반적인 문제
1. **의존성 오류**: `pip install -r requirements.txt` 재실행
2. **API 키 오류**: `.env` 파일의 API 키 확인
3. **Telegram 연결 오류**: 봇 토큰 및 채팅 ID 확인

### 로그 확인
```bash
# 디버그 모드 실행
LOG_LEVEL=DEBUG python main_news_mcp.py
```

### 테스트
```python
# 테스트 알림 전송
{
  "tool": "send_test_notification",
  "parameters": {"channel": "telegram"}
}
```

## 📁 파일 구조

```
telegram-mcp-server/
├── main_news_mcp.py           # MCP 서버 메인 파일
├── agent_base.py             # 에이전트 기반 클래스
├── collector_agent.py        # 뉴스 수집 에이전트
├── translator_agent.py       # 번역 에이전트
├── analyzer_agent.py         # 분석 에이전트
├── categorizer_agent.py      # 분류 에이전트
├── telegram_sender_agent.py  # 텔레그램 발신 에이전트
├── mail_sender_agent.py      # 이메일 발신 에이전트
├── requirements.txt          # 의존성 목록
├── .env.example             # 환경 변수 예시
├── .gitignore               # Git 무시 파일
└── README.md                # 이 파일
```

## 🔮 향후 개선 사항

- [ ] 데이터베이스 연동 (뉴스 히스토리 저장)
- [ ] 웹 대시보드 개발
- [ ] 더 정교한 NLP 분석 모델 통합
- [ ] 멀티언어 지원 확장
- [ ] 사용자 맞춤형 필터링
- [ ] CI/CD 파이프라인 구축

## 📄 라이선스

MIT License

## 🤝 기여

이슈 리포트 및 PR은 환영합니다!