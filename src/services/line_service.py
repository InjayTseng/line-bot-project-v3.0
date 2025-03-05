import logging
import aiohttp
from linebot.v3 import WebhookParser
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.messaging import TextMessage, ImageMessage, ReplyMessageRequest, PushMessageRequest
from src.config import settings
import traceback

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
            logger.error(traceback.format_exc())
            raise

    async def reply_image(self, reply_token, image_url):
        """發送圖片訊息"""
        try:
            logger.info(f"準備發送圖片訊息，圖片 URL：{image_url}")
            
            # 檢查 URL 是否有效
            if not image_url or not image_url.startswith(('http://', 'https://')):
                logger.error(f"無效的圖片 URL：{image_url}")
                raise ValueError(f"無效的圖片 URL：{image_url}")
            
            # 記錄更多詳細信息
            logger.info(f"圖片 URL 長度: {len(image_url)}")
            logger.info(f"圖片 URL 前20個字符: {image_url[:20]}...")
            logger.info(f"圖片 URL 後20個字符: ...{image_url[-20:]}")
                
            message = ImageMessage(original_content_url=image_url, preview_image_url=image_url)
            request = ReplyMessageRequest(
                reply_token=reply_token,
                messages=[message]
            )
            
            # 記錄請求詳情
            logger.info(f"發送圖片訊息請求，reply_token: {reply_token}")
            logger.info(f"請求詳情: {request}")
            
            # 發送請求
            response = self.line_bot_api.reply_message_with_http_info(request)
            logger.info(f"圖片訊息發送成功，圖片 URL：{image_url}，回應：{response}")
        except Exception as e:
            logger.error(f"發送圖片訊息失敗：{str(e)}")
            logger.error(traceback.format_exc())
            raise

    async def reply_message(self, reply_token, messages):
        """發送多個訊息"""
        try:
            logger.info(f"準備發送多個訊息，訊息數量：{len(messages)}")
            
            # 檢查訊息
            for i, msg in enumerate(messages):
                if isinstance(msg, ImageMessage):
                    logger.info(f"訊息 {i+1} 是圖片訊息，URL：{msg.original_content_url}")
                    logger.info(f"圖片 URL 長度: {len(msg.original_content_url)}")
                    logger.info(f"圖片 URL 前20個字符: {msg.original_content_url[:20]}...")
                    logger.info(f"圖片 URL 後20個字符: ...{msg.original_content_url[-20:]}")
                    
                    if not msg.original_content_url or not msg.original_content_url.startswith(('http://', 'https://')):
                        logger.error(f"無效的圖片 URL：{msg.original_content_url}")
                        raise ValueError(f"無效的圖片 URL：{msg.original_content_url}")
                elif isinstance(msg, TextMessage):
                    logger.info(f"訊息 {i+1} 是文字訊息，內容：{msg.text[:30]}...")
            
            request = ReplyMessageRequest(
                reply_token=reply_token,
                messages=messages
            )
            
            # 記錄請求詳情
            logger.info(f"發送多個訊息請求，reply_token: {reply_token}")
            logger.info(f"請求詳情: {request}")
            
            # 發送請求
            response = self.line_bot_api.reply_message_with_http_info(request)
            logger.info(f"多個訊息發送成功，回應：{response}")
        except Exception as e:
            logger.error(f"發送多個訊息失敗：{str(e)}")
            logger.error(traceback.format_exc())
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
            logger.error(traceback.format_exc())
            raise
            
    async def push_message(self, user_id, message):
        """發送推播訊息"""
        try:
            # 使用 v3 API 而不是 v2 API
            logger.info(f"使用 v3 API 發送推播訊息，用戶 ID：{user_id}")
            
            request = PushMessageRequest(
                to=user_id,
                messages=[message]
            )
            
            # 記錄請求詳情
            logger.info(f"發送推播訊息，用戶 ID：{user_id}")
            logger.info(f"訊息類型：{type(message).__name__}")
            
            # 發送請求
            response = self.line_bot_api.push_message_with_http_info(request)
            logger.info(f"推播訊息發送成功，用戶 ID：{user_id}，回應：{response}")
            return True
        except Exception as e:
            logger.error(f"發送推播訊息失敗：{str(e)}")
            logger.error(traceback.format_exc())
            raise
            
    async def push_image(self, user_id, image_url):
        """專門用於發送圖片的推播訊息"""
        try:
            logger.info(f"準備發送圖片推播訊息，用戶 ID：{user_id}，圖片 URL：{image_url}")
            
            # 檢查 URL 是否有效
            if not image_url or not image_url.startswith(('http://', 'https://')):
                logger.error(f"無效的圖片 URL：{image_url}")
                raise ValueError(f"無效的圖片 URL：{image_url}")
            
            # 記錄更多詳細信息
            logger.info(f"圖片 URL 長度: {len(image_url)}")
            logger.info(f"圖片 URL 前20個字符: {image_url[:20]}...")
            logger.info(f"圖片 URL 後20個字符: ...{image_url[-20:]}")
            
            # 創建圖片訊息
            image_message = ImageMessage(
                original_content_url=image_url,
                preview_image_url=image_url
            )
            
            # 使用 push_message 方法發送
            return await self.push_message(user_id, image_message)
        except Exception as e:
            logger.error(f"發送圖片推播訊息失敗：{str(e)}")
            logger.error(traceback.format_exc())
            raise
