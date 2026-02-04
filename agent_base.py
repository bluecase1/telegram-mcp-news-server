from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel
import asyncio
import logging

logger = logging.getLogger(__name__)


class NewsItem(BaseModel):
    id: str
    title: str
    content: str
    url: str
    source: str
    published_at: datetime
    language: str = "en"
    country: str = "us"


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


class AgentMessage(BaseModel):
    sender: str
    receiver: str
    message_type: str
    data: Dict[str, Any]
    timestamp: datetime = datetime.now()


class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.message_queue = asyncio.Queue()
        self.running = False
        self.logger = logging.getLogger(f"agent.{name}")
    
    async def start(self):
        """에이전트 시작"""
        self.running = True
        self.logger.info(f"Agent {self.name} started")
        await self.run()
    
    async def stop(self):
        """에이전트 중지"""
        self.running = False
        self.logger.info(f"Agent {self.name} stopped")
    
    async def send_message(self, receiver: str, message_type: str, data: Dict[str, Any]):
        """다른 에이전트에게 메시지 전송"""
        message = AgentMessage(
            sender=self.name,
            receiver=receiver,
            message_type=message_type,
            data=data
        )
        # 메시지 브로커를 통해 전송 (여기서는 간단하게 큐 사용)
        await message_broker.send_message(message)
    
    async def receive_message(self) -> Optional[AgentMessage]:
        """메시지 수신"""
        try:
            return await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None
    
    @abstractmethod
    async def run(self):
        """에이전트 메인 실행 로직"""
        pass
    
    @abstractmethod
    async def process_message(self, message: AgentMessage):
        """수신된 메시지 처리"""
        pass


class MessageBroker:
    """에이전트 간 메시지 중계"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.logger = logging.getLogger("message_broker")
    
    def register_agent(self, agent: BaseAgent):
        """에이전트 등록"""
        self.agents[agent.name] = agent
        self.logger.info(f"Agent {agent.name} registered")
    
    async def send_message(self, message: AgentMessage):
        """메시지 전송"""
        receiver = self.agents.get(message.receiver)
        if receiver:
            await receiver.message_queue.put(message)
            self.logger.debug(f"Message sent from {message.sender} to {message.receiver}")
        else:
            self.logger.warning(f"Unknown receiver: {message.receiver}")
    
    def get_agents(self) -> List[str]:
        """등록된 에이전트 목록 반환"""
        return list(self.agents.keys())


# 전역 메시지 브로커 인스턴스
message_broker = MessageBroker()