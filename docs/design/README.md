# Multi-Agent Telegram News Alert MCP Server - Design Document

**Date:** 2026-02-04

## Feature Description

멀티에이전트 기반의 AI 트렌드 뉴스 수집 및 알림 MCP 서버입니다. 각 에이전트가 특정 역할을 맡아 뉴스를 수집, 번역, 분석, 분류하고 텔레그램과 이메일로 알림을 전송합니다.

### Core Features
- 멀티에이전트 아키텍처 기반 뉴스 처리 파이프라인
- 국내외 AI 트렌드 뉴스 자동 수집
- 실시간 번역 및 분석 기능
- 텔레그램 및 이메일 알림 시스템
- 뉴스 카테고리별 분류 및 태깅

## Agent Architecture

### 1. Collector Agent
- **이름**: collector (수집기)
- **기능**: 최신 AI 트렌드 관련 뉴스 수집
- **처리 순서**: 국내 뉴스 우선 수집 → 해외 뉴스 수집
- **주요 소스**:
  - 국내: IT 뉴스 포털, 테크 미디어
  - 해외: TechCrunch, VentureBeat, AI 관련 블로그
- **기술**: RSS 피드, News API, 웹 크롤링

### 2. Translator Agent
- **이름**: translator (번역기)
- **기능**: 해외 뉴스 한국어 번역
- **처리 대상**: Collector가 수집한 해외 뉴스
- **기술**: Google Translate API, Papago API
- **품질 관리**: 번역 결과 검증 및 후처리

### 3. Analyzer Agent
- **이름**: analyzer (분석기)
- **기능**: 뉴스 내용 분석 및 요약 (10줄 이내)
- **분석 항목**: 핵심 내용 추출, 트렌드 중요도 평가
- **출력 형식**: 구조화된 요약문
- **기술**: NLP, GPT 기반 분석

### 4. Categorizer Agent
- **이름**: categorizer (분류기)
- **기능**: 분석된 뉴스 카테고리 분류
- **카테고리**: 머신러닝, 딥러닝, NLP, 컴퓨터비전, 기업 동향 등
- **태깅**: 자동 태그 생성 및 관리
- **기술**: 텍스트 분류 알고리즘

### 5. Telegram-Sender Agent
- **이름**: telegram-sender (텔레그램 발신자)
- **기능**: 최종 뉴스 텔레그램으로 전송
- **전송 형식**: 포맷팅된 메시지, 이미지 첨부
- **대상 관리**: 채팅 ID별 구독 관리
- **기술**: python-telegram-bot 라이브러리

### 6. Mail-Sender Agent
- **이름**: mail-sender (메일 발신자)
- **기능**: 뉴스 이메일로 전송 및 수신자 관리
- **전송 형식**: HTML 이메일 템플릿
- **수신자 관리**: 구독/구독해제, 선호도 설정
- **기술**: SMTP, Jinja2 템플릿

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server Core                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Agent     │  │   Message   │  │  Scheduler  │              │
│  │  Manager    │  │    Queue    │  │   Service   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Collector │───▶│ Translator  │    │   Analyzer  │
│   Agent     │    │   Agent     │    │   Agent     │
└─────────────┘    └─────────────┘    └─────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Categorizer │◀───│ Telegram-   │    │  Mail-Sender │
│   Agent     │    │  Sender     │    │    Agent     │
└─────────────┘    └─────────────┘    └─────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Telegram      │  │    Mail Server  │  │   Database      │
│      Bot        │  │   (SMTP)        │  │   (News Store)  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Data Flow Pipeline

```
News Sources → Collector → Translator → Analyzer → Categorizer → Senders → Users
     ↓              ↓          ↓          ↓            ↓         ↓
  RSS/APIs     Raw News  Translated   Analyzed    Categorized  Formatted
  Crawling     Collection  News      Summary     News       Messages
```

## Implementation Details

### Core Classes

