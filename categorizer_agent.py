import asyncio
import re
from typing import Dict, Any, List, Optional, Tuple
import logging

from agent_base import BaseAgent, AgentMessage, AnalyzedNews, CategorizedNews, TranslatedNews, NewsItem, message_broker


class CategorizerAgent(BaseAgent):
    """뉴스 분류 에이전트"""
    
    def __init__(self):
        super().__init__("categorizer")
        
        # 카테고리 정의
        self.categories = {
            "ml": {
                "name": "머신러닝",
                "keywords": ["머신러닝", "machine learning", "ML", "알고리즘", "algorithm", "모델", "model"],
                "weight": 1.0
            },
            "dl": {
                "name": "딥러닝",
                "keywords": ["딥러닝", "deep learning", "DL", "신경망", "neural network", "CNN", "RNN", "Transformer"],
                "weight": 1.2
            },
            "nlp": {
                "name": "자연어처리",
                "keywords": ["자연어처리", "NLP", "natural language processing", "언어 모델", "language model", "GPT", "LLM", "대규모 언어 모델", "챗봇", "chatbot"],
                "weight": 1.1
            },
            "cv": {
                "name": "컴퓨터비전",
                "keywords": ["컴퓨터비전", "computer vision", "CV", "이미지 인식", "image recognition", "객체 탐지", "object detection"],
                "weight": 1.0
            },
            "robotics": {
                "name": "로보틱스",
                "keywords": ["로보틱스", "robotics", "로봇", "robot", "자율주행", "autonomous", "드론", "drone"],
                "weight": 0.9
            },
            "enterprise": {
                "name": "기업 동향",
                "keywords": ["기업", "company", "투자", "investment", "인수", "acquisition", "출시", "launch", "실적", "earnings"],
                "weight": 0.8
            },
            "research": {
                "name": "연구 개발",
                "keywords": ["연구", "research", "개발", "development", "논문", "paper", "발표", "presentation", "실험", "experiment"],
                "weight": 0.9
            },
            "ethics": {
                "name": "AI 윤리",
                "keywords": ["윤리", "ethics", "안전", "safety", "규제", "regulation", "정책", "policy", "편향", "bias"],
                "weight": 1.0
            },
            "generative": {
                "name": "생성 AI",
                "keywords": ["생성 AI", "generative AI", "생성형", "Stable Diffusion", "DALL-E", "Midjourney", "이미지 생성", "text-to-image"],
                "weight": 1.3
            },
            "hardware": {
                "name": "AI 하드웨어",
                "keywords": ["GPU", "CPU", "칩", "chip", "반도체", "semiconductor", "NVIDIA", "TPU", "하드웨어", "hardware"],
                "weight": 0.9
            }
        }
        
        # 트렌드 레벨 임계값
        self.trend_thresholds = {
            "high": 0.8,
            "medium": 0.5,
            "low": 0.0
        }
    
    async def run(self):
        """에이전트 메인 실행 로직"""
        while self.running:
            try:
                # 메시지 처리
                message = await self.receive_message()
                if message:
                    await self.process_message(message)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in categorizer agent: {e}")
                await asyncio.sleep(5)
    
    async def process_message(self, message: AgentMessage):
        """수신된 메시지 처리"""
        if message.message_type == "categorize_news":
            await self.categorize_news_message(message)
        elif message.message_type == "get_categories":
            await self.send_categories_info(message.sender)
        elif message.message_type == "get_category_stats":
            await self.send_category_stats(message.sender)
    
    async def categorize_news_message(self, message: AgentMessage):
        """뉴스 분류 처리"""
        try:
            analyzed_news_data = message.data["analyzed_news"]
            analyzed_news = AnalyzedNews(**analyzed_news_data)
            
            # 뉴스 분류 수행
            categorized_news = await self.categorize_news(analyzed_news)
            
            if categorized_news:
                # 분류 결과를 발신 에이전트들에게 전송
                await self.send_to_senders(categorized_news)
                
                # 원래 발신자에게 결과 통보
                await self.send_message("collector", "categorization_complete", {
                    "news_id": categorized_news.analyzed_news.news.original.id if isinstance(categorized_news.analyzed_news.news, TranslatedNews) else categorized_news.analyzed_news.news.id,
                    "category": categorized_news.category,
                    "trend_level": categorized_news.trend_level
                })
                
                self.logger.info(f"Categorized news: {categorized_news.category} (trend: {categorized_news.trend_level})")
            
        except Exception as e:
            self.logger.error(f"Error categorizing news: {e}")
    
    async def categorize_news(self, analyzed_news: AnalyzedNews) -> Optional[CategorizedNews]:
        """뉴스 분류 수행"""
        try:
            # 분석된 뉴스에서 텍스트 추출
            news = analyzed_news.news
            if isinstance(news, TranslatedNews):
                title = news.translated_title
                content = news.translated_content
            else:
                title = news.title
                content = news.content
            
            # 요약과 키워드 포함
            summary = analyzed_news.summary
            key_points = " ".join(analyzed_news.key_points)
            
            # 전체 텍스트
            full_text = f"{title} {content} {summary} {key_points}".lower()
            
            # 카테고리별 점수 계산
            category_scores = self.calculate_category_scores(full_text)
            
            # 최고 점수 카테고리 선택
            best_category = max(category_scores.items(), key=lambda x: x[1])
            category_id = best_category[0]
            category_score = best_category[1]
            
            # 카테고리 이름
            category_name = self.categories[category_id]["name"]
            
            # 태그 생성
            tags = self.generate_tags(full_text, category_id)
            
            # 트렌드 레벨 결정
            trend_level = self.determine_trend_level(analyzed_news, category_score)
            
            categorized_news = CategorizedNews(
                analyzed_news=analyzed_news,
                category=category_name,
                tags=tags,
                trend_level=trend_level
            )
            
            return categorized_news
            
        except Exception as e:
            self.logger.error(f"Categorization failed: {e}")
            return None
    
    def calculate_category_scores(self, text: str) -> Dict[str, float]:
        """카테고리별 점수 계산"""
        scores = {}
        
        for category_id, category_info in self.categories.items():
            score = 0.0
            keywords = category_info["keywords"]
            weight = category_info["weight"]
            
            for keyword in keywords:
                # 키워드 빈도수 계산
                count = text.count(keyword.lower())
                if count > 0:
                    # 키워드 길이에 따른 가중치 (긴 키워드가 더 중요)
                    keyword_weight = len(keyword.split()) * 0.5 + 0.5
                    score += count * keyword_weight * weight
            
            scores[category_id] = score
        
        return scores
    
    def generate_tags(self, text: str, primary_category: str) -> List[str]:
        """태그 생성"""
        tags = []
        
        # 모든 카테고리 키워드 검색
        all_keywords = []
        for category_id, category_info in self.categories.items():
            if category_id != primary_category:
                all_keywords.extend(category_info["keywords"])
        
        # 텍스트에서 키워드 찾기
        for keyword in all_keywords:
            if keyword.lower() in text.lower() and keyword not in tags:
                tags.append(keyword)
                if len(tags) >= 5:  # 최대 5개 태그
                    break
        
        # 기술 관련 추가 태그
        tech_tags = ["AI", "인공지능", "innovation", "혁신"]
        for tag in tech_tags:
            if tag.lower() in text.lower() and tag not in tags:
                tags.append(tag)
                if len(tags) >= 8:  # 최대 8개 태그
                    break
        
        return tags[:8]
    
    def determine_trend_level(self, analyzed_news: AnalyzedNews, category_score: float) -> str:
        """트렌드 레벨 결정"""
        # AI 관련성, 중요도, 카테고리 점수 종합
        combined_score = (
            analyzed_news.ai_relevance * 0.4 +
            analyzed_news.importance_score * 0.3 +
            min(category_score / 5.0, 1.0) * 0.3  # 카테고리 점수 정규화
        )
        
        if combined_score >= self.trend_thresholds["high"]:
            return "high"
        elif combined_score >= self.trend_thresholds["medium"]:
            return "medium"
        else:
            return "low"
    
    async def send_to_senders(self, categorized_news: CategorizedNews):
        """발신 에이전트들에게 분류된 뉴스 전송"""
        # 텔레그램 발신자에게 전송
        await self.send_message("telegram-sender", "send_news", {
            "categorized_news": categorized_news.dict()
        })
        
        # 메일 발신자에게 전송
        await self.send_message("mail-sender", "send_news", {
            "categorized_news": categorized_news.dict()
        })
    
    async def send_categories_info(self, requester: str):
        """카테고리 정보 전송"""
        categories_info = {}
        for category_id, category_info in self.categories.items():
            categories_info[category_id] = {
                "name": category_info["name"],
                "keywords": category_info["keywords"]
            }
        
        await self.send_message(requester, "categories_info", {
            "categories": categories_info
        })
    
    async def send_category_stats(self, requester: str):
        """카테고리 통계 전송"""
        stats = {
            "total_categories": len(self.categories),
            "category_names": [info["name"] for info in self.categories.values()],
            "trend_thresholds": self.trend_thresholds
        }
        
        await self.send_message(requester, "category_stats", stats)


# CategorizerAgent 인스턴스 생성 및 등록
categorizer_agent = CategorizerAgent()
message_broker.register_agent(categorizer_agent)