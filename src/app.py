import os
import logging
import cloudinary
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage

from src.config import settings
from src.handlers.message_handler import MessageHandler

# 設定日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 Flask
app = Flask(__name__)

# 初始化 LINE Bot
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)

# 初始化 Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

# 初始化訊息處理器
message_handler = MessageHandler()

@app.route("/callback", methods=['POST'])
def callback():
    """處理 LINE Webhook"""
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
        logger.info("webhook 處理成功")
        return 'OK'
    except InvalidSignatureError:
        logger.error("無效的簽章")
        abort(400)
    except Exception as e:
        logger.error(f"處理 webhook 時發生錯誤：{str(e)}")
        abort(500)

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    message_handler.handle_text_message(event)

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    message_handler.handle_image_message(event)

if __name__ == "__main__":
    # 設定更詳細的日誌記錄
    logging.getLogger('linebot').setLevel(logging.DEBUG)
    
    # 確保上傳目錄存在
    os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
    
    # 啟動應用
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
