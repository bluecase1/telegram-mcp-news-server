import asyncio
import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv
from pydantic import BaseModel
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    TextContent,
    Tool,
)

# 에이전트 임포트
from agent_base import message_broker, AgentMessage
from collector_agent import collector_agent
from translator_agent import translator_agent
from analyzer_agent import analyzer_agent
from categorizer_agent import categorizer_agent
from telegram_sender_agent import telegram_sender_agent
from mail_sender_agent import mail_sender_agent

# 환경 변수 로드
load_dotenv()


class NewsMCPSettings(BaseModel):
    # 일반 설정
    log_level: str = "INFO"
    collection_interval: int = 300  # 5분
    
    # 뉴스 소스 설정
    enable_domestic_news: bool = True
    enable_international_news: bool = True
    
    # 번역 설정
    enable_translation: bool = True
    translation_provider: str = "google"  # google, papago
    
    # 분석 설정
    enable_analysis: bool = True
    analysis_model: str = "simple"  # simple, openai
    
    # 전송 설정
    enable_telegram: bool = True
    enable_email: bool = True
    
    # 텔레그램 설정
    telegram_bot_token: str = ""
    allowed_chat_ids: str = ""
    
    # 이메일 설정
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    
    # API 키 설정
    google_translate_api_key: str = ""
    openai_api_key: str = ""
    papago_client_id: str = ""
    papago_client_secret: str = ""


