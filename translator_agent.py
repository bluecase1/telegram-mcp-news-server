import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
import logging
import os

from agent_base import BaseAgent, AgentMessage, NewsItem, TranslatedNews, message_broker


class TranslatorAgent(BaseAgent):
    """해외 뉴스 번역 에이전트"""
    
    def __init__(self):
        super().__init__("translator")
        
        # 번역 API 설정
        self.translation_provider = os.getenv("TRANSLATION_PROVIDER", "google")
        self.google_api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
        self.papago_client_id = os.getenv("PAPAGO_CLIENT_ID")
        self.papago_client_secret = os.getenv("PAPAGO_CLIENT_SECRET")
        
        # 번역 품질 임계값
        self.confidence_threshold = 0.7
        
        # 지원 언어 쌍
        self.supported_languages = {
            "en": "ko",  # 영어 → 한국어
            "ja": "ko",  # 일본어 → 한국어
            "zh": "ko",  # 중국어 → 한국어
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
                self.logger.error(f"Error in translator agent: {e}")
                await asyncio.sleep(5)
    
    async def process_message(self, message: AgentMessage):
        """수신된 메시지 처리"""
        if message.message_type == "translate_news":
            await self.translate_news_message(message)
        elif message.message_type == "get_translation_status":
            await self.send_translation_status(message.sender)
    
    async def translate_news_message(self, message: AgentMessage):
        """뉴스 번역 처리"""
        try:
            news_data = message.data["news"]
            news = NewsItem(**news_data)
            
            # 번역 가능 여부 확인
            if news.language not in self.supported_languages:
                self.logger.warning(f"Unsupported language: {news.language}")
                return
            
            # 번역 수행
            translated_news = await self.translate_news(news)
            
            if translated_news:
                # 번역 결과를 분석기로 전송
                await self.send_message("analyzer", "analyze_news", {
                    "news": translated_news.dict()
                })
                
                # 원래 발신자에게 결과 통보
                if message.sender != "collector":
                    await self.send_message(message.sender, "translation_complete", {
                        "original_id": news.id,
                        "translated_id": translated_news.original.id
                    })
                
                self.logger.info(f"Translated news: {news.title}")
            
        except Exception as e:
            self.logger.error(f"Error translating news: {e}")
    
    async def translate_news(self, news: NewsItem) -> Optional[TranslatedNews]:
        """뉴스 번역"""
        try:
            # 제목 번역
            translated_title = await self.translate_text(
                news.title, 
                news.language, 
                "ko"
            )
            
            # 내용 번역
            translated_content = await self.translate_text(
                news.content, 
                news.language, 
                "ko"
            )
            
            # 번역 품질 평가 (간단한 구현)
            confidence = self.evaluate_translation_quality(
                news.title, translated_title,
                news.content, translated_content
            )
            
            translated_news = TranslatedNews(
                original=news,
                translated_title=translated_title,
                translated_content=translated_content,
                translation_confidence=confidence
            )
            
            return translated_news
            
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            return None
    
    async def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """텍스트 번역"""
        if self.translation_provider == "google":
            return await self.translate_with_google(text, source_lang, target_lang)
        elif self.translation_provider == "papago":
            return await self.translate_with_papago(text, source_lang, target_lang)
        else:
            # 기본 번역 (모의)
            return f"[{source_lang}->{target_lang}] {text}"
    
    async def translate_with_google(self, text: str, source_lang: str, target_lang: str) -> str:
        """Google Translate API 사용"""
        if not self.google_api_key:
            self.logger.warning("Google Translate API key not configured")
            return f"[Google] {text}"
        
        try:
            url = f"https://translation.googleapis.com/language/translate/v2"
            
            params = {
                "key": self.google_api_key,
                "q": text,
                "source": source_lang,
                "target": target_lang,
                "format": "text"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        translated_text = result["data"]["translations"][0]["translatedText"]
                        return translated_text
                    else:
                        self.logger.error(f"Google Translate API error: {response.status}")
                        return f"[Google Error] {text}"
                        
        except Exception as e:
            self.logger.error(f"Google Translate error: {e}")
            return f"[Google Error] {text}"
    
    async def translate_with_papago(self, text: str, source_lang: str, target_lang: str) -> str:
        """Papago 번역 API 사용"""
        if not self.papago_client_id or not self.papago_client_secret:
            self.logger.warning("Papago API credentials not configured")
            return f"[Papago] {text}"
        
        try:
            url = "https://openapi.naver.com/v1/papago/n2mt"
            
            headers = {
                "X-Naver-Client-Id": self.papago_client_id,
                "X-Naver-Client-Secret": self.papago_client_secret,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }
            
            # Papago 언어 코드 변환
            lang_map = {"en": "en", "ko": "ko", "ja": "ja", "zh": "zh-CN"}
            papago_source = lang_map.get(source_lang, source_lang)
            papago_target = lang_map.get(target_lang, target_lang)
            
            data = {
                "source": papago_source,
                "target": papago_target,
                "text": text
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        translated_text = result["message"]["result"]["translatedText"]
                        return translated_text
                    else:
                        self.logger.error(f"Papago API error: {response.status}")
                        return f"[Papago Error] {text}"
                        
        except Exception as e:
            self.logger.error(f"Papago Translate error: {e}")
            return f"[Papago Error] {text}"
    
    def evaluate_translation_quality(self, original_title: str, translated_title: str,
                                   original_content: str, translated_content: str) -> float:
        """번역 품질 평가 (간단한 구현)"""
        try:
            # 기본 품질 평가 로직 (실제로는 더 복잡한 알고리즘 필요)
            if translated_title and translated_content:
                # 길이 비율, 특수문자 등 기반으로 간단한 평가
                length_ratio = len(translated_content) / len(original_content) if original_content else 0
                title_ratio = len(translated_title) / len(original_title) if original_title else 0
                
                # 0.5 ~ 1.5 사이의 길이 비율이 좋은 번역의 지표
                length_score = 1.0 - abs(length_ratio - 1.0) * 0.3
                title_score = 1.0 - abs(title_ratio - 1.0) * 0.2
                
                confidence = min(max((length_score + title_score) / 2, 0.0), 1.0)
                return confidence
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error evaluating translation quality: {e}")
            return 0.5  # 기본값
    
    async def send_translation_status(self, requester: str):
        """번역 상태 전송"""
        status = {
            "provider": self.translation_provider,
            "supported_languages": self.supported_languages,
            "confidence_threshold": self.confidence_threshold,
            "google_configured": bool(self.google_api_key),
            "papago_configured": bool(self.papago_client_id and self.papago_client_secret)
        }
        
        await self.send_message(requester, "translation_status", status)


# TranslatorAgent 인스턴스 생성 및 등록
translator_agent = TranslatorAgent()
message_broker.register_agent(translator_agent)