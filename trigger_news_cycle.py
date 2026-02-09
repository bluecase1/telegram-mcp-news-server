import asyncio
import sys
import os
import time
# Set encoding to utf-8 for stdout/stderr to avoid cp949 errors on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def run_news_cycle():
    """
    MCP 서버를 실행하고 뉴스 수집을 1회 트리거한 뒤,
    작업이 완료될 때까지 대기하고 종료하는 스크립트
    """
    # 환경 변수 설정
    env = os.environ.copy()
    
    # 서버 스크립트 경로 (현재 디렉토리 기준)
    current_dir = os.getcwd()
    server_script = os.path.join(current_dir, "main_news_mcp.py")
    
    print(f"🚀 MCP 서버를 시작합니다... (Script: {server_script})")
    
    # 서버 파라미터 설정
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=env
    )

    # stdio_client를 통해 서버와 연결 (stderr는 현재 프로세스의 stderr로 출력됨)
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. 초기화
            await session.initialize()
            print("✅ MCP 서버에 연결되었습니다.")
            
            # 2. 뉴스 수집 툴 호출 (강제 실행)
            print("\n📰 뉴스 수집 및 분석 요청 중...")
            try:
                result = await session.call_tool("start_news_collection", arguments={"force": True})
                
                # 툴 실행 결과 출력
                print("✅ 요청 완료. 서버 응답:")
                for content in result.content:
                    if content.type == "text":
                        print(f"   > {content.text}")
            except Exception as e:
                print(f"❌ 툴 호출 중 오류 발생: {e}")
                return

            # 3. 작업 완료 대기 (로그 모니터링을 위해 대기)
            # 서버가 백그라운드에서 동작하므로 충분한 시간을 대기합니다.
            # 실제 운영 환경에서는 작업 상태를 폴링하거나 이벤트를 수신하는 것이 좋습니다.
            wait_seconds = 60
            print(f"\n⏳ 백그라운드 작업 처리 중... (약 {wait_seconds}초 대기)")
            print("   (아래에 서버 로그가 표시됩니다)\n")
            print("=" * 60)
            
            for i in range(wait_seconds):
                if i % 10 == 0 and i > 0:
                    print(f"... {i}초 경과")
                await asyncio.sleep(1)
            
            print("=" * 60)
            print("\n✅ 대기 시간 종료. 프로그램을 종료합니다.")

if __name__ == "__main__":
    try:
        asyncio.run(run_news_cycle())
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단되었습니다.")
