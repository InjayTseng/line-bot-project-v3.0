import os
import json
import logging
import cloudinary
from quart import Quart, request, abort, send_from_directory
from linebot.v3 import WebhookParser
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent, FollowEvent

from src.config import settings
from src.handlers.message_handler import MessageHandler

# 設定日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 Quart
app = Quart(__name__)

# 初始化 LINE Bot
configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
with ApiClient(configuration) as api_client:
    line_bot_api = MessagingApi(api_client)

# 初始化 Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

# 初始化訊息處理器
message_handler = MessageHandler()

# 設定靜態文件路由
@app.route('/static/<path:filename>')
async def serve_static(filename):
    return await send_from_directory('static', filename)

# 設定上傳文件路由
@app.route('/tmp/uploads/<path:filename>')
async def serve_uploads(filename):
    return await send_from_directory(settings.UPLOAD_FOLDER, filename)

@app.route("/callback", methods=['POST'])
async def callback():
    """處理 LINE Webhook"""
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.get_data(as_text=True)
    
    try:
        # 解析事件
        events = WebhookParser(settings.LINE_CHANNEL_SECRET).parse(body, signature)
        
        # 處理每個事件
        for event in events:
            if isinstance(event, FollowEvent):
                # 處理用戶關注事件
                logger.info("收到關注事件")
                await message_handler.handle_follow_event(event)
            elif isinstance(event, MessageEvent):
                if isinstance(event.message, TextMessageContent):
                    await message_handler.handle_text_message(event)
                elif isinstance(event.message, ImageMessageContent):
                    await message_handler.handle_image_message(event)
        
        logger.info("webhook 處理成功")
        return 'OK'
    except InvalidSignatureError:
        logger.error("無效的簽章")
        abort(400)
    except Exception as e:
        logger.error(f"處理 webhook 時發生錯誤：{str(e)}")
        abort(500)

if __name__ == "__main__":
    # 設定更詳細的日誌記錄
    logging.getLogger('linebot').setLevel(logging.DEBUG)
    
    # 確保上傳目錄存在
    os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
    
    # 啟動應用
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, use_reloader=True, debug=False)
