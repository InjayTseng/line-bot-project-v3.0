import time
from flask import Flask, request, abort, send_from_directory, url_for
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
import dotenv

app = Flask(__name__, static_url_path='/static', static_folder='static')

# 加載環境變數
dotenv.load_dotenv()

# 確保必要的目錄存在
for directory in ['static/uploads', 'static/frames']:
    if not os.path.exists(directory):
        os.makedirs(directory)
        app.logger.info(f"已創建目錄：{directory}")

# 設定圖片路由
@app.route('/images/<path:filename>')
def serve_image(filename):
    try:
        app.logger.info(f"接收到圖片請求：{filename}")
        app.logger.info(f"請求頭部：{request.headers}")
        
        # 檢查文件是否存在
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        abs_path = os.path.abspath(file_path)
        app.logger.info(f"圖片完整路徑：{abs_path}")
        
        if not os.path.isfile(abs_path):
            app.logger.error(f"找不到圖片檔案：{abs_path}")
            return "Image not found", 404
        
        # 使用 send_from_directory 發送檔案
        try:
            response = send_from_directory(
                os.path.dirname(abs_path),
                os.path.basename(abs_path),
                mimetype='image/jpeg',
                as_attachment=False,
                max_age=31536000
            )
            
            # 設定額外的標頭
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Cache-Control'] = 'public, max-age=31536000'
            
            app.logger.info(f"圖片發送成功，響應標頭：{response.headers}")
            return response
            
        except Exception as e:
            app.logger.error(f"發送圖片時發生錯誤：{str(e)}")
            app.logger.error(traceback.format_exc())
            return str(e), 500
            
    except Exception as e:
        app.logger.error(f"處理圖片請求時發生錯誤：{str(e)}")
        app.logger.error(traceback.format_exc())
        return str(e), 500
        
    except Exception as e:
        app.logger.error(f"提供圖片時發生錯誤：{str(e)}")
        app.logger.error(traceback.format_exc())
        abort(500)

# 設定日誌級別
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 從環境變數獲取設定
CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
NGROK_URL = os.environ.get('NGROK_URL')

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise ValueError("請設置 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET 環境變數")

if not NGROK_URL:
    raise ValueError("請設置 NGROK_URL 環境變數，例如：https://xxxx-xx-xxx-xxx-xx.ngrok-free.app")

# 設定上傳目錄
# 在 Render 上使用臨時資料夾
if os.environ.get('RENDER'):
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 設定 ngrok URL（請替換成您的 ngrok URL）
NGROK_URL = os.environ.get('NGROK_URL')

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
    '可愛風格': 'cute.png',
    '復古風格': 'vintage.png'
}

