from flask import Flask, request, abort
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    TextMessage,
    ImageMessage
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
from PIL import Image

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

# 設定 ngrok URL（請替換成您的 ngrok URL）
NGROK_URL = 'https://06e4-124-218-234-7.ngrok-free.app'

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

# 設定相框樣式對應的檔案名稱
FRAME_FILES = {
    '簡約風格': 'simple.png',
    '可愛風格': 'cute.png',
    '復古風格': 'vintage.png',
    '節日風格': 'holiday.png'
}

def process_image_with_frame(image_filename, frame_style):
    """
    將用戶的圖片與選擇的框架合成
    
    Args:
        image_filename (str): 原始圖片的檔名
        frame_style (str): 選擇的框架樣式
        
    Returns:
        str: 處理後的圖片檔名，如果處理失敗則返回 None
    """
    try:
        # 構建檔案路徑
        input_path = os.path.join(UPLOAD_FOLDER, image_filename)
        frame_path = os.path.join('static/frames', FRAME_FILES.get(frame_style, 'simple.png'))
        
        # 檢查輸入檔案是否存在
        if not os.path.exists(input_path):
            app.logger.error(f"找不到原始圖片：{input_path}")
            return None
            
        # 檢查相框檔案是否存在
        if not os.path.exists(frame_path):
            app.logger.error(f"找不到相框圖片：{frame_path}")
            return None
            
        # 讀取原始圖片
        with Image.open(input_path) as img:
            # 轉換圖片模式為 RGBA
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # 獲取原始尺寸
            original_width, original_height = img.size
            
            # 計算目標尺寸（保持原始比例）
            if original_width > original_height:
                # 橫向照片
                target_height = 1080
                target_width = int(original_width * (target_height / original_height))
            else:
                # 直向照片
                target_width = 1080
                target_height = int(original_height * (target_width / original_width))
            
            # 調整圖片大小，保持原始比例
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # 創建一個新的正方形畫布（1080x1080，透明背景）
            canvas = Image.new('RGBA', (1080, 1080), (0, 0, 0, 0))
            
            # 將調整後的圖片置中貼上
            paste_x = (1080 - target_width) // 2
            paste_y = (1080 - target_height) // 2
            canvas.paste(img, (paste_x, paste_y))
            
            # 讀取相框
            with Image.open(frame_path) as frame:
                if frame.mode != 'RGBA':
                    frame = frame.convert('RGBA')
                
                # 合成圖片
                result = Image.alpha_composite(canvas, frame)
                
                # 生成輸出檔名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f"processed_{timestamp}_{image_filename}"
                output_path = os.path.join(UPLOAD_FOLDER, output_filename)
                
                # 儲存處理後的圖片，使用高品質設定
                result = result.convert('RGB')  # LINE 不支援 RGBA
                result.save(output_path, 'JPEG', quality=95)
                app.logger.info(f"圖片處理完成：{output_filename}")
                
                return output_filename
            
    except Exception as e:
        app.logger.error(f"處理圖片時發生錯誤：{str(e)}")
        app.logger.error(traceback.format_exc())
        return None

# 用戶狀態追蹤
user_states = {}  # 用來存儲用戶的狀態
FRAME_STYLES = {
    '1': '簡約風格',
    '2': '可愛風格',
    '3': '復古風格',
    '4': '節日風格'
}

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    try:
        user_id = event.source.user_id
        user_message = event.message.text
        app.logger.info(f"接收到文字訊息：{user_message}")
        
        # 檢查用戶是否在等待選擇框架
        if user_id in user_states and 'waiting_for_frame' in user_states[user_id]:
            # 驗證用戶的選擇
            if user_message in FRAME_STYLES:
                # 儲存用戶的選擇
                frame_style = FRAME_STYLES[user_message]
                user_states[user_id]['frame_style'] = frame_style
                
                # 處理圖片
                image_filename = user_states[user_id].get('image_filename')
                if image_filename:
                    processed_filename = process_image_with_frame(image_filename, frame_style)
                    if processed_filename:
                        # 構建圖片的完整 URL（使用 HTTPS）
                        image_url = f"{NGROK_URL}/static/uploads/{processed_filename}"
                        app.logger.info(f"處理後的圖片 URL：{image_url}")
                        
                        # 回傳文字訊息和圖片
                        with ApiClient(configuration) as api_client:
                            line_bot_api = MessagingApi(api_client)
                            line_bot_api.reply_message_with_http_info(
                                ReplyMessageRequest(
                                    reply_token=event.reply_token,
                                    messages=[
                                        TextMessage(text=f"您的照片已處理完成！\n框架樣式：{frame_style}"),
                                        ImageMessage(
                                            originalContentUrl=image_url,
                                            previewImageUrl=image_url
                                        )
                                    ]
                                )
                            )
                        app.logger.info(f"用戶 {user_id} 的圖片處理完成：{processed_filename}")
                        return
                    else:
                        response_message = "很抱歉，圖片處理失敗，請重新上傳照片。"
                        app.logger.error(f"用戶 {user_id} 的圖片處理失敗")
                else:
                    response_message = "找不到您的照片，請重新上傳。"
                    app.logger.error(f"找不到用戶 {user_id} 的原始圖片")
                
                # 清除用戶狀態
                user_states.pop(user_id, None)
            else:
                response_message = f"請選擇有效的框架樣式（1-4）：\n1️⃣ 簡約風格\n2️⃣ 可愛風格\n3️⃣ 復古風格\n4️⃣ 節日風格"
                app.logger.warning(f"用戶 {user_id} 輸入了無效的選擇：{user_message}")
        else:
            response_message = "請先傳送一張照片給我"
            app.logger.warning(f"用戶 {user_id} 在未上傳圖片的情況下發送了訊息")
        
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=response_message)]
                )
            )
            
    except Exception as e:
        app.logger.error(f"處理文字訊息時發生錯誤：{str(e)}")
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

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    try:
        app.logger.info(f"收到圖片訊息，message_id: {event.message.id}")
        
        # 儲存圖片
        filename = save_image(event.message.id)
        
        if filename:
            reply_text = f"已收到您的照片！\n請選擇要使用的相框樣式：\n1️⃣ 簡約風格\n2️⃣ 可愛風格\n3️⃣ 復古風格\n4️⃣ 節日風格"
            app.logger.info("圖片處理成功，準備回覆選項訊息")
            
            # 記錄用戶狀態
            user_id = event.source.user_id
            user_states[user_id] = {
                'waiting_for_frame': True,
                'image_filename': filename
            }
            app.logger.debug(f"用戶狀態已更新：{user_states[user_id]}")
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
    port = int(os.environ.get("PORT", 8001))
    app.run(host="0.0.0.0", port=port)
