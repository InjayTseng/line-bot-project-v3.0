import logging
from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, ImageSendMessage
from src.config import settings

logger = logging.getLogger(__name__)

class LineService:
    def __init__(self):
        self.line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
        self.handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)

    def reply_text(self, reply_token, text):
        """發送文字訊息"""
        try:
            self.line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text=text)
            )
            logger.info(f"文字訊息發送成功：{text}")
        except Exception as e:
            logger.error(f"發送文字訊息失敗：{str(e)}")
            raise

    def reply_image(self, reply_token, image_url):
        """發送圖片訊息"""
        try:
            self.line_bot_api.reply_message(
                reply_token,
                ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            )
            logger.info(f"圖片訊息發送成功，圖片 URL：{image_url}")
        except Exception as e:
            logger.error(f"發送圖片訊息失敗：{str(e)}")
            raise

    def get_message_content(self, message_id):
        """獲取訊息內容"""
        try:
            message_content = self.line_bot_api.get_message_content(message_id)
            return message_content.content
        except Exception as e:
            logger.error(f"獲取訊息內容失敗：{str(e)}")
            raise
