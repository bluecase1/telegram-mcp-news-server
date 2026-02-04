import asyncio
import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv
from pydantic import BaseModel
import telegram
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    GetToolsRequest,
    ListToolsRequest,
    TextContent,
    Tool,
)

# Load environment variables
load_dotenv()


class Settings(BaseModel):
    bot_token: str
    allowed_chat_ids: List[int] = []
    log_level: str = "INFO"


class TelegramMCPServer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.bot = telegram.Bot(token=settings.bot_token)
        self.server = Server("telegram-mcp-server")
        self._setup_handlers()
    
    def _setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return [
                Tool(
                    name="send_message",
                    description="Send a message to a Telegram chat",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chat_id": {
                                "type": "integer",
                                "description": "Telegram chat ID to send message to"
                            },
                            "text": {
                                "type": "string",
                                "description": "Message text content"
                            },
                            "parse_mode": {
                                "type": "string",
                                "enum": ["HTML", "Markdown", "MarkdownV2"],
                                "description": "Message parsing mode"
                            },
                            "disable_notification": {
                                "type": "boolean",
                                "description": "Send message silently",
                                "default": False
                            }
                        },
                        "required": ["chat_id", "text"]
                    }
                ),
                Tool(
                    name="send_photo",
                    description="Send a photo to a Telegram chat",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chat_id": {
                                "type": "integer",
                                "description": "Telegram chat ID to send photo to"
                            },
                            "photo": {
                                "type": "string",
                                "description": "Photo URL or local file path"
                            },
                            "caption": {
                                "type": "string",
                                "description": "Photo caption"
                            },
                            "parse_mode": {
                                "type": "string",
                                "enum": ["HTML", "Markdown", "MarkdownV2"],
                                "description": "Caption parsing mode"
                            }
                        },
                        "required": ["chat_id", "photo"]
                    }
                ),
                Tool(
                    name="send_document",
                    description="Send a document to a Telegram chat",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chat_id": {
                                "type": "integer",
                                "description": "Telegram chat ID to send document to"
                            },
                            "document": {
                                "type": "string",
                                "description": "Document URL or local file path"
                            },
                            "caption": {
                                "type": "string",
                                "description": "Document caption"
                            },
                            "parse_mode": {
                                "type": "string",
                                "enum": ["HTML", "Markdown", "MarkdownV2"],
                                "description": "Caption parsing mode"
                            }
                        },
                        "required": ["chat_id", "document"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            try:
                if name == "send_message":
                    return await self._send_message(arguments)
                elif name == "send_photo":
                    return await self._send_photo(arguments)
                elif name == "send_document":
                    return await self._send_document(arguments)
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
    
    async def _validate_chat_id(self, chat_id: int) -> bool:
        """Check if chat ID is allowed"""
        if not self.settings.allowed_chat_ids:
            return True  # If no restrictions, allow all
        return chat_id in self.settings.allowed_chat_ids
    
    async def _send_message(self, arguments: Dict[str, Any]) -> CallToolResult:
        chat_id = arguments["chat_id"]
        text = arguments["text"]
        parse_mode = arguments.get("parse_mode")
        disable_notification = arguments.get("disable_notification", False)
        
        if not await self._validate_chat_id(chat_id):
            return CallToolResult(
                content=[TextContent(type="text", text=f"Chat ID {chat_id} is not allowed")],
                isError=True
            )
        
        try:
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_notification=disable_notification
            )
            
            return CallToolResult(
                content=[TextContent(
                    type="text", 
                    text=f"Message sent successfully to chat {chat_id}. Message ID: {message.message_id}"
                )]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to send message: {str(e)}")],
                isError=True
            )
    
    async def _send_photo(self, arguments: Dict[str, Any]) -> CallToolResult:
        chat_id = arguments["chat_id"]
        photo = arguments["photo"]
        caption = arguments.get("caption")
        parse_mode = arguments.get("parse_mode")
        
        if not await self._validate_chat_id(chat_id):
            return CallToolResult(
                content=[TextContent(type="text", text=f"Chat ID {chat_id} is not allowed")],
                isError=True
            )
        
        try:
            # Check if photo is a URL or local file
            if photo.startswith(('http://', 'https://')):
                message = await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode=parse_mode
                )
            else:
                # Local file
                with open(photo, 'rb') as photo_file:
                    message = await self.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo_file,
                        caption=caption,
                        parse_mode=parse_mode
                    )
            
            return CallToolResult(
                content=[TextContent(
                    type="text", 
                    text=f"Photo sent successfully to chat {chat_id}. Message ID: {message.message_id}"
                )]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to send photo: {str(e)}")],
                isError=True
            )
    
    async def _send_document(self, arguments: Dict[str, Any]) -> CallToolResult:
        chat_id = arguments["chat_id"]
        document = arguments["document"]
        caption = arguments.get("caption")
        parse_mode = arguments.get("parse_mode")
        
        if not await self._validate_chat_id(chat_id):
            return CallToolResult(
                content=[TextContent(type="text", text=f"Chat ID {chat_id} is not allowed")],
                isError=True
            )
        
        try:
            # Check if document is a URL or local file
            if document.startswith(('http://', 'https://')):
                message = await self.bot.send_document(
                    chat_id=chat_id,
                    document=document,
                    caption=caption,
                    parse_mode=parse_mode
                )
            else:
                # Local file
                with open(document, 'rb') as doc_file:
                    message = await self.bot.send_document(
                        chat_id=chat_id,
                        document=doc_file,
                        caption=caption,
                        parse_mode=parse_mode
                    )
            
            return CallToolResult(
                content=[TextContent(
                    type="text", 
                    text=f"Document sent successfully to chat {chat_id}. Message ID: {message.message_id}"
                )]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to send document: {str(e)}")],
                isError=True
            )


async def main():
    try:
        settings = Settings(
            bot_token=os.getenv("BOT_TOKEN", ""),
            allowed_chat_ids=[
                int(x.strip()) for x in os.getenv("ALLOWED_CHAT_IDS", "").split(",") 
                if x.strip()
            ],
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
        
        if not settings.bot_token:
            print("Error: BOT_TOKEN environment variable is required", file=sys.stderr)
            sys.exit(1)
        
        mcp_server = TelegramMCPServer(settings)
        
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="telegram-mcp-server",
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