```python
class MultiAgentMCPServer:
    def __init__(self):
        self.agents = {
            'collector': CollectorAgent(),
            'translator': TranslatorAgent(),
            'analyzer': AnalyzerAgent(),
            'categorizer': CategorizerAgent(),
            'telegram-sender': TelegramSenderAgent(),
            'mail-sender': MailSenderAgent()
        }
        self.message_queue = MessageQueue()
        self.scheduler = SchedulerService()

class CollectorAgent(BaseAgent):
    async def collect_news(self) -> List[NewsItem]
    async def collect_domestic_news(self) -> List[NewsItem]
    async def collect_international_news(self) -> List[NewsItem]

class TranslatorAgent(BaseAgent):
    async def translate_news(self, news: NewsItem) -> TranslatedNews

class AnalyzerAgent(BaseAgent):
    async def analyze_news(self, news: NewsItem) -> AnalyzedNews

class CategorizerAgent(BaseAgent):
    async def categorize_news(self, news: AnalyzedNews) -> CategorizedNews

class TelegramSenderAgent(BaseAgent):
    async def send_news_alert(self, news: CategorizedNews, chat_ids: List[int])

class MailSenderAgent(BaseAgent):
    async def send_news_email(self, news: CategorizedNews, recipients: List[str])
```

### Data Models

```python
class NewsItem(BaseModel):
    id: str
    title: str
    content: str
    url: str
    source: str
    published_at: datetime
    language: str
    country: str

class TranslatedNews(BaseModel):
    original: NewsItem
    translated_title: str
    translated_content: str
    translation_confidence: float

class AnalyzedNews(BaseModel):
    news: Union[NewsItem, TranslatedNews]
    summary: str  # 10줄 이내
    key_points: List[str]
    importance_score: float
    ai_relevance: float

class CategorizedNews(BaseModel):
    analyzed_news: AnalyzedNews
    category: str
    tags: List[str]
    trend_level: str  # 'high', 'medium', 'low'
```

### MCP Tool Definitions

```python
NEWS_TOOLS = [
    {
        "name": "start_news_collection",
        "description": "Start news collection process"
    },
    {
        "name": "get_news_summary",
        "description": "Get latest AI trend news summary"
    },
    {
        "name": "subscribe_telegram",
        "description": "Subscribe to Telegram news alerts"
    },
    {
        "name": "subscribe_email",
        "description": "Subscribe to email news alerts"
    },
    {
        "name": "configure_categories",
        "description": "Configure news category preferences"
    }
]
```

## Test Cases

### Unit Tests

1. **CollectorAgent Tests**
   - 국내 뉴스 수집 기능 테스트
   - 해외 뉴스 수집 기능 테스트
   - RSS 피드 파싱 테스트
   - API 장애 상황 에러 핸들링

2. **TranslatorAgent Tests**
   - 번역 품질 검증 테스트
   - 다국어 처리 능력 테스트
   - 번역 API 연동 테스트

3. **AnalyzerAgent Tests**
   - 뉴스 분석 정확성 테스트
   - 요약 길이 제한 테스트
   - 중요도 평가 알고리즘 테스트

4. **CategorizerAgent Tests**
   - 카테고리 분류 정확도 테스트
   - 태그 생성 품질 테스트
   - 새로운 카테고리 학습 능력 테스트

### Integration Tests

1. **End-to-End Pipeline**
   - 수집 → 번역 → 분석 → 분류 → 전송 전체 프로세스
   - 에이전트 간 메시지 전송 테스트
   - 오류 전파 및 복구 테스트

2. **Multi-Agent Coordination**
   - 동시 실행 에이전트 간 충돌 방지
   - 자원 관리 및 스케줄링 테스트
   - 에이전트 실패 시 페일오버 테스트

## Configuration Management

```python
class AgentSettings(BaseSettings):
    # Collector settings
    collection_interval: int = 300  # 5분
    domestic_sources: List[str] = []
    international_sources: List[str] = []
    
    # Translator settings
    translation_api_key: str
    translation_provider: str = "google"  # google, papago
    
    # Analyzer settings
    analysis_model: str = "gpt-4"
    max_summary_lines: int = 10
    
    # Categorizer settings
    categories: List[str] = ["ml", "dl", "nlp", "cv", "enterprise"]
    
    # Sender settings
    telegram_bot_token: str
    smtp_server: str
    smtp_port: int = 587
```

## Security Considerations

- API 키 보안 관리
- 사용자 데이터 암호화
- Rate limiting 구현
- Input validation 및 sanitization
- 에이전트 간 통신 보안

## Performance Optimization

- 비동기 에이전트 실행
- 메시지 큐 병렬 처리
- 캐싱 전략 구현
- 리소스 풀링 관리

## Future Enhancements

- 실시간 뉴스 스트리밍
- 사용자 맞춤형 뉴스 필터링
- AI 기반 예측 분석
- 멀티언어 지원 확장
- 웹 대시보드 추가