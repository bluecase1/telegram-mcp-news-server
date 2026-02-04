import asyncio
import json
from typing import Dict, Any, List, Optional
import logging
import os

from agent_base import BaseAgent, AgentMessage, CategorizedNews, TranslatedNews, NewsItem, message_broker

try:
    import telegram
    from telegram import Bot, Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("Warning: python-telegram-bot not installed. Telegram functionality will be disabled.")


class TelegramSenderAgent(BaseAgent):
    """텔레그램 뉴스 발신 에이전트"""
    
    def __init__(self):
        super().__init__("telegram-sender")
        
        # 텔레그램 설정
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.allowed_chat_ids = self.parse_chat_ids(os.getenv("ALLOWED_CHAT_IDS", ""))
        
        # 텔레그램 봇 인스턴스
        self.bot = None
        self.application = None
        
        # 전송 설정
        self.max_message_length = 4096  # 텔레그램 메시지 제한
        self.enable_markdown = True
        
        # 구독자 관리
        self.subscribers = set()  # 메모리에 저장 (실제로는 DB에 저장)
        self.load_subscribers()
        
        # 통계
        self.send_count = 0
        self.error_count = 0
        
        if TELEGRAM_AVAILABLE and self.bot_token:
            self.initialize_telegram()
    
    def parse_chat_ids(self, chat_ids_str: str) -> List[int]:
        """채팅 ID 파싱"""
        try:
            return [int(x.strip()) for x in chat_ids_str.split(",") if x.strip()]
        except:
            return []
    
    def load_subscribers(self):
        """구독자 목록 로드"""
        try:
            # 실제로는 파일이나 DB에서 로드
            self.subscribers.update(self.allowed_chat_ids)
            self.logger.info(f"Loaded {len(self.subscribers)} subscribers")
        except Exception as e:
            self.logger.error(f"Error loading subscribers: {e}")
    
    def initialize_telegram(self):
        """텔레그램 초기화"""
        try:
            self.bot = Bot(token=self.bot_token)
            self.application = Application.builder().token(self.bot_token).build()
            
            # 핸들러 등록
            self.setup_handlers()
            
            self.logger.info("Telegram bot initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram bot: {e}")
    
    def setup_handlers(self):
        """텔레그램 핸들러 설정"""
        if not self.application:
            return
        
        # 커맨드 핸들러
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("help", self.handle_help))
        self.application.add_handler(CommandHandler("subscribe", self.handle_subscribe))
        self.application.add_handler(CommandHandler("unsubscribe", self.handle_unsubscribe))
        self.application.add_handler(CommandHandler("status", self.handle_status))
        
        # 메시지 핸들러
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def run(self):
        """에이전트 메인 실행 로직"""
        if not TELEGRAM_AVAILABLE:
            self.logger.warning("Telegram functionality disabled due to missing dependencies")
            return
        
        if not self.bot_token:
            self.logger.warning("Telegram bot token not configured")
            return
        
        # 텔레그램 봇 실행
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.logger.info("Telegram bot started polling")
            
            # 메시지 처리 루프
            while self.running:
                try:
                    # 메시지 처리
                    message = await self.receive_message()
                    if message:
                        await self.process_message(message)
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"Error in telegram sender agent: {e}")
                    await asyncio.sleep(5)
        
        except Exception as e:
            self.logger.error(f"Failed to start Telegram bot: {e}")
    
    async def stop(self):
        """에이전트 중지"""
        await super().stop()
        
        if self.application:
            try:
                await self.application.stop()
                await self.application.shutdown()
                self.logger.info("Telegram bot stopped")
            except Exception as e:
                self.logger.error(f"Error stopping Telegram bot: {e}")
    
    async def process_message(self, message: AgentMessage):
        """수신된 메시지 처리"""
        if message.message_type == "send_news":
            await self.send_news_message(message)
        elif message.message_type == "get_subscribers":
            await self.send_subscribers_info(message.sender)
        elif message.message_type == "add_subscriber":
            await self.add_subscriber(message.data.get("chat_id"))
        elif message.message_type == "remove_subscriber":
            await self.remove_subscriber(message.data.get("chat_id"))
    
    async def send_news_message(self, message: AgentMessage):
        """뉴스 메시지 전송"""
        try:
            categorized_news_data = message.data["categorized_news"]
            categorized_news = CategorizedNews(**categorized_news_data)
            
            # 포맷팅된 메시지 생성
            formatted_message = self.format_news_message(categorized_news)
            
            # 구독자에게 전송
            sent_count = await self.send_to_subscribers(formatted_message)
            
            self.send_count += sent_count
            self.logger.info(f"Sent news to {sent_count} subscribers")
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error sending news message: {e}")
    
    def format_news_message(self, categorized_news: CategorizedNews) -> str:
        """뉴스 메시지 포맷팅"""
        analyzed_news = categorized_news.analyzed_news
        news = analyzed_news.news
        
        # 제목
        if isinstance(news, TranslatedNews):
            title = news.translated_title
        else:
            title = news.title
        
        # 요약
        summary = analyzed_news.summary
        
        # 메시지 구성
        message_parts = [
            f"🤖 *AI 뉴스 알림*",
            f"",
            f"📰 *제목*: {title}",
            f"🏷️ 카테고리: {categorized_news.category}",
            f"📈 트렌드 레벨: {self.get_trend_emoji(categorized_news.trend_level)} {categorized_news.trend_level.upper()}",
            f"",
            f"📋 *요약*:",
            f"{summary}",
        ]
        
        # 키 포인트 추가
        if analyzed_news.key_points:
            message_parts.append("")
            message_parts.append("🔑 *주요 포인트*:")
            for i, point in enumerate(analyzed_news.key_points[:3], 1):
                message_parts.append(f"{i}. {point}")
        
        # 태그 추가
        if categorized_news.tags:
            message_parts.append("")
            message_parts.append(f"🏷️ 태그: {', '.join(categorized_news.tags[:5])}")
        
        # 링크 추가
        message_parts.append("")
        message_parts.append(f"🔗 [원문 기사]({news.url})")
        message_parts.append("")
        message_parts.append(f"📊 중요도: {analyzed_news.importance_score:.2f} | AI 관련성: {analyzed_news.ai_relevance:.2f}")
        message_parts.append("")
        message_parts.append("📤 구독 해지: /unsubscribe")
        
        return "\n".join(message_parts)
    
    def get_trend_emoji(self, trend_level: str) -> str:
        """트렌드 레벨 이모지"""
        emoji_map = {
            "high": "🔥",
            "medium": "📈", 
            "low": "📉"
        }
        return emoji_map.get(trend_level, "📊")
    
    async def send_to_subscribers(self, message: str) -> int:
        """구독자에게 메시지 전송"""
        if not self.bot:
            self.logger.error("Telegram bot not initialized")
            return 0
        
        sent_count = 0
        
        for chat_id in self.subscribers:
            try:
                # 메시지 길이 확인 및 분할
                if len(message) > self.max_message_length:
                    messages = self.split_message(message)
                    for msg in messages:
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=msg,
                            parse_mode="Markdown" if self.enable_markdown else None,
                            disable_web_page_preview=False
                        )
                else:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="Markdown" if self.enable_markdown else None,
                        disable_web_page_preview=False
                    )
                
                sent_count += 1
                
                # 전송 간격 (Rate limiting)
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Failed to send to {chat_id}: {e}")
        
        return sent_count
    
    def split_message(self, message: str) -> List[str]:
        """긴 메시지 분할"""
        if len(message) <= self.max_message_length:
            return [message]
        
        # 단순 분할 (더 정교한 분할 가능)
        messages = []
        current_message = ""
        
        lines = message.split('\n')
        for line in lines:
            if len(current_message + line + '\n') > self.max_message_length:
                if current_message:
                    messages.append(current_message.rstrip())
                current_message = line + '\n'
            else:
                current_message += line + '\n'
        
        if current_message:
            messages.append(current_message.rstrip())
        
        return messages
    
    # 텔레그램 핸들러들
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start 핸들러"""
        chat_id = update.effective_chat.id
        
        if self.is_allowed_chat(chat_id):
            await self.add_subscriber(chat_id)
            await update.message.reply_text(
                "🤖 AI 뉴스 알림 봇에 오신 것을 환영합니다!\n"
                "이제부터 AI 트렌드 뉴스를 받으실 수 있습니다.\n\n"
                "📋 명령어:\n"
                "/help - 도움말\n"
                "/subscribe - 뉴스 구독\n"
                "/unsubscribe - 구독 해지\n"
                "/status - 구독 상태"
            )
        else:
            await update.message.reply_text("⚠️ 접근 권한이 없습니다.")
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/help 핸들러"""
        help_text = """
🤖 *AI 뉴스 알림 봇 도움말*

📋 *명령어:*
/start - 봇 시작 및 정보
/subscribe - AI 뉴스 구독
/unsubscribe - 구독 해지
/status - 구독 상태 확인
/help - 이 도움말

📰 *기능:*
• 최신 AI 트렌드 뉴스 자동 수집
• 국내외 뉴스 번역 및 분석
• 카테고리별 뉴스 분류
• 실시간 알림 전송

🏷️ *카테고리:*
머신러닝, 딥러닝, NLP, 컴퓨터비전, 생성 AI 등

📞 *문의:*
문제가 있으시면 관리자에게 문의하세요.
        """
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def handle_subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/subscribe 핸들러"""
        chat_id = update.effective_chat.id
        
        if self.is_allowed_chat(chat_id):
            if await self.add_subscriber(chat_id):
                await update.message.reply_text("✅ AI 뉴스 구독이 시작되었습니다!")
            else:
                await update.message.reply_text("⚠️ 이미 구독 중입니다.")
        else:
            await update.message.reply_text("⚠️ 접근 권한이 없습니다.")
    
    async def handle_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/unsubscribe 핸들러"""
        chat_id = update.effective_chat.id
        
        if await self.remove_subscriber(chat_id):
            await update.message.reply_text("✅ AI 뉴스 구독이 해지되었습니다.")
        else:
            await update.message.reply_text("⚠️ 구독 중이 아닙니다.")
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/status 핸들러"""
        chat_id = update.effective_chat.id
        is_subscribed = chat_id in self.subscribers
        
        status_text = f"""
