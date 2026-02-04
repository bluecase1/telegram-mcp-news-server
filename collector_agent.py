import asyncio
import aiohttp
import feedparser
from typing import List, Dict, Any
from datetime import datetime, timedelta
import hashlib
from urllib.parse import urljoin
import logging

from agent_base import BaseAgent, AgentMessage, NewsItem, message_broker


class CollectorAgent(BaseAgent):
    """AI 트렌드 뉴스 수집 에이전트"""
    
    def __init__(self):
        super().__init__("collector")
        
        # 국내 뉴스 소스
        self.domestic_sources = [
            "https://www.zdnet.co.kr/news/news_ai.asp",
            "https://www.itworld.co.kr/taxonomy/931/AI",
            "https://technews.co.kr/b/ai",
            "https://www.bloter.net/archives/category/tech/ai",
            "https://www.ciokorea.com/news/AI"  
        ]
        
        # 해외 뉴스 소스
        self.international_sources = [
            "https://techcrunch.com/category/artificial-intelligence/",
            "https://venturebeat.com/ai/",
            "https://www.artificialintelligence-news.com/",
            "https://techcrunch.com/feed/",
            "https://venturebeat.com/feed/"
        ]
        
        # AI 관련 키워드
        self.ai_keywords = [
            "artificial intelligence", "machine learning", "deep learning",
            "neural network", "AI", "ML", "DL", "GPT", "ChatGPT", "LLM",
            "computer vision", "natural language processing", "NLP",
            "예지능", "머신러닝", "딥러닝", "신경망", "GPT", "챗GPT"
        ]
        
        self.last_collection_time = datetime.now() - timedelta(hours=1)
        self.collection_interval = 300  # 5분
    
    async def run(self):
        """에이전트 메인 실행 로직"""
        while self.running:
            try:
                # 메시지 처리
                message = await self.receive_message()
                if message:
                    await self.process_message(message)
                
                # 주기적 뉴스 수집
                current_time = datetime.now()
                if (current_time - self.last_collection_time).seconds >= self.collection_interval:
                    await self.collect_and_distribute_news()
                    self.last_collection_time = current_time
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in collector agent: {e}")
                await asyncio.sleep(5)
    
    async def process_message(self, message: AgentMessage):
        """수신된 메시지 처리"""
        if message.message_type == "collect_now":
            await self.collect_and_distribute_news()
        elif message.message_type == "get_sources":
            sources = {
                "domestic": self.domestic_sources,
                "international": self.international_sources
            }
            await self.send_message(message.sender, "sources_response", {"sources": sources})
    
    async def collect_and_distribute_news(self):
        """뉴스 수집 및 분배"""
        self.logger.info("Starting news collection")
        
        # 국내 뉴스 우선 수집
        domestic_news = await self.collect_domestic_news()
        international_news = await self.collect_international_news()
        
        all_news = domestic_news + international_news
        
        if all_news:
            # 중복 제거
            unique_news = self.remove_duplicates(all_news)
            
            # 수집된 뉴스를 다른 에이전트에게 전송
            for news in unique_news:
                if self.is_ai_related(news):
                    await self.send_news_to_pipeline(news)
            
            self.logger.info(f"Collected {len(unique_news)} AI-related news items")
    
    async def collect_domestic_news(self) -> List[NewsItem]:
        """국내 뉴스 수집"""
        news_items = []
        
        async with aiohttp.ClientSession() as session:
            for source_url in self.domestic_sources:
                try:
                    # RSS 피드인 경우
                    if source_url.endswith('.xml') or 'feed' in source_url:
                        news = await self.collect_from_rss(session, source_url, "ko", "kr")
                    else:
                        # 웹 크롤링인 경우
                        news = await self.collect_from_web(session, source_url, "ko", "kr")
                    
                    news_items.extend(news)
                    
                except Exception as e:
                    self.logger.error(f"Error collecting from {source_url}: {e}")
        
        return news_items
    
    async def collect_international_news(self) -> List[NewsItem]:
        """해외 뉴스 수집"""
        news_items = []
        
        async with aiohttp.ClientSession() as session:
            for source_url in self.international_sources:
                try:
                    if source_url.endswith('.xml') or 'feed' in source_url:
                        news = await self.collect_from_rss(session, source_url, "en", "us")
                    else:
                        news = await self.collect_from_web(session, source_url, "en", "us")
                    
                    news_items.extend(news)
                    
                except Exception as e:
                    self.logger.error(f"Error collecting from {source_url}: {e}")
        
        return news_items
    
    async def collect_from_rss(self, session: aiohttp.ClientSession, rss_url: str, 
                              language: str, country: str) -> List[NewsItem]:
        """RSS 피드에서 뉴스 수집"""
        news_items = []
        
        try:
            async with session.get(rss_url) as response:
                if response.status == 200:
                    rss_content = await response.text()
                    feed = feedparser.parse(rss_content)
                    
                    for entry in feed.entries[:10]:  # 최신 10개만
                        news_item = NewsItem(
                            id=self.generate_id(entry.link),
                            title=entry.title,
                            content=entry.description or entry.summary or "",
                            url=entry.link,
                            source=feed.feed.title,
                            published_at=self.parse_date(entry.published),
                            language=language,
                            country=country
                        )
                        news_items.append(news_item)
                        
        except Exception as e:
            self.logger.error(f"Error parsing RSS {rss_url}: {e}")
        
        return news_items
    
    async def collect_from_web(self, session: aiohttp.ClientSession, url: str,
                              language: str, country: str) -> List[NewsItem]:
        """웹사이트에서 뉴스 수집 (기본 구현)"""
        news_items = []
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    # 실제 구현에서는 BeautifulSoup 등으로 파싱 필요
                    # 여기서는 기본 구조만 생성
                    html_content = await response.text()
                    
                    # 간단한 뉴스 아이템 생성 (실제로는 HTML 파싱 필요)
                    news_item = NewsItem(
                        id=self.generate_id(url),
                        title=f"News from {url}",
                        content=f"Content from {url}",
                        url=url,
                        source=url,
                        published_at=datetime.now(),
                        language=language,
                        country=country
                    )
                    news_items.append(news_item)
                    
        except Exception as e:
            self.logger.error(f"Error collecting from web {url}: {e}")
        
        return news_items
    
    def is_ai_related(self, news: NewsItem) -> bool:
        """AI 관련 뉴스인지 확인"""
        text = (news.title + " " + news.content).lower()
        return any(keyword.lower() in text for keyword in self.ai_keywords)
    
    def remove_duplicates(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """중복 뉴스 제거"""
        seen_urls = set()
        unique_news = []
        
        for news in news_items:
            if news.url not in seen_urls:
                seen_urls.add(news.url)
                unique_news.append(news)
        
        return unique_news
    
    async def send_news_to_pipeline(self, news: NewsItem):
        """수집된 뉴스를 파이프라인으로 전송"""
        if news.language == "en":
            # 해외 뉴스는 번역기로
            await self.send_message("translator", "translate_news", {
                "news": news.dict()
            })
        else:
            # 국내 뉴스는 바로 분석기로
            await self.send_message("analyzer", "analyze_news", {
                "news": news.dict()
            })
    
    def generate_id(self, url: str) -> str:
        """고유 ID 생성"""
        return hashlib.md5(url.encode()).hexdigest()[:12]
    
    def parse_date(self, date_str: str) -> datetime:
        """날짜 파싱"""
        try:
            from dateutil.parser import parse
            return parse(date_str)
        except:
            return datetime.now()


# CollectorAgent 인스턴스 생성 및 등록
collector_agent = CollectorAgent()
message_broker.register_agent(collector_agent)