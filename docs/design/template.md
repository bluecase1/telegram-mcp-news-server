1. 🎯 프로젝트 비전 (The Vibe)
핵심 목적: 이 기능을 왜 만드는가? (예: "매일 아침 수동으로 뉴스를 찾아보는 시간을 아끼기 위해")

사용자 시나리오: "사용자가 특정 키워드를 입력하면, AI가 뉴스를 긁어와 요약하고 텔레그램으로 쏜다."

2. 🛠 기술 스택 & 제약 사항 (Specs & Constraints)
Engine: Gemini 2.0 Flash (OpenCode 연동)

Language: Python 3.10+

MCP Servers: telegram-mcp, web-scraper-mcp

Constraints: 그래픽 카드 없음(CPU 기반), 외부 API 호출 시 에러 핸들링 필수.

3. 📐 시스템 구조 (Architecture)
입력(Input): 텔레그램 명령어 또는 스케줄러.

처리(Process):

News Search (Tool A)

Content Scraping (Tool B)

LLM Summarization

출력(Output): 텔레그램 메시지 발송.

4. 🧰 도구 정의 (MCP Tool Definitions)
에이전트가 사용할 도구의 인터페이스를 미리 정의합니다.

fetch_news(keyword): 특정 키워드로 뉴스 URL 목록 반환.

send_telegram(message): 요약된 내용을 지정된 봇으로 전송.

5. ✅ 테스트 케이스 (Verification)
[ ] 뉴스 검색 결과가 0건일 때 "검색 결과 없음" 메시지가 가는가?

[ ] 텔레그램 API 토큰이 잘못되었을 때 적절한 에러 로그를 남기는가?

[ ] 본문이 너무 길 때 LLM이 잘 요약해주는가?

6. 📝 작업 일지 (Vibe Logs)
2026-02-04: 프로젝트 생성 및 설계 문서 작성 완료.

추가 예정: 구현 과정에서의 특이사항 기록.