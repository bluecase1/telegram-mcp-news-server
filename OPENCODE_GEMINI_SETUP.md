# OpenCode Google Gemini API 인증 설정 가이드

## 1. Google Gemini API 키 발급

1. **Google AI Studio 접속**: https://aistudio.google.com/
2. **Google 계정으로 로그인**
3. **API 키 생성**:
   - 왼쪽 메뉴에서 "Get API Key" 선택
   - "Create API Key" 클릭
   - 새 프로젝트 생성 또는 기존 프로젝트 선택
   - 생성된 API 키 복사 (예: `AIzaSy...`)

## 2. 환경 변수 설정

### Windows (CMD):
```cmd
set GOOGLE_AI_API_KEY=AIzaSy..._your_actual_api_key_here
```

### Windows (PowerShell):
```powershell
$env:GOOGLE_AI_API_KEY="AIzaSy..._your_actual_api_key_here"
```

### 영구 설정 (Windows 시스템 환경 변수):
1. Win + R → `sysdm.cpl`
2. 고급 탭 → 환경 변수
3. 새로 만들기:
   - 변수 이름: `GOOGLE_AI_API_KEY`
   - 변수 값: 발급받은 API 키

## 3. OpenCode 인증

1. **인증 명령어 실행**:
   ```bash
   opencode auth login
   ```

2. **프로바이더 선택**:
   - 목록에서 "Google" 선택
   - Enter 키로 확인

3. **API 키 입력**:
   - 발급받은 Google Gemini API 키 입력
   - 완료되면 인증 성공 메시지 확인

## 4. 인증 확인

```bash
opencode auth list
```

## 5. 현재 상태

현재 OpenCode는 Google을 포함한 여러 AI 프로바이더를 지원합니다:
- OpenCode Zen (추천)
- Anthropic
- GitHub Copilot  
- OpenAI
- **Google** ← Gemini API 사용 가능
- Vertex
- Azure Cognitive Services
- Vercel AI Gateway

## 주의사항

- API 키는 절대 공개적으로 공유하지 마세요
- 환경 변수 설정 후 터미널을 재시작해야 적용될 수 있습니다
- Google AI Studio에서 발급받은 키만 사용 가능합니다