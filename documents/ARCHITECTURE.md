# Telegram MCP Server - 프로젝트 아키텍처 및 코드 가이드

이 문서는 `telegram-mcp-server` 프로젝트의 아키텍처, 주요 소스 코드의 역할, 그리고 데이터 흐름을 설명합니다.

## 1. 프로젝트 개요

이 프로젝트는 **Model Context Protocol (MCP)**를 기반으로 작동하는 뉴스 수집 및 알림 에이전트 시스템입니다.
다양한 소스(RSS, 웹)에서 AI 관련 뉴스를 수집하고, 번역(Google/Papago), 요약(Gemini/OpenAI), 분류 과정을 거쳐 텔레그램 및 이메일로 사용자에게 전달합니다.

## 2. 시스템 아키텍처 (Architecture)

이 시스템은 **Pub/Sub (Publisher-Subscriber) 패턴**을 사용하는 `MessageBroker`를 중심으로 느슨하게 결합된 에이전트들로 구성되어 있습니다.

```mermaid
graph TD
    User[사용자/MCP Client] -->|start_news_collection| Main[Main Server (main_news_mcp.py)]
    Main -->|collect_now| Broker[Message Broker (agent_base.py)]
    
    subgraph Agents
        Collector[Collector Agent]
        Translator[Translator Agent]
        Analyzer[Analyzer Agent]
        Categorizer[Categorizer Agent]
        Telegram[Telegram Sender]
        Mail[Mail Sender]
    end

    Broker -->|trigger| Collector
    Collector -->|raw news| Broker
    Broker -->|route| Translator
    Translator -->|translated| Broker
    Broker -->|route| Analyzer
    Analyzer -->|summary| Broker
    Broker -->|route| Categorizer
    Categorizer -->|categorized| Broker
    Broker -->|route| Telegram
    Broker -->|route| Mail
    
    Telegram -->|Message| User
    Mail -->|Email| User
```

---

## 3. 소스 코드 별 상세 설명

### 3.1. 핵심 프레임워크 (Core Framework)

#### `agent_base.py`
- **역할**: 시스템의 중추 신경망 역할.
- **주요 클래스**:
    - `MessageBroker`: 에이전트 간의 메시지 전달을 담당하는 싱글톤 브로커입니다. 직접적인 함수 호출 대신 메시지 큐를 통해 비동기 통신을 중개합니다.
    - `BaseAgent`: 모든 에이전트의 부모 클래스입니다. 메시지 수신(`receive_message`) 및 발신(`send_message`) 공통 로직을 포함합니다.
    - **데이터 모델**: `NewsItem`, `TranslatedNews`, `AnalyzedNews`, `CategorizedNews` 등 데이터 흐름에 따라 확장되는 Pydantic 모델을 정의합니다.

#### `main_news_mcp.py`
- **역할**: 애플리케이션의 진입점(Entry Point)이자 MCP 서버입니다.
- **주요 기능**:
    - 환경 변수 로드 및 설정 관리 (`NewsMCPSettings`).
    - 모든 에이전트 인스턴스 초기화 및 백그라운드 실행 (`start_agents`).
    - MCP 툴 정의 (`start_news_collection`, `subscribe_telegram` 등).
    - MCP 클라이언트(Claude 등)로부터 명령을 받아 브로커에 전달.

---

### 3.2. 기능성 에이전트 (Functional Agents)

#### `collector_agent.py`
- **역할**: 뉴스 원문 수집.
- **흐름**:
    1. `collect_now` 메시지 수신 또는 주기적 실행.
    2. RSS 피드 및 웹페이지 크롤링 (국내/해외 소스).
    3. 중복 뉴스 제거 및 AI 관련성 1차 필터링.
    4. **Output**: 해외 뉴스는 `Translator`로, 국내 뉴스는 `Analyzer`로 메시지 전송.

#### `translator_agent.py`
- **역할**: 다국어 뉴스 번역.
- **흐름**:
    1. 영어/외국어 뉴스 수신.
    2. Google Translate API (또는 Papago)를 호출하여 제목/본문 번역.
    3. **Output**: 번역된 데이터를 `Analyzer`로 전송.

#### `analyzer_agent.py`
- **역할**: 뉴스 내용 분석 및 요약 (LLM 사용).
- **흐름**:
    1. 뉴스 원문(또는 번역본) 수신.
    2. **Google Gemini (google-genai)** 또는 OpenAI API를 호출.
    3. 뉴스 요약(10줄 이내), 핵심 포인트 추출, 중요도 점수 산정.
    4. **Output**: 분석 결과를 `Categorizer`로 전송.

#### `categorizer_agent.py`
- **역할**: 뉴스 카테고리 분류 및 트렌드 분석.
- **흐름**:
    1. 분석된 뉴스 수신.
    2. 키워드 기반 가중치 알고리즘을 통해 카테고리(ML, NLP, Robotics 등) 결정.
    3. 중요도와 AI 관련성을 종합하여 트렌드 레벨(High, Medium, Low) 판별.
    4. **Output**: 최종 가공된 데이터를 `TelegramSender`, `MailSender`로 브로드캐스트.

---

### 3.3. 발신 에이전트 (Sender Agents)

#### `telegram_sender_agent.py`
- **역할**: 텔레그램 봇을 통한 알림 발송.
- **주요 기능**:
    - 사용자 구독 관리 (Chat ID).
    - 마크다운 포맷으로 뉴스 메시지 가공.
    - 긴 메시지 자동 분할 전송.

#### `mail_sender_agent.py`
- **역할**: 이메일 뉴스레터 발송.
- **주요 기능**:
    - SMTP 서버 연동 (Gmail 등).
    - HTML 템플릿을 사용한 이메일 본문 생성.

---

### 3.4. 유틸리티

#### `trigger_news_cycle.py`
- **역할**: 개발 및 테스트용 트리거 스크립트.
- **기능**: MCP 서버를 서브 프로세스로 실행하고, `start_news_collection` 툴을 강제로 호출하여 전체 파이프라인이 1회 동작하도록 만듭니다. 동작 과정을 로그로 보여주고 종료합니다.

## 4. 데이터 흐름 요약 (Data Flow)

1. **Trigger**: `main_news_mcp.py`가 MCP 요청을 받음 -> `Collector`에게 수집 명령.
2. **Collection**: `Collector`가 URL에서 뉴스 수집 -> `NewsItem` 생성.
3. **Branching**:
    - 한국어 뉴스 -> `Analyzer`로 이동.
    - 외국어 뉴스 -> `Translator` -> `TranslatedNews` 생성 -> `Analyzer`로 이동.
4. **Analysis**: `Analyzer`가 LLM으로 요약 -> `AnalyzedNews` 생성 -> `Categorizer`로 이동.
5. **Categorization**: `Categorizer`가 분류 -> `CategorizedNews` 생성 -> `Sender`들로 이동.
6. **Delivery**:
    - `TelegramSender` -> 텔레그램 메시지 전송.
    - `MailSender` -> 이메일 전송.

## 5. 의존성 및 설정

- **설정 파일**: `.env` (API 키 및 기능 On/Off 설정)
- **주요 라이브러리**:
    - `mcp`: MCP 프로토콜 구현.
    - `google-genai`: Gemini 모델 연동.
    - `python-telegram-bot`: 텔레그램 봇 연동.
    - `aiohttp`: 비동기 웹 요청.
    - `feedparser`: RSS 파싱.