class NewsAlertMCPServer:
    """뉴스 알림 MCP 서버"""
    
    def __init__(self, settings: NewsMCPSettings):
        self.settings = settings
        self.server = Server("news-alert-mcp-server")
        self.agents_started = False
        self._setup_handlers()
    
    def _setup_handlers(self):
        """MCP 핸들러 설정"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return [
                Tool(
                    name="start_news_collection",
                    description="Start the news collection process",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "force": {
                                "type": "boolean",
                                "description": "Force immediate collection",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="get_news_summary",
                    description="Get latest AI trend news summary",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of news items to return",
                                "default": 10
                            },
                            "category": {
                                "type": "string",
                                "description": "Filter by category"
                            },
                            "trend_level": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "Filter by trend level"
                            }
                        }
                    }
                ),
                Tool(
                    name="subscribe_telegram",
                    description="Subscribe to Telegram news alerts",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chat_id": {
                                "type": "integer",
                                "description": "Telegram chat ID"
                            }
                        },
                        "required": ["chat_id"]
                    }
                ),
                Tool(
                    name="subscribe_email",
                    description="Subscribe to email news alerts",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "email": {
                                "type": "string",
                                "format": "email",
                                "description": "Email address"
                            }
                        },
                        "required": ["email"]
                    }
                ),
                Tool(
                    name="configure_news_sources",
                    description="Configure news collection sources",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "enable_domestic": {
                                "type": "boolean",
                                "description": "Enable domestic news collection"
                            },
                            "enable_international": {
                                "type": "boolean", 
                                "description": "Enable international news collection"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_agent_status",
                    description="Get status of all agents",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="send_test_notification",
                    description="Send test notification to configured channels",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "channel": {
                                "type": "string",
                                "enum": ["telegram", "email", "all"],
                                "description": "Channel to send test notification",
                                "default": "all"
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            try:
                if not self.agents_started:
                    await self.start_agents()
                
                if name == "start_news_collection":
                    return await self.start_news_collection(arguments)
                elif name == "get_news_summary":
                    return await self.get_news_summary(arguments)
                elif name == "subscribe_telegram":
                    return await self.subscribe_telegram(arguments)
                elif name == "subscribe_email":
                    return await self.subscribe_email(arguments)
                elif name == "configure_news_sources":
                    return await self.configure_news_sources(arguments)
                elif name == "get_agent_status":
                    return await self.get_agent_status(arguments)
                elif name == "send_test_notification":
                    return await self.send_test_notification(arguments)
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                        isError=True
                    )
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )
    
    async def start_agents(self):
        """모든 에이전트 시작"""
        try:
            # Collector Agent 시작
            asyncio.create_task(collector_agent.start())
            await asyncio.sleep(0.1)
            
            # Translator Agent 시작 (번역 활성화된 경우)
            if self.settings.enable_translation:
                asyncio.create_task(translator_agent.start())
                await asyncio.sleep(0.1)
            
            # Analyzer Agent 시작
            asyncio.create_task(analyzer_agent.start())
            await asyncio.sleep(0.1)
            
            # Categorizer Agent 시작
            asyncio.create_task(categorizer_agent.start())
            await asyncio.sleep(0.1)
            
            # Telegram Sender Agent 시작 (텔레그램 활성화된 경우)
            if self.settings.enable_telegram and telegram_sender_agent:
                asyncio.create_task(telegram_sender_agent.start())
                await asyncio.sleep(0.1)
            
            # Mail Sender Agent 시작 (이메일 활성화된 경우)
            if self.settings.enable_email:
                asyncio.create_task(mail_sender_agent.start())
                await asyncio.sleep(0.1)
            
            self.agents_started = True
            print("All agents started successfully")
            
        except Exception as e:
            print(f"Error starting agents: {e}")
            raise
    
    async def start_news_collection(self, arguments: Dict[str, Any]) -> CallToolResult:
        """뉴스 수집 시작"""
        try:
            force = arguments.get("force", False)
            
            if force:
                # 즉시 수집 요청
                await message_broker.send_message(
                    AgentMessage(
                        sender="mcp_server",
                        receiver="collector",
                        message_type="collect_now",
                        data={}
                    )
                )
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"News collection {'forced ' if force else ''}started. Collection interval: {self.settings.collection_interval} seconds"
                )]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to start collection: {str(e)}")],
                isError=True
            )
    
    async def get_news_summary(self, arguments: Dict[str, Any]) -> CallToolResult:
        """최신 뉴스 요약"""
        try:
            # 현재는 간단한 상태 메시지 반환
            # 실제로는 데이터베이스에서 최신 뉴스 가져오기
            limit = arguments.get("limit", 10)
            category = arguments.get("category")
            trend_level = arguments.get("trend_level")
            
            summary_text = f"News Summary Request:\n"
            summary_text += f"- Limit: {limit}\n"
            if category:
                summary_text += f"- Category: {category}\n"
            if trend_level:
                summary_text += f"- Trend Level: {trend_level}\n"
            summary_text += "\nNews collection is running in the background. News will be sent to your subscribed channels."
            
            return CallToolResult(
                content=[TextContent(type="text", text=summary_text)]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to get news summary: {str(e)}")],
                isError=True
            )
    
    async def subscribe_telegram(self, arguments: Dict[str, Any]) -> CallToolResult:
        """텔레그램 구독"""
        try:
            chat_id = arguments["chat_id"]
            
            if telegram_sender_agent:
                success = await telegram_sender_agent.add_subscriber(chat_id)
                if success:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Successfully subscribed chat {chat_id} to Telegram notifications")]
                    )
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Chat {chat_id} is already subscribed")],
                        isError=True
                    )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text="Telegram functionality is not available")],
                    isError=True
                )
                
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to subscribe to Telegram: {str(e)}")],
                isError=True
            )
    
    async def subscribe_email(self, arguments: Dict[str, Any]) -> CallToolResult:
        """이메일 구독"""
        try:
            email = arguments["email"]
            
            success = await mail_sender_agent.add_recipient(email)
            if success:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Successfully subscribed {email} to email notifications")]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Email {email} is already subscribed")],
                    isError=True
                )
                
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to subscribe to email: {str(e)}")],
                isError=True
            )
    
    async def configure_news_sources(self, arguments: Dict[str, Any]) -> CallToolResult:
        """뉴스 소스 설정"""
        try:
            enable_domestic = arguments.get("enable_domestic", self.settings.enable_domestic_news)
            enable_international = arguments.get("enable_international", self.settings.enable_international_news)
            
            # 설정 업데이트
            self.settings.enable_domestic_news = enable_domestic
            self.settings.enable_international_news = enable_international
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"News sources configured:\n- Domestic news: {enable_domestic}\n- International news: {enable_international}"
                )]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to configure news sources: {str(e)}")],
                isError=True
            )
    
    async def get_agent_status(self, arguments: Dict[str, Any]) -> CallToolResult:
        """에이전트 상태 조회"""
        try:
            agents_status = []
            
            # 각 에이전트 상태 확인
            agents = [
                ("collector", collector_agent),
                ("translator", translator_agent),
                ("analyzer", analyzer_agent),
                ("categorizer", categorizer_agent),
                ("telegram-sender", telegram_sender_agent),
                ("mail-sender", mail_sender_agent)
            ]
            
            for name, agent in agents:
                if agent:
                    status = "running" if agent.running else "stopped"
                    agents_status.append(f"- {name}: {status}")
            
            status_text = "Agent Status:\n" + "\n".join(agents_status)
            
            return CallToolResult(
                content=[TextContent(type="text", text=status_text)]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to get agent status: {str(e)}")],
                isError=True
            )
    
    async def send_test_notification(self, arguments: Dict[str, Any]) -> CallToolResult:
        """테스트 알림 전송"""
        try:
            channel = arguments.get("channel", "all")
            
            results = []
            
            if channel in ["telegram", "all"] and telegram_sender_agent:
                try:
                    # 텔레그램 테스트 메시지 전송
                    test_message = "🧪 AI 뉴스 알림 테스트\n\n이것은 테스트 메시지입니다. 서비스가 정상적으로 동작하고 있습니다."
                    
                    # 테스트를 위해 모든 구독자에게 전송
                    sent_count = await telegram_sender_agent.send_to_subscribers(test_message)
                    results.append(f"Telegram: Sent to {sent_count} subscribers")
                    
                except Exception as e:
                    results.append(f"Telegram: Failed - {str(e)}")
            
            if channel in ["email", "all"]:
                try:
                    # 이메일 테스트 전송
                    success = await mail_sender_agent.send_test_email()
                    results.append(f"Email: {'Sent successfully' if success else 'Failed'}")
                    
                except Exception as e:
                    results.append(f"Email: Failed - {str(e)}")
            
            if not results:
                results.append("No channels configured for testing")
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="Test Notification Results:\n" + "\n".join(results)
                )]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to send test notification: {str(e)}")],
                isError=True
            )


async def main():
    try:
        # 설정 로드
        settings = NewsMCPSettings(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            collection_interval=int(os.getenv("COLLECTION_INTERVAL", "300")),
            enable_domestic_news=os.getenv("ENABLE_DOMESTIC_NEWS", "true").lower() == "true",
            enable_international_news=os.getenv("ENABLE_INTERNATIONAL_NEWS", "true").lower() == "true",
            enable_translation=os.getenv("ENABLE_TRANSLATION", "true").lower() == "true",
            translation_provider=os.getenv("TRANSLATION_PROVIDER", "google"),
            enable_analysis=os.getenv("ENABLE_ANALYSIS", "true").lower() == "true",
            analysis_model=os.getenv("ANALYSIS_MODEL", "simple"),
            enable_telegram=os.getenv("ENABLE_TELEGRAM", "true").lower() == "true",
            enable_email=os.getenv("ENABLE_EMAIL", "true").lower() == "true",
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            allowed_chat_ids=os.getenv("ALLOWED_CHAT_IDS", ""),
            smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            google_translate_api_key=os.getenv("GOOGLE_TRANSLATE_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            papago_client_id=os.getenv("PAPAGO_CLIENT_ID", ""),
            papago_client_secret=os.getenv("PAPAGO_CLIENT_SECRET", "")
        )
        
        # 필수 설정 확인
        if settings.enable_telegram and not settings.telegram_bot_token:
            print("Warning: Telegram enabled but no bot token provided", file=sys.stderr)
        
        if settings.enable_email and not (settings.smtp_username and settings.smtp_password):
            print("Warning: Email enabled but no SMTP credentials provided", file=sys.stderr)
        
        # MCP 서버 생성
        mcp_server = NewsAlertMCPServer(settings)
        
        # MCP 서버 실행
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="news-alert-mcp-server",
                    server_version="1.0.0",
                    capabilities=mcp_server.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None
                    )
                )
            )
    
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())