📊 *구독 상태*

👤 채팅 ID: `{chat_id}`
📱 구독 상태: {'✅ 구독 중' if is_subscribed else '❌ 미구독'}
📧 전체 구독자: {len(self.subscribers)}명
📨 전송된 뉴스: {self.send_count}건
❌ 전송 실패: {self.error_count}건
        """
        
        await update.message.reply_text(status_text, parse_mode="Markdown")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """일반 메시지 핸들러"""
        chat_id = update.effective_chat.id
        text = update.message.text
        
        self.logger.info(f"Received message from {chat_id}: {text}")
        
        # 간단한 응답
        if text.lower() in ["hi", "hello", "안녕", "안녕하세요"]:
            await update.message.reply_text(
                "안녕하세요! AI 뉴스 알림 봇입니다.\n"
                "도움이 필요하시면 /help를 입력해주세요."
            )
    
    def is_allowed_chat(self, chat_id: int) -> bool:
        """허용된 채팅 ID인지 확인"""
        if not self.allowed_chat_ids:
            return True  # 허용 목록이 없으면 모두 허용
        return chat_id in self.allowed_chat_ids
    
    async def add_subscriber(self, chat_id: int) -> bool:
        """구독자 추가"""
        if chat_id not in self.subscribers:
            self.subscribers.add(chat_id)
            self.save_subscribers()
            self.logger.info(f"Added subscriber: {chat_id}")
            return True
        return False
    
    async def remove_subscriber(self, chat_id: int) -> bool:
        """구독자 제거"""
        if chat_id in self.subscribers:
            self.subscribers.remove(chat_id)
            self.save_subscribers()
            self.logger.info(f"Removed subscriber: {chat_id}")
            return True
        return False
    
    def save_subscribers(self):
        """구독자 목록 저장"""
        try:
            # 실제로는 파일이나 DB에 저장
            with open("subscribers.json", "w") as f:
                json.dump(list(self.subscribers), f)
        except Exception as e:
            self.logger.error(f"Error saving subscribers: {e}")
    
    async def send_subscribers_info(self, requester: str):
        """구독자 정보 전송"""
        await self.send_message(requester, "subscribers_info", {
            "count": len(self.subscribers),
            "subscribers": list(self.subscribers),
            "send_count": self.send_count,
            "error_count": self.error_count
        })


# TelegramSenderAgent 인스턴스 생성 및 등록
if TELEGRAM_AVAILABLE:
    telegram_sender_agent = TelegramSenderAgent()
    message_broker.register_agent(telegram_sender_agent)
else:
    telegram_sender_agent = None