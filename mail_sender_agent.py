import asyncio
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, List, Optional
import logging
import os
from datetime import datetime

from agent_base import BaseAgent, AgentMessage, CategorizedNews, TranslatedNews, NewsItem, message_broker

try:
    from jinja2 import Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("Warning: Jinja2 not installed. Email templates will be basic.")


class MailSenderAgent(BaseAgent):
    """이메일 뉴스 발신 에이전트"""
    
    def __init__(self):
        super().__init__("mail-sender")
        
        # SMTP 설정
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
        # 발신자 정보
        self.sender_email = os.getenv("SENDER_EMAIL", self.smtp_username)
        self.sender_name = os.getenv("SENDER_NAME", "AI 뉴스 알림")
        
        # 수신자 관리
        self.recipients = set()
        self.load_recipients()
        
        # 전송 설정
        self.batch_size = 10  # 한 번에 보내는 메일 수
        self.send_interval = 1  # 메일 간 간격 (초)
        
        # 통계
        self.send_count = 0
        self.error_count = 0
        self.last_send_time = None
        
        # 템플릿
        self.email_template = self.get_email_template()
    
    def load_recipients(self):
        """수신자 목록 로드"""
        try:
            # 파일에서 수신자 목록 로드
            if os.path.exists("email_recipients.json"):
                with open("email_recipients.json", "r") as f:
                    recipients_data = json.load(f)
                    self.recipients = set(recipients_data.get("recipients", []))
            
            self.logger.info(f"Loaded {len(self.recipients)} email recipients")
            
        except Exception as e:
            self.logger.error(f"Error loading recipients: {e}")
    
    def save_recipients(self):
        """수신자 목록 저장"""
        try:
            recipients_data = {
                "recipients": list(self.recipients),
                "updated_at": datetime.now().isoformat()
            }
            
            with open("email_recipients.json", "w") as f:
                json.dump(recipients_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving recipients: {e}")
    
    def get_email_template(self) -> str:
        """이메일 템플릿 반환"""
        if JINJA2_AVAILABLE:
            return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .news-item { background: white; margin: 15px 0; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; }
        .category { background: #667eea; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .trend-high { color: #e74c3c; }
        .trend-medium { color: #f39c12; }
        .trend-low { color: #27ae60; }
        .tags { margin-top: 10px; }
        .tag { background: #ecf0f1; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-right: 5px; }
        .footer { text-align: center; padding: 20px; color: #777; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI 뉴스 알림</h1>
        <p>{{ date }} - 최신 AI 트렌드 뉴스</p>
    </div>
    
    <div class="content">
        {% for news in news_items %}
        <div class="news-item">
            <h3>{{ news.title }}</h3>
            <p><span class="category">{{ news.category }}</span> 
               <span class="trend-{{ news.trend_level }}">📈 {{ news.trend_level.upper() }}</span>
            </p>
            <p>{{ news.summary|nl2br }}</p>
            
            {% if news.key_points %}
            <h4>🔑 주요 포인트</h4>
            <ul>
                {% for point in news.key_points[:3] %}
                <li>{{ point }}</li>
                {% endfor %}
            </ul>
            {% endif %}
            
            {% if news.tags %}
            <div class="tags">
                {% for tag in news.tags[:5] %}
                <span class="tag">{{ tag }}</span>
                {% endfor %}
            </div>
            {% endif %}
            
            <p><a href="{{ news.url }}" style="color: #667eea;">📰 원문 기사 보기</a></p>
        </div>
        {% endfor %}
    </div>
    
    <div class="footer">
        <p>이 메일은 AI 뉴스 알림 서비스에서 자동으로 발송되었습니다.</p>
        <p>구독 해지: 구독 해지를 원하시면 관리자에게 문의해주세요.</p>
    </div>
</body>
</html>
            """
        else:
            return """
AI 뉴스 알림 - {{ date }}

{% for news in news_items %}
{{ news.title }}

카테고리: {{ news.category }} | 트렌드: {{ news.trend_level.upper() }}

요약:
{{ news.summary }}

{% if news.key_points %}
주요 포인트:
{% for point in news.key_points[:3] %}
- {{ point }}
{% endfor %}
{% endif %}

{% if news.tags %}
태그: {{ news.tags[:5]|join(', ') }}
{% endif %}

원문 링크: {{ news.url }}

---
{% endfor %}

---
AI 뉴스 알림 서비스
            """
    
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
                self.error_count += 1
                self.logger.error(f"Error in mail sender agent: {e}")
                await asyncio.sleep(5)
    
    async def process_message(self, message: AgentMessage):
        """수신된 메시지 처리"""
        if message.message_type == "send_news":
            await self.send_news_message(message)
        elif message.message_type == "send_digest":
            await self.send_news_digest(message)
        elif message.message_type == "get_recipients":
            await self.send_recipients_info(message.sender)
        elif message.message_type == "add_recipient":
            await self.add_recipient(message.data.get("email"))
        elif message.message_type == "remove_recipient":
            await self.remove_recipient(message.data.get("email"))
        elif message.message_type == "test_email":
            await self.send_test_email(message.data.get("email"))
    
    async def send_news_message(self, message: AgentMessage):
        """단일 뉴스 메시지 전송"""
        try:
            categorized_news_data = message.data["categorized_news"]
            categorized_news = CategorizedNews(**categorized_news_data)
            
            # 이메일 내용 포맷팅
            email_data = self.format_single_news(categorized_news)
            
            # 수신자에게 전송
            sent_count = await self.send_email_to_recipients(
                subject=f"AI 뉴스: {email_data['title']}",
                html_content=email_data['html_content'],
                text_content=email_data['text_content']
            )
            
            self.send_count += sent_count
            self.last_send_time = datetime.now()
            
            self.logger.info(f"Sent single news to {sent_count} recipients")
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error sending news email: {e}")
    
    async def send_news_digest(self, message: AgentMessage):
        """뉴스 다이제스트 전송"""
        try:
            news_items_data = message.data.get("news_items", [])
            news_items = [CategorizedNews(**item) for item in news_items_data]
            
            if not news_items:
                self.logger.warning("No news items to send in digest")
                return
            
            # 다이제스트 포맷팅
            email_data = self.format_news_digest(news_items)
            
            # 수신자에게 전송
            sent_count = await self.send_email_to_recipients(
                subject=f"AI 뉴스 다이제스트 - {datetime.now().strftime('%Y년 %m월 %d일')}",
                html_content=email_data['html_content'],
                text_content=email_data['text_content']
            )
            
            self.send_count += sent_count
            self.last_send_time = datetime.now()
            
            self.logger.info(f"Sent news digest to {sent_count} recipients")
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error sending digest email: {e}")
    
    def format_single_news(self, categorized_news: CategorizedNews) -> Dict[str, str]:
        """단일 뉴스 이메일 포맷팅"""
        analyzed_news = categorized_news.analyzed_news
        news = analyzed_news.news
        
        # 제목 및 URL
        if isinstance(news, TranslatedNews):
            title = news.translated_title
            content = news.translated_content
            url = news.original.url
        else:
            title = news.title
            content = news.content
            url = news.url
        
        # 템플릿 데이터
        template_data = {
            "title": title,
            "category": categorized_news.category,
            "trend_level": categorized_news.trend_level,
            "summary": analyzed_news.summary,
            "key_points": analyzed_news.key_points,
            "tags": categorized_news.tags,
            "url": url,
            "importance": analyzed_news.importance_score,
            "ai_relevance": analyzed_news.ai_relevance,
            "date": datetime.now().strftime("%Y년 %m월 %d일")
        }
        
        if JINJA2_AVAILABLE:
            template = Template(self.email_template)
            html_content = template.render(news_items=[template_data], date=template_data['date'])
            text_content = self.generate_text_version([template_data])
        else:
            html_content = self.generate_simple_html([template_data])
            text_content = self.generate_text_version([template_data])
        
        return {
            "title": title,
            "html_content": html_content,
            "text_content": text_content
        }
    
    def format_news_digest(self, news_items: List[CategorizedNews]) -> Dict[str, str]:
        """뉴스 다이제스트 포맷팅"""
        template_data_list = []
        
        for categorized_news in news_items:
            analyzed_news = categorized_news.analyzed_news
            news = analyzed_news.news
            
            if isinstance(news, TranslatedNews):
                title = news.translated_title
                url = news.original.url
            else:
                title = news.title
                url = news.url
            
            template_data = {
                "title": title,
                "category": categorized_news.category,
                "trend_level": categorized_news.trend_level,
                "summary": analyzed_news.summary,
                "key_points": analyzed_news.key_points,
                "tags": categorized_news.tags,
                "url": url,
                "importance": analyzed_news.importance_score,
                "ai_relevance": analyzed_news.ai_relevance
            }
            
            template_data_list.append(template_data)
        
        # 중요도순 정렬
        template_data_list.sort(key=lambda x: x['importance'], reverse=True)
        
        if JINJA2_AVAILABLE:
            template = Template(self.email_template)
            html_content = template.render(
                news_items=template_data_list, 
                date=datetime.now().strftime("%Y년 %m월 %d일")
            )
            text_content = self.generate_text_version(template_data_list)
        else:
            html_content = self.generate_simple_html(template_data_list)
            text_content = self.generate_text_version(template_data_list)
        
        return {
            "html_content": html_content,
            "text_content": text_content
        }
    
    def generate_simple_html(self, news_items: List[Dict]) -> str:
        """간단한 HTML 생성"""
        html_parts = [
            "<html><body>",
            "<h2>🤖 AI 뉴스 알림</h2>",
            f"<p>📅 {datetime.now().strftime('%Y년 %m월 %d일')}</p><hr>"
        ]
        
        for item in news_items:
            html_parts.extend([
                f"<h3>{item['title']}</h3>",
                f"<p><strong>카테고리:</strong> {item['category']} | ",
                f"<strong>트렌드:</strong> {item['trend_level'].upper()}</p>",
                f"<p><strong>요약:</strong><br>{item['summary'].replace(chr(10), '<br>')}</p>"
            ])
            
            if item.get('key_points'):
                html_parts.append("<p><strong>주요 포인트:</strong><ul>")
                for point in item['key_points'][:3]:
                    html_parts.append(f"<li>{point}</li>")
                html_parts.append("</ul></p>")
            
            html_parts.extend([
                f"<p><a href='{item['url']}'>📰 원문 기사 보기</a></p><hr>"
            ])
        
        html_parts.extend([
            "<p><em>이 메일은 AI 뉴스 알림 서비스에서 자동으로 발송되었습니다.</em></p>",
            "</body></html>"
        ])
        
        return "".join(html_parts)
    
    def generate_text_version(self, news_items: List[Dict]) -> str:
        """텍스트 버전 생성"""
        text_parts = [
            f"AI 뉴스 알림 - {datetime.now().strftime('%Y년 %m월 %d일')}",
            "=" * 50
        ]
        
        for item in news_items:
            text_parts.extend([
                "",
                f"제목: {item['title']}",
                f"카테고리: {item['category']} | 트렌드: {item['trend_level'].upper()}",
                "",
                "요약:",
                item['summary']
            ])
            
            if item.get('key_points'):
                text_parts.extend([
                    "",
                    "주요 포인트:"
                ])
                for point in item['key_points'][:3]:
                    text_parts.append(f"- {point}")
            
            text_parts.extend([
                "",
                f"원문 링크: {item['url']}",
                "-" * 30
            ])
        
        text_parts.extend([
            "",
            "---",
            "AI 뉴스 알림 서비스"
        ])
        
        return "\n".join(text_parts)
    
    async def send_email_to_recipients(self, subject: str, html_content: str, text_content: str) -> int:
        """수신자들에게 이메일 전송"""
        if not self.smtp_username or not self.smtp_password:
            self.logger.error("SMTP credentials not configured")
            return 0
        
        sent_count = 0
        
        # 수신자를 배치로 나누어 전송
        recipient_list = list(self.recipients)
        for i in range(0, len(recipient_list), self.batch_size):
            batch = recipient_list[i:i + self.batch_size]
            
            for recipient in batch:
                try:
                    await self.send_single_email(
                        to_email=recipient,
                        subject=subject,
                        html_content=html_content,
                        text_content=text_content
                    )
                    sent_count += 1
                    
                    # 전송 간격
                    await asyncio.sleep(self.send_interval)
                    
                except Exception as e:
                    self.error_count += 1
                    self.logger.error(f"Failed to send email to {recipient}: {e}")
            
            # 배치 간 대기
            if i + self.batch_size < len(recipient_list):
                await asyncio.sleep(self.send_interval * 2)
        
        return sent_count
    
    async def send_single_email(self, to_email: str, subject: str, html_content: str, text_content: str):
        """단일 이메일 전송"""
        # 메시지 생성
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.sender_name} <{self.sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # 텍스트 파트
        text_part = MIMEText(text_content, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # HTML 파트
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # SMTP 연결 및 전송
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            if self.smtp_use_tls:
                server.starttls()
            
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
    
    async def add_recipient(self, email: str) -> bool:
        """수신자 추가"""
        if email and email not in self.recipients:
            self.recipients.add(email)
            self.save_recipients()
            self.logger.info(f"Added email recipient: {email}")
            return True
        return False
    
    async def remove_recipient(self, email: str) -> bool:
        """수신자 제거"""
        if email in self.recipients:
            self.recipients.remove(email)
            self.save_recipients()
            self.logger.info(f"Removed email recipient: {email}")
            return True
        return False
    
    async def send_test_email(self, email: str = None):
        """테스트 이메일 전송"""
        test_email = email or self.smtp_username
        
        try:
            await self.send_single_email(
                to_email=test_email,
                subject="AI 뉴스 알림 테스트",
                html_content="<h2>테스트 메일</h2><p>AI 뉴스 알림 서비스가 정상적으로 동작합니다.</p>",
                text_content="테스트 메일\nAI 뉴스 알림 서비스가 정상적으로 동작합니다."
            )
            
            self.logger.info(f"Test email sent to {test_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send test email: {e}")
            return False
    
    async def send_recipients_info(self, requester: str):
        """수신자 정보 전송"""
        await self.send_message(requester, "recipients_info", {
            "count": len(self.recipients),
            "recipients": list(self.recipients),
            "send_count": self.send_count,
            "error_count": self.error_count,
            "last_send_time": self.last_send_time.isoformat() if self.last_send_time else None
        })


# MailSenderAgent 인스턴스 생성 및 등록
mail_sender_agent = MailSenderAgent()
message_broker.register_agent(mail_sender_agent)