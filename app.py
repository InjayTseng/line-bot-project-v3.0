from flask import Flask, request, abort
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent
from linebot.v3.webhook import WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
import os
from datetime import datetime
import requests
import logging
import traceback
import sys

app = Flask(__name__)

# 設定日誌級別
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 設定 LINE Channel 資訊
CHANNEL_ACCESS_TOKEN = 'DWRA+HWkxIdL6/2+W+omDW7lIVnYaEO/ORyCo+rm3TtkGDzwo9dnJvSGIxke8/om+Pbj3FLr8iApjCGeeSmYkWxD67CewJfnk/nuVStpggxP+JlZCKCyDAM8plcJOdocNSt1g+/u9N+Qxne5586Y/AdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = '1d3649a096dd20c6b4e0917b3270841f'

# 設定上傳目錄
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 確保上傳目錄存在
if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER)
        app.logger.info(f"創建上傳目錄：{UPLOAD_FOLDER}")
    except Exception as e:
        app.logger.error(f"創建目錄失敗：{str(e)}")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(message_id):
    """從 LINE 下載圖片並儲存"""
    try:
        app.logger.info(f"開始處理圖片，message_id: {message_id}")
        
        # 檢查上傳目錄
        if not os.path.exists(UPLOAD_FOLDER):
            app.logger.error(f"上傳目錄不存在：{UPLOAD_FOLDER}")
            return None
            
        with ApiClient(configuration) as api_client:
            # 取得圖片內容
            app.logger.debug("準備下載圖片內容...")
            
            try:
                blob_api = MessagingApiBlob(api_client)
                message_content = blob_api.get_message_content(message_id)
                app.logger.debug("圖片內容下載完成")
            except LineBotApiError as e:
                app.logger.error(f"下載圖片失敗：{str(e)}")
                return None
            
            # 產生檔案名稱
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{message_id}.jpg"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            # 儲存圖片
            app.logger.debug(f"開始儲存圖片到: {file_path}")
            try:
                with open(file_path, 'wb') as fd:
                    fd.write(message_content)
                app.logger.info(f"圖片儲存成功: {filename}")
                return filename
            except IOError as e:
                app.logger.error(f"寫入檔案失敗：{str(e)}")
                return None
            
    except Exception as e:
        app.logger.error(f"儲存圖片時發生錯誤：{str(e)}")
        app.logger.error(traceback.format_exc())
        return None

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    try:
        user_message = event.message.text
        response_message = f"你說的是：{user_message}"
        app.logger.info(f"接收到文字訊息：{user_message}")
        
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=response_message)]
                )
            )
        app.logger.info(f"成功回覆訊息：{response_message}")
    except Exception as e:
        app.logger.error(f"回覆訊息失敗：{str(e)}")
        app.logger.error(traceback.format_exc())

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    try:
        app.logger.info(f"收到圖片訊息，message_id: {event.message.id}")
        
        # 儲存圖片
        filename = save_image(event.message.id)
        
        if filename:
            reply_text = f"已收到您的照片！\n請選擇要使用的相框樣式：\n1️⃣ 簡約風格\n2️⃣ 可愛風格\n3️⃣ 復古風格\n4️⃣ 節日風格"
            app.logger.info("圖片處理成功，準備回覆選項訊息")
        else:
            reply_text = "很抱歉，照片處理時發生錯誤，請稍後再試。"
            app.logger.error("圖片處理失敗")
        
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            app.logger.debug("準備發送回覆訊息")
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
            app.logger.info("回覆訊息發送成功")
    except Exception as e:
        app.logger.error(f"處理圖片訊息失敗：{str(e)}")
        app.logger.error(traceback.format_exc())
        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="很抱歉，系統發生錯誤，請稍後再試。")]
                    )
                )
        except:
            app.logger.error("發送錯誤訊息也失敗了")

@app.route("/callback", methods=['POST'])
def callback():
    # 確保有接收到訊息並處理
    try:
        # 從 LINE 伺服器取得訊息
        body = request.get_data(as_text=True)
        app.logger.info(f"收到 webhook 請求：{body}")

        # 使用 LINE Bot SDK 處理訊息
        signature = request.headers['X-Line-Signature']
        app.logger.debug(f"請求標頭 X-Line-Signature: {signature}")
        
        try:
            handler.handle(body, signature)
            app.logger.info("webhook 處理成功")
        except InvalidSignatureError:
            app.logger.error("無效的簽名")
            abort(400)

        return 'OK', 200
    except Exception as e:
        app.logger.error(f"處理 webhook 時發生錯誤：{str(e)}")
        app.logger.error(traceback.format_exc())
        return str(e), 500

if __name__ == "__main__":
    app.logger.info("啟動 Flask 應用程式...")
    # 修改為接受所有來源的連接
    app.run(host="0.0.0.0", port=8000, debug=True)