# 設定相框資料夾路徑
FRAMES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/frames')

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
        frame_path = os.path.join(FRAMES_FOLDER, FRAME_FILES.get(frame_style, 'simple.png'))
        
        app.logger.debug(f"處理圖片：{input_path}")
        app.logger.debug(f"使用相框：{frame_path}")
        
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
            app.logger.debug(f"原始圖片模式：{img.mode}, 尺寸：{img.size}")
            
            # 轉換圖片模式為 RGBA
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
                app.logger.debug("已將圖片轉換為 RGBA 模式")
            
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
            
            app.logger.debug(f"調整後的目標尺寸：{target_width}x{target_height}")
            
            # 讀取相框並獲取其原始尺寸
            with Image.open(frame_path) as frame_size_check:
                frame_width, frame_height = frame_size_check.size
                frame_ratio = frame_width / frame_height
                
                # 使用相框的原始比例計算目標尺寸
                target_height = 1080
                target_width = int(target_height * frame_ratio)
            
            # 調整圖片大小，保持原始比例
            img_ratio = img.size[0] / img.size[1]
            if img_ratio > frame_ratio:
                # 如果原始圖片太寬，根據高度縮放
                new_height = target_height
                new_width = int(new_height * img_ratio)
            else:
                # 如果原始圖片太長，根據寬度縮放
                new_width = target_width
                new_height = int(new_width / img_ratio)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            app.logger.debug(f"調整後的圖片尺寸：{new_width}x{new_height}")
            
            # 創建畫布，使用相框的比例
            canvas = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
            app.logger.debug(f"創建畫布，尺寸：{target_width}x{target_height}")
            
            # 將調整後的圖片置中貼上
            paste_x = (target_width - new_width) // 2
            paste_y = (target_height - new_height) // 2
            canvas.paste(img, (paste_x, paste_y))
            app.logger.debug(f"圖片已置中貼上，位置：({paste_x}, {paste_y})")
            
            # 讀取相框並獲取其原始尺寸
            with Image.open(frame_path) as frame:
                app.logger.debug(f"相框原始模式：{frame.mode}, 尺寸：{frame.size}")
                frame_width, frame_height = frame.size
                frame_ratio = frame_width / frame_height
                
                if frame.mode != 'RGBA':
                    frame = frame.convert('RGBA')
                    app.logger.debug("已將相框轉換為 RGBA 模式")
                
                # 使用相框的原始比例計算畫布尺寸
                target_height = 1080
                target_width = int(target_height * frame_ratio)
                
                # 調整相框大小，保持原始比例
                frame = frame.resize((target_width, target_height), Image.Resampling.LANCZOS)
                app.logger.debug(f"調整後的相框尺寸：{target_width}x{target_height}")
                
                # 重新設定畫布尺寸以符合相框比例
                canvas = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
                
                # 重新計算圖片的貼上位置
                paste_x = (target_width - target_width) // 2
                paste_y = (target_height - target_height) // 2
                canvas.paste(img, (paste_x, paste_y))
                
                # 合成圖片
                try:
                    result = Image.alpha_composite(canvas, frame)
                    app.logger.debug("圖片合成成功")
                except ValueError as ve:
                    app.logger.error(f"圖片合成失敗：{str(ve)}")
                    app.logger.error(f"畫布模式：{canvas.mode}, 尺寸：{canvas.size}")
                    app.logger.error(f"相框模式：{frame.mode}, 尺寸：{frame.size}")
                    raise
                
                # 生成輸出檔名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f"processed_{timestamp}_{image_filename}"
                output_path = os.path.join(UPLOAD_FOLDER, output_filename)
                
                # 轉換為 RGB
                result = result.convert('RGB')
                
                # 調整圖片尺寸
                target_size = (800, 800)  # 使用更小的尺寸
                result.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # 確保圖片小於 200KB
                max_size_bytes = 200000  # 200KB
                quality = 80  # 降低品質
                
                # 記錄原始圖片資訊
                app.logger.info(f"原始圖片尺寸：{result.size}")
                
                # 使用自適應品質來控制檔案大小
                while quality > 60:  # 不要讓品質太低
                    # 先在記憶體中測試
                    from io import BytesIO
                    temp_buffer = BytesIO()
                    result.save(temp_buffer, 'JPEG', quality=quality)
                    size = temp_buffer.tell()
                    
                    if size <= max_size_bytes:
                        break
                    
                    quality -= 5
                    app.logger.info(f"調整品質至：{quality}, 當前大小：{size} bytes")
                
                # 儲存最終的圖片
                result.save(output_path, 'JPEG', quality=quality)
                
                # 確認最終檔案大小
                final_size = os.path.getsize(output_path)
                app.logger.info(f"圖片處理完成：{output_filename}, 最終大小：{final_size} bytes, 品質：{quality}")
                
                return output_filename
            
    except Exception as e:
        app.logger.error(f"處理圖片時發生錯誤：{str(e)}")
        app.logger.error(traceback.format_exc())
        return None

