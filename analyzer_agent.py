import asyncio
import aiohttp
import json
import re
from typing import Dict, Any, List, Tuple, Union, Optional
import logging
import os
from google import genai

from agent_base import BaseAgent, AgentMessage, NewsItem, TranslatedNews, AnalyzedNews, message_broker


class AnalyzerAgent(BaseAgent):
    """뉴스 분석 및 요약 에이전트"""
    
    def __init__(self):
        super().__init__("analyzer")
        
        # 분석 모델 설정
        self.analysis_model = os.getenv("ANALYSIS_MODEL", "simple")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

        self.gemini_client = None
        if self.gemini_api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            except Exception as e:
                self.logger.error(f"Failed to initialize Gemini client: {e}")
        
        # AI 관련 키워드 가중치
        self.ai_keywords_weights = {
            "GPT": 0.9,
            "ChatGPT": 0.9,
            "LLM": 0.8,
            "대규모 언어 모델": 0.9,
            "deep learning": 0.7,
            "딥러닝": 0.8,
            "machine learning": 0.6,
            "머신러닝": 0.7,
            "neural network": 0.6,
            "신경망": 0.7,
            "computer vision": 0.6,
            "컴퓨터 비전": 0.7,
            "NLP": 0.6,
            "자연어 처리": 0.7,
            "AGI": 0.9,
            "인공지능": 0.7
        }
        
        # 최대 요약 라인 수
        self.max_summary_lines = 10
    
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
                self.logger.error(f"Error in analyzer agent: {e}")
                await asyncio.sleep(5)
    
    async def process_message(self, message: AgentMessage):
        """수신된 메시지 처리"""
        if message.message_type == "analyze_news":
            await self.analyze_news_message(message)
        elif message.message_type == "get_analysis_stats":
            await self.send_analysis_stats(message.sender)
    
    async def analyze_news_message(self, message: AgentMessage):
        """뉴스 분석 처리"""
        try:
            news_data = message.data["news"]
            
            # NewsItem 또는 TranslatedNews 처리
            if "translated_title" in news_data:
                news = TranslatedNews(**news_data)
            else:
                news = NewsItem(**news_data)
            
            # 뉴스 분석 수행
            analyzed_news = await self.analyze_news(news)
            
            if analyzed_news:
                # 분석 결과를 분류기로 전송
                await self.send_message("categorizer", "categorize_news", {
                    "analyzed_news": analyzed_news.dict()
                })
                
                # 원래 발신자에게 결과 통보
                if message.sender != "translator" and message.sender != "collector":
                    await self.send_message(message.sender, "analysis_complete", {
                    "news_id": analyzed_news.news.original.id if isinstance(analyzed_news.news, TranslatedNews) else analyzed_news.news.id,
                    "importance_score": analyzed_news.importance_score
                })
                
                title = analyzed_news.news.translated_title if isinstance(analyzed_news.news, TranslatedNews) else analyzed_news.news.title
                self.logger.info(f"Analyzed news: {title}")
            
        except Exception as e:
            self.logger.error(f"Error analyzing news: {e}")
    
    async def analyze_news(self, news: Union[NewsItem, TranslatedNews]) -> Optional[AnalyzedNews]:
        """뉴스 분석 수행"""
        try:
            # 제목과 내용 추출
            if isinstance(news, TranslatedNews):
                title = news.translated_title
                content = news.translated_content
            else:
                title = news.title
                content = news.content
            
            # 요약 생성
            summary = await self.generate_summary(title, content)
            
            # 핵심 포인트 추출
            key_points = await self.extract_key_points(title, content)
            
            # 중요도 및 AI 관련성 평가
            importance_score = self.evaluate_importance(title, content)
            ai_relevance = self.evaluate_ai_relevance(title, content)
            
            analyzed_news = AnalyzedNews(
                news=news,
                summary=summary,
                key_points=key_points,
                importance_score=importance_score,
                ai_relevance=ai_relevance
            )
            
            return analyzed_news
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return None
    
    async def generate_summary(self, title: str, content: str) -> str:
        """뉴스 요약 생성 (10줄 이내)"""
        if self.analysis_model == "openai" and self.openai_api_key:
            return await self.generate_summary_with_gpt(title, content)
        elif self.analysis_model == "gemini" and self.gemini_client:
            return await self.generate_summary_with_gemini(title, content)
        else:
            return self.generate_simple_summary(title, content)
    
    async def generate_summary_with_gemini(self, title: str, content: str) -> str:
        """Gemini를 사용한 요약 생성"""
        try:
            prompt = f"""
            다음 뉴스 기사를 10줄 이내로 요약해주세요. 핵심 내용에 집중하고, AI 기술 관련 정보를 강조해주세요.
            
            제목: {title}
            내용: {content[:8000]}  # Gemini는 컨텍스트 윈도우가 더 큼
            
            요약:
            """
            
            response = await self.gemini_client.aio.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            summary = response.text.strip()
            return self.limit_lines(summary, self.max_summary_lines)
                        
        except Exception as e:
            self.logger.error(f"Gemini summary error: {e}")
            return self.generate_simple_summary(title, content)

    async def generate_summary_with_gpt(self, title: str, content: str) -> str:
        """GPT를 사용한 요약 생성"""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""
            다음 뉴스 기사를 10줄 이내로 요약해주세요. 핵심 내용에 집중하고, AI 기술 관련 정보를 강조해주세요.
            
            제목: {title}
            내용: {content[:2000]}  # 내용이 긴 경우 첫 2000자만 사용
            
            요약:
            """
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.3
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        summary = result["choices"][0]["message"]["content"].strip()
                        return self.limit_lines(summary, self.max_summary_lines)
                    else:
                        self.logger.error(f"OpenAI API error: {response.status}")
                        return self.generate_simple_summary(title, content)
                        
        except Exception as e:
            self.logger.error(f"GPT summary error: {e}")
            return self.generate_simple_summary(title, content)
    
    def generate_simple_summary(self, title: str, content: str) -> str:
        """간단한 요약 생성"""
        # 내용에서 문장 분리
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 제목 포함
        summary_lines = [f"제목: {title}"]
        
        # 중요 문장 선택 (간단한 알고리즘)
        for sentence in sentences[:8]:  # 최대 8개 문장 선택
            if len(sentence) > 10:  # 짧은 문장 제외
                summary_lines.append(f"• {sentence}")
        
        return '\n'.join(summary_lines[:self.max_summary_lines])
    
    async def extract_key_points(self, title: str, content: str) -> List[str]:
        """핵심 포인트 추출"""
        key_points = []
        
        # AI 관련 키워드 포함 문장 찾기
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
                
            # AI 키워드 확인
            for keyword in self.ai_keywords_weights.keys():
                if keyword.lower() in sentence.lower():
                    key_points.append(f"{keyword}: {sentence}")
                    break
        
        # 최대 5개 키 포인트
        return key_points[:5]
    
    def evaluate_importance(self, title: str, content: str) -> float:
        """뉴스 중요도 평가 (0.0 - 1.0)"""
        importance_score = 0.3  # 기본 점수
        
        text = (title + " " + content).lower()
        
        # 중요 키워드 가중치
        important_keywords = {
            "발표": 0.2, "출시": 0.2, "투자": 0.15, "인수": 0.15,
            "launch": 0.2, "release": 0.2, "investment": 0.15, "acquisition": 0.15
        }
        
        for keyword, weight in important_keywords.items():
            if keyword in text:
                importance_score += weight
        
        # 문서 길이 기반 중요도
        if len(content) > 1000:
            importance_score += 0.1
        elif len(content) > 2000:
            importance_score += 0.2
        
        return min(importance_score, 1.0)
    
    def evaluate_ai_relevance(self, title: str, content: str) -> float:
        """AI 관련성 평가 (0.0 - 1.0)"""
        text = (title + " " + content).lower()
        relevance_score = 0.0
        
        for keyword, weight in self.ai_keywords_weights.items():
            if keyword.lower() in text:
                relevance_score += weight
        
        # 여러 키워드가 있을 경우 보너스
        keyword_count = sum(1 for keyword in self.ai_keywords_weights.keys() 
                          if keyword.lower() in text)
        if keyword_count > 1:
            relevance_score *= 1.2
        
        return min(relevance_score, 1.0)
    
    def limit_lines(self, text: str, max_lines: int) -> str:
        """라인 수 제한"""
        lines = text.split('\n')
        return '\n'.join(lines[:max_lines])
    
    async def send_analysis_stats(self, requester: str):
        """분석 상태 전송"""
        stats = {
            "model": self.analysis_model,
            "max_summary_lines": self.max_summary_lines,
            "openai_configured": bool(self.openai_api_key),
            "gemini_configured": bool(self.gemini_client),
            "ai_keywords_count": len(self.ai_keywords_weights)
        }
        
        await self.send_message(requester, "analysis_stats", stats)


# AnalyzerAgent 인스턴스 생성 및 등록
analyzer_agent = AnalyzerAgent()
message_broker.register_agent(analyzer_agent)