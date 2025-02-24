import logging
import aiohttp
from linebot.v3 import WebhookParser
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.messaging import TextMessage, ImageMessage, ReplyMessageRequest
from src.config import settings

logger = logging.getLogger(__name__)

class LineService:
    def __init__(self):
        self.configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
        self.api_client = ApiClient(self.configuration)
        self.line_bot_api = MessagingApi(self.api_client)
        self.session = None
        
    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def reply_text(self, reply_token, text):
        """發送文字訊息"""
        try:
            message = TextMessage(text=text)
            request = ReplyMessageRequest(
                reply_token=reply_token,
                messages=[message]
            )
            self.line_bot_api.reply_message_with_http_info(request)
            logger.info(f"文字訊息發送成功：{text}")
        except Exception as e:
            logger.error(f"發送文字訊息失敗：{str(e)}")
            raise

    async def reply_image(self, reply_token, image_url):
        """發送圖片訊息"""
        try:
            message = ImageMessage(original_content_url=image_url, preview_image_url=image_url)
            request = ReplyMessageRequest(
                reply_token=reply_token,
                messages=[message]
            )
            self.line_bot_api.reply_message_with_http_info(request)
            logger.info(f"圖片訊息發送成功，圖片 URL：{image_url}")
        except Exception as e:
            logger.error(f"發送圖片訊息失敗：{str(e)}")
            raise

    async def reply_message(self, reply_token, messages):
        """發送多個訊息"""
        try:
            request = ReplyMessageRequest(
                reply_token=reply_token,
                messages=messages
            )
            self.line_bot_api.reply_message_with_http_info(request)
            logger.info("多個訊息發送成功")
        except Exception as e:
            logger.error(f"發送多個訊息失敗：{str(e)}")
            raise

    async def get_message_content(self, message_id):
        """獲取訊息內容"""
        try:
            session = await self.get_session()
            headers = {
                'Authorization': f'Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}'
            }
            async with session.get(
                f'https://api-data.line.me/v2/bot/message/{message_id}/content',
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LINE API 回應狀態碼: {response.status}, 錯誤: {error_text}")
                return await response.read()
        except Exception as e:
            logger.error(f"獲取訊息內容失敗：{str(e)}")
            raise
            
    async def push_message(self, user_id, message):
        """發送推播訊息"""
        try:
            session = await self.get_session()
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}'
            }
            data = {
                'to': user_id,
                'messages': [message.as_json_dict()]
            }
            async with session.post(
                'https://api.line.me/v2/bot/message/push',
                headers=headers,
                json=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LINE API 回應狀態碼: {response.status}, 錯誤: {error_text}")
                    
            logger.info(f"推播訊息發送成功，用戶 ID：{user_id}")
        except Exception as e:
            logger.error(f"發送推播訊息失敗：{str(e)}")
            raise
