import os
import logging
from datetime import datetime
from linebot.v3.messaging import ImageMessage, TextMessage
from src.config import settings
from src.services.line_service import LineService
from src.services.image_service import ImageService
from src.services.printer_service import PrinterService

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self):
        self.line_service = LineService()
        self.image_service = ImageService()
        self.user_states = {}  # 用來存儲用戶的狀態

    async def handle_text_message(self, event):
        """處理文字訊息"""
        user_id = event.source.user_id
        text = event.message.text

        if user_id in self.user_states:
            # 檢查是否要列印
            if text.lower() == 'print':
                if 'processed_image' not in self.user_states[user_id]:
                    await self.line_service.reply_text(event.reply_token, "請先上傳照片。")
                    return
                
                try:
                    # 取得處理後的圖片路徑
                    processed_path = self.user_states[user_id]['processed_path']
                    
                    # 列印圖片
                    printer_service = PrinterService()
                    
                    # 列印完成回調
                    async def on_print_complete():
                        try:
                            # 發送完成訊息
                            await self.line_service.push_message(
                                event.source.user_id,
                                TextMessage(text="列印完成！")
                            )
                            
                            # 清理檔案
                            try:
                                os.remove(processed_path)
                                logger.info(f"已刪除臨時檔案：{processed_path}")
                            except Exception as e:
                                logger.error(f"刪除臨時檔案失敗：{str(e)}")

                            # 清理原始圖片
                            original_path = self.user_states[user_id]['original_path']
                            try:
                                os.remove(original_path)
                                logger.info(f"清理原始圖片：{original_path}")
                            except Exception as e:
                                logger.error(f"刪除原始圖片失敗：{str(e)}")

                            # 清理使用者狀態
                            del self.user_states[user_id]
                            logger.info(f"已清理使用者狀態：{user_id}")
                            
                        except Exception as e:
                            logger.error(f"列印完成回調失敗：{str(e)}")
                    
                    await printer_service.print_photo(processed_path, on_print_complete)
                    
                    # 回覆等待訊息
                    await self.line_service.reply_text(event.reply_token, "等待列印中...")
                    return
                except Exception as e:
                    logger.error(f"列印失敗：{str(e)}")
                    await self.line_service.reply_text(event.reply_token, "列印失敗，請稍後再試。")
                    return
            else:
                await self.line_service.reply_text(
                    event.reply_token,
                    "您的照片已處理完成！如果想要繼續處理其他照片，請直接上傳新的圖片。\n或是打 'Print' 進行列印。"
                )
        else:
            # 用戶尚未上傳圖片
            await self.line_service.reply_text(event.reply_token, "請上傳一張照片，讓我為您加上精美的框架！")

    async def handle_image_message(self, event):
        """處理圖片訊息"""
        try:
            message_content = await self.line_service.get_message_content(event.message.id)
            
            # 生成檔案名稱
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"{timestamp}_{event.message.id}.jpg"
            image_path = os.path.join(settings.UPLOAD_FOLDER, image_filename)
            
            # 儲存圖片
            with open(image_path, 'wb') as f:
                f.write(message_content)
            
            # 檢查檔案是否成功儲存
            if not os.path.exists(image_path):
                await self.line_service.reply_text(event.reply_token, "圖片儲存失敗，請重新上傳。")
                return
                
            # 更新用戶狀態
            self.user_states[event.source.user_id] = {
                'image': image_filename,
                'upload_time': datetime.now().isoformat()
            }
            
            # 直接使用預設框架處理圖片
            frame_style = settings.DEFAULT_FRAME_STYLE
            try:
                # 處理圖片
                processed_filename = await self.image_service.process_image_with_frame(image_filename, frame_style)
                if not processed_filename:
                    await self.line_service.reply_text(event.reply_token, "圖片處理失敗，請重新上傳照片。")
                    return

                # 儲存處理後的圖片檔名
                self.user_states[event.source.user_id]['processed_image'] = processed_filename
                
                # 上傳到 Cloudinary
                try:
                    processed_path = os.path.join(settings.UPLOAD_FOLDER, processed_filename)
                    cloudinary_url = await self.image_service.upload_to_cloudinary(processed_path)
                    if not cloudinary_url:
                        raise Exception("上傳到 Cloudinary 失敗")
                    
                    # 記錄 Cloudinary URL
                    logger.info(f"Cloudinary URL: {cloudinary_url}")
                except Exception as e:
                    logger.error(f"上傳到 Cloudinary 失敗：{str(e)}")
                    await self.line_service.reply_text(event.reply_token, "圖片上傳失敗，請稍後再試。")
                    return

                # 儲存處理後的圖片路徑
                self.user_states[event.source.user_id]['processed_path'] = processed_path
                self.user_states[event.source.user_id]['original_path'] = os.path.join(settings.UPLOAD_FOLDER, image_filename)
                self.user_states[event.source.user_id]['cloudinary_url'] = cloudinary_url

                try:
                    # 發送處理後的圖片和完成訊息
                    image_message = ImageMessage(
                        original_content_url=cloudinary_url,
                        preview_image_url=cloudinary_url
                    )
                    text_message = TextMessage(text="您的照片已處理完成！如果想要繼續處理其他照片，請直接上傳新的圖片。\n或是打 'Print' 進行列印。")
                    
                    # 先嘗試單獨發送圖片
                    await self.line_service.reply_message(
                        event.reply_token,
                        [image_message, text_message]
                    )
                except Exception as e:
                    logger.error(f"發送圖片訊息失敗：{str(e)}")
                    # 如果發送失敗，嘗試只發送文字訊息
                    try:
                        await self.line_service.reply_text(
                            event.reply_token, 
                            f"您的照片已處理完成！圖片可在此查看：{cloudinary_url}\n如果想要繼續處理其他照片，請直接上傳新的圖片。\n或是打 'Print' 進行列印。"
                        )
                    except Exception as text_error:
                        logger.error(f"發送文字訊息也失敗：{str(text_error)}")

            except Exception as e:
                logger.error(f"處理圖片時發生錯誤：{str(e)}")
                await self.line_service.reply_text(event.reply_token, "抱歉，處理圖片時發生錯誤。")
            
        except Exception as e:
            logger.error(f"處理圖片訊息時發生錯誤：{str(e)}")
            await self.line_service.reply_text(event.reply_token, "圖片處理失敗，請重新上傳。")
