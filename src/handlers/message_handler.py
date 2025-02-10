import os
import logging
from datetime import datetime
from src.config import settings
from src.services.line_service import LineService
from src.services.image_service import ImageService

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self):
        self.line_service = LineService()
        self.image_service = ImageService()
        self.user_states = {}  # 用來存儲用戶的狀態

    def handle_text_message(self, event):
        """處理文字訊息"""
        user_id = event.source.user_id
        text = event.message.text

        if user_id in self.user_states:
            # 用戶已上傳圖片，正在選擇框架
            if text in ['1', '2', '3', '4']:
                frame_style = settings.FRAME_STYLES.get(text)
                if not frame_style:
                    self.line_service.reply_text(event.reply_token, "無效的選擇，請重新選擇框架風格。")
                    return

                image_filename = self.user_states[user_id]
                try:
                    # 處理圖片
                    processed_filename = self.image_service.process_image_with_frame(image_filename, frame_style)
                    if not processed_filename:
                        self.line_service.reply_text(event.reply_token, "圖片處理失敗，請重新上傳照片。")
                        return

                    # 上傳到 Cloudinary
                    processed_path = os.path.join(settings.UPLOAD_FOLDER, processed_filename)
                    cloudinary_url = self.image_service.upload_to_cloudinary(processed_path)

                    # 清理檔案
                    try:
                        os.remove(processed_path)
                        logger.info(f"已刪除臨時檔案：{processed_path}")
                    except:
                        pass

                    # 清理原始圖片
                    original_path = os.path.join(settings.UPLOAD_FOLDER, image_filename)
                    try:
                        os.remove(original_path)
                        logger.info(f"清理原始圖片：{original_path}")
                    except:
                        pass

                    # 清理使用者狀態
                    del self.user_states[user_id]
                    logger.info(f"已清理使用者狀態：{user_id}")

                    # 發送處理後的圖片
                    self.line_service.reply_image(event.reply_token, cloudinary_url)

                except Exception as e:
                    logger.error(f"處理圖片時發生錯誤：{str(e)}")
                    self.line_service.reply_text(event.reply_token, "抱歉，處理圖片時發生錯誤。")
            else:
                self.line_service.reply_text(
                    event.reply_token,
                    "請選擇框架風格：\n1. 可愛風格\n2. 復古風格\n3. 簡約風格\n4. 華麗風格"
                )
        else:
            # 用戶尚未上傳圖片
            self.line_service.reply_text(event.reply_token, "請上傳一張照片，讓我為您加上精美的框架！")

    def handle_image_message(self, event):
        """處理圖片訊息"""
        try:
            message_content = self.line_service.get_message_content(event.message.id)
            
            # 生成檔案名稱
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"{timestamp}_{event.message.id}.jpg"
            image_path = os.path.join(settings.UPLOAD_FOLDER, image_filename)
            
            # 儲存圖片
            with open(image_path, 'wb') as f:
                f.write(message_content)
            
            # 檢查檔案是否成功儲存
            if not os.path.exists(image_path):
                self.line_service.reply_text(event.reply_token, "圖片儲存失敗，請重新上傳。")
                return
                
            # 更新用戶狀態
            self.user_states[event.source.user_id] = image_filename
            
            # 回覆訊息
            self.line_service.reply_text(
                event.reply_token,
                "請選擇框架風格：\n1. 可愛風格\n2. 復古風格"
            )
            
        except Exception as e:
            logger.error(f"處理圖片訊息時發生錯誤：{str(e)}")
            self.line_service.reply_text(event.reply_token, "圖片處理失敗，請重新上傳。")