# 用戶狀態追蹤
user_states = {}  # 用來存儲用戶的狀態
FRAME_STYLES = {
    '1': '可愛風格',
    '2': '復古風格'
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
                        try:
                            # 檢查處理後的圖片路徑
                            processed_path = os.path.join(UPLOAD_FOLDER, processed_filename)
                            app.logger.info(f"處理後的圖片路徑：{processed_path}")
                            
                            # 檢查圖片是否存在
                            if not os.path.exists(processed_path):
                                app.logger.error(f"找不到處理後的圖片：{processed_path}")
                                raise Exception("圖片處理失敗")
                            
                            # 構建圖片的完整 URL
                            image_url = f"{NGROK_URL}/static/uploads/{processed_filename}"
                            app.logger.info(f"處理後的圖片 URL：{image_url}")
                            
                            # 確保 URL 是 HTTPS
                            if not image_url.startswith('https'):
                                app.logger.error(f"URL 必須是 HTTPS: {image_url}")
                                raise ValueError("URL must be HTTPS")
                            
                            # 檢查圖片大小
                            file_size = os.path.getsize(processed_path)
                            app.logger.info(f"處理後的圖片大小：{file_size} bytes")
                            
                            # 如果圖片太大，再次處理
                            if file_size > 200000:  # 如果大於 200KB
                                app.logger.info("圖片太大，再次處理")
                                with Image.open(processed_path) as img:
                                    img = img.convert('RGB')
                                    img.thumbnail((600, 600))
                                    img.save(processed_path, 'JPEG', quality=70, optimize=True)
                                file_size = os.path.getsize(processed_path)
                                app.logger.info(f"再次處理後的圖片大小：{file_size} bytes")
                            
                            # 只檢查本地檔案是否存在和大小
                            if not os.path.exists(processed_path):
                                app.logger.error(f"找不到處理後的圖片：{processed_path}")
                                raise Exception("圖片處理失敗")
                            
                            # 檢查圖片大小
                            file_size = os.path.getsize(processed_path)
                            app.logger.info(f"圖片大小：{file_size} bytes")

                            # 檢查圖片檔案路徑
                            processed_path = os.path.join(UPLOAD_FOLDER, processed_filename)
                            app.logger.info(f"處理後的圖片路徑：{processed_path}")
                            
                            # 檢查圖片大小
                            file_size = os.path.getsize(processed_path)
                            app.logger.info(f"圖片大小：{file_size} bytes")
                            
                            # 如果圖片太大，嘗試再次處理
                            if file_size > 300000:  # 如果大於 300KB
                                app.logger.info("圖片太大，嘗試再次處理")
                                with Image.open(processed_path) as img:
                                    img = img.convert('RGB')
                                    # 降低尺寸
                                    img.thumbnail((600, 600))
                                    # 降低品質
                                    img.save(processed_path, 'JPEG', quality=70, optimize=True)
                                file_size = os.path.getsize(processed_path)
                                app.logger.info(f"重新處理後的圖片大小：{file_size} bytes")
                            
                            # 檢查圖片 URL 是否可訪問
                            try:
                                # 使用專用的圖片路由
                                image_url = f"{NGROK_URL}/images/{processed_filename}"
                                app.logger.info(f"圖片 URL：{image_url}")
                                
                                response = requests.head(image_url)
                                app.logger.info(f"圖片 URL 響應狀態碼：{response.status_code}")
                                app.logger.info(f"圖片 URL 響應標頭：{response.headers}")
                                
                                if response.status_code != 200:
                                    raise Exception(f"圖片 URL 無法訪問，狀態碼：{response.status_code}")
                                
                                # 只發送圖片訊息
                                messages = [
                                    ImageMessage(
                                        originalContentUrl=image_url,
                                        previewImageUrl=image_url
                                    )
                                ]
                                
                                app.logger.info("已創建 LINE 圖片訊息")
                                
                                with ApiClient(configuration) as api_client:
                                    line_bot_api = MessagingApi(api_client)
                                    response = line_bot_api.reply_message_with_http_info(
                                        ReplyMessageRequest(
                                            reply_token=event.reply_token,
                                            messages=messages
                                        )
                                    )
                                    app.logger.info(f"訊息發送成功，響應：{response}")
                                    
                                    # 設定延遲刪除的時間，確保 LINE 有足夠時間獲取圖片
                                    def delayed_cleanup(original_path, processed_path, delay_seconds=300):  # 5 分鐘後刪除
                                        try:
                                            time.sleep(delay_seconds)
                                            # 刪除原始圖片
                                            if os.path.exists(original_path):
                                                os.remove(original_path)
                                                app.logger.info(f"原始圖片已刪除：{original_path}")
                                            
                                            # 刪除處理後的圖片
                                            if os.path.exists(processed_path):
                                                os.remove(processed_path)
                                                app.logger.info(f"處理後的圖片已刪除：{processed_path}")
                                        except Exception as e:
                                            app.logger.error(f"刪除圖片時發生錯誤：{str(e)}")
                                    
                                    # 啟動一個新的執行緒來處理延遲刪除
                                    import threading
                                    original_path = os.path.join(UPLOAD_FOLDER, image_filename)
                                    cleanup_thread = threading.Thread(
                                        target=delayed_cleanup,
                                        args=(original_path, processed_path),
                                        daemon=True
                                    )
                                    cleanup_thread.start()
                                    app.logger.info("已啟動延遲刪除執行緒")
                                    
                            except Exception as e:
                                app.logger.error(f"發送圖片訊息時發生錯誤：{str(e)}")
                                # 如果發生錯誤，發送錯誤訊息
                                with ApiClient(configuration) as api_client:
                                    line_bot_api = MessagingApi(api_client)
                                    line_bot_api.reply_message_with_http_info(
                                        ReplyMessageRequest(
                                            reply_token=event.reply_token,
                                            messages=[TextMessage(text="圖片處理失敗，請再試一次。")]
                                        )
                                    )
                        except Exception as e:
                            app.logger.error(f"發送圖片訊息失敗：{str(e)}")
                            app.logger.error(traceback.format_exc())
                            raise
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
                response_message = f"您好，您輸入了：{user_message}\n請上傳一張圖片繼續。"
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
            reply_text = f"已收到您的照片！\n請選擇要使用的相框樣式：\n1️⃣ 可愛風格\n2️⃣ 復古風格"
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
    # 設定更詳細的日誌記錄
    logging.getLogger('linebot').setLevel(logging.DEBUG)
    
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
