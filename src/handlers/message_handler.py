import os
import logging
import traceback
from datetime import datetime
from linebot.v3.messaging import ImageMessage, TextMessage, TemplateMessage, MessageAction, ConfirmTemplate, URIAction
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
        
        # 歡迎訊息和使用說明
        self.welcome_message = (
            "🌟 歡迎使用照片相框合成機器人！ 🌟\n\n"
            "這個機器人可以將您的照片與精美相框合成，創造獨特的回憶。\n\n"
            "📸 使用方法：\n"
            "1. 直接上傳一張照片\n"
            "2. 選擇您喜歡的相框風格\n"
            "3. 等待處理完成後，您可以選擇列印或分享\n\n"
            "🔍 小提示：\n"
            "• 一次只能處理一張照片\n"
            "• 支援直式和橫式照片\n"
            "• 照片會自動調整大小和位置\n"
            "• 輸入「幫助」或「說明」可再次查看此訊息\n\n"
            "開始使用吧！上傳您的第一張照片 📤"
        )
        
        # 幫助關鍵字列表
        self.help_keywords = ["幫助", "說明", "help", "指南", "怎麼用", "如何使用"]

    async def handle_follow_event(self, event):
        """處理用戶關注事件"""
        try:
            user_id = event.source.user_id
            logger.info(f"新用戶關注：{user_id}")
            
            # 發送歡迎訊息
            await self.line_service.reply_text(event.reply_token, self.welcome_message)
            
            # 清除該用戶的狀態（如果有）
            if user_id in self.user_states:
                del self.user_states[user_id]
                
            logger.info(f"已發送歡迎訊息給用戶：{user_id}")
        except Exception as e:
            logger.error(f"處理關注事件時發生錯誤：{str(e)}")
            logger.error(traceback.format_exc())

    async def handle_text_message(self, event):
        """處理文字訊息"""
        user_id = event.source.user_id
        text = event.message.text
        
        # 檢查是否為幫助關鍵字
        if text.lower() in [keyword.lower() for keyword in self.help_keywords]:
            logger.info(f"用戶 {user_id} 請求幫助")
            await self.line_service.reply_text(event.reply_token, self.welcome_message)
            return
            
        # 處理「繼續上傳」的回應
        if text == "繼續上傳":
            logger.info(f"用戶 {user_id} 選擇繼續上傳")
            await self.line_service.reply_text(
                event.reply_token,
                "請上傳您想要處理的下一張照片。"
            )
            return

        if user_id in self.user_states:
            # 檢查是否要列印
            if text.lower() == 'print':
                try:
                    # 檢查用戶是否有上傳過照片
                    if user_id in self.user_states and 'processed_path' in self.user_states[user_id]:
                        # 提供詳細的 Epson Printer LINE Bot 使用指南（第一條消息）
                        guide_message = (
                            "請按照以下步驟使用 Epson Printer LINE Bot 列印您的照片：\n\n"
                            "1. 點進 Epson Printer LINE BOT\n"
                            "2. 選擇「印表機管理」\n"
                            "3. 選擇「印表機登入」\n"
                            "4. 輸入印表機郵件地址：pma16577avrgx6\n"
                            "5. 印表機名稱：任意取名\n\n"
                            "請點此前往印表機 BOT：https://line.me/R/ti/p/%40199utzga"
                        )
                        
                        # 發送第一條消息（使用指南）
                        await self.line_service.reply_text(
                            event.reply_token, 
                            guide_message
                        )
                        
                        # 發送第二條消息（只有印表機郵件地址，方便複製）
                        await self.line_service.push_message(
                            user_id,
                            TextMessage(text="pma16577avrgx6")
                        )
                        
                        return
                    else:
                        await self.line_service.reply_text(event.reply_token, "請先上傳一張照片，然後再嘗試列印。")
                        return
                except Exception as e:
                    logger.error(f"列印處理失敗：{str(e)}")
                    logger.error(traceback.format_exc())
                    await self.line_service.reply_text(event.reply_token, "照片列印失敗，請稍後再試。")
            else:
                await self.line_service.reply_text(
                    event.reply_token,
                    "您的照片已處理完成！如果想要繼續處理其他照片，請直接上傳新的圖片。\n或是點選「列印設定」按鈕進行列印。"
                )
        else:
            # 用戶尚未上傳圖片
            await self.line_service.reply_text(event.reply_token, "請上傳一張照片，讓我為您加上精美的框架！")

    async def handle_image_message(self, event):
        """處理圖片訊息"""
        try:
            logger.info(f"開始處理圖片訊息: {event.message.id}")
            message_content = await self.line_service.get_message_content(event.message.id)
            
            # 生成檔案名稱
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"{timestamp}_{event.message.id}.jpg"
            image_path = os.path.join(settings.UPLOAD_FOLDER, image_filename)
            logger.info(f"生成圖片檔名: {image_filename}")
            
            # 儲存圖片
            with open(image_path, 'wb') as f:
                f.write(message_content)
            
            # 檢查檔案是否成功儲存
            if not os.path.exists(image_path):
                logger.error(f"圖片儲存失敗: {image_path}")
                await self.line_service.reply_text(event.reply_token, "圖片儲存失敗，請重新上傳。")
                return
                
            # 更新用戶狀態
            self.user_states[event.source.user_id] = {
                'image': image_filename,
                'upload_time': datetime.now().isoformat()
            }
            logger.info(f"更新用戶狀態: {event.source.user_id}")
            
            # 自動判斷照片方向並處理圖片
            try:
                # 處理圖片，不指定框架風格，讓系統自動判斷
                logger.info(f"開始處理圖片: {image_filename}")
                processed_filename = await self.image_service.process_image_with_frame(image_filename)
                if not processed_filename:
                    logger.error(f"圖片處理失敗: {image_filename}")
                    await self.line_service.reply_text(event.reply_token, "圖片處理失敗，請重新上傳照片。")
                    return

                # 儲存處理後的圖片檔名
                self.user_states[event.source.user_id]['processed_image'] = processed_filename
                logger.info(f"處理後的圖片檔名: {processed_filename}")
                
                # 上傳到 Cloudinary
                try:
                    processed_path = os.path.join(settings.UPLOAD_FOLDER, processed_filename)
                    logger.info(f"開始上傳到 Cloudinary: {processed_path}")
                    cloudinary_url = await self.image_service.upload_to_cloudinary(processed_path)
                    if not cloudinary_url:
                        logger.error(f"上傳到 Cloudinary 失敗: {processed_path}")
                        raise Exception("上傳到 Cloudinary 失敗")
                    
                    # 記錄 Cloudinary URL
                    logger.info(f"Cloudinary URL: {cloudinary_url}")
                except Exception as e:
                    logger.error(f"上傳到 Cloudinary 失敗：{str(e)}")
                    logger.error(traceback.format_exc())
                    await self.line_service.reply_text(event.reply_token, "圖片上傳失敗，請稍後再試。")
                    return

                # 儲存處理後的圖片路徑
                self.user_states[event.source.user_id]['processed_path'] = processed_path
                self.user_states[event.source.user_id]['original_path'] = os.path.join(settings.UPLOAD_FOLDER, image_filename)
                self.user_states[event.source.user_id]['cloudinary_url'] = cloudinary_url

                try:
                    # 發送處理後的圖片
                    logger.info(f"準備發送處理後的圖片: {cloudinary_url}")
                    image_message = ImageMessage(
                        original_content_url=cloudinary_url,
                        preview_image_url=cloudinary_url
                    )
                    
                    # 檢查是否為直式照片
                    is_portrait = "portrait" in processed_filename
                    logger.info(f"照片方向: {'直式' if is_portrait else '橫式'}")
                    
                    if is_portrait:
                        # 對於直式照片，嘗試使用 push_image 而不是 push_message
                        logger.info(f"直式照片: 使用 push_image 發送")
                        try:
                            # 先發送文字訊息作為回覆
                            await self.line_service.reply_text(
                                event.reply_token, 
                                "您的照片已處理完成！正在準備圖片..."
                            )
                            
                            # 然後使用 push_image 發送圖片
                            await self.line_service.push_image(
                                event.source.user_id,
                                cloudinary_url
                            )
                            
                            # 發送確認模板訊息
                            await self.line_service.push_message(
                                event.source.user_id,
                                TemplateMessage(
                                    alt_text="請選擇下一步操作",
                                    template=ConfirmTemplate(
                                        text="您想要列印這張照片嗎？",
                                        actions=[
                                            MessageAction(label="列印設定", text="Print"),
                                            MessageAction(label="繼續上傳", text="繼續上傳")
                                        ]
                                    )
                                )
                            )
                            
                            logger.info(f"直式照片: push_image 和確認模板發送成功")
                        except Exception as push_error:
                            logger.error(f"使用 push_image 發送直式照片失敗: {str(push_error)}")
                            logger.error(traceback.format_exc())
                            # 如果 push_image 失敗，嘗試使用 reply_image
                            try:
                                logger.info(f"嘗試使用 reply_image 發送直式照片")
                                await self.line_service.reply_image(
                                    event.reply_token,
                                    cloudinary_url
                                )
                                logger.info(f"使用 reply_image 發送直式照片成功")
                                
                                # 發送確認模板訊息
                                await self.line_service.push_message(
                                    event.source.user_id,
                                    TemplateMessage(
                                        alt_text="請選擇下一步操作",
                                        template=ConfirmTemplate(
                                            text="您想要列印這張照片嗎？",
                                            actions=[
                                                MessageAction(label="列印設定", text="Print"),
                                                MessageAction(label="繼續上傳", text="繼續上傳")
                                            ]
                                        )
                                    )
                                )
                            except Exception as reply_image_error:
                                logger.error(f"使用 reply_image 發送直式照片失敗: {str(reply_image_error)}")
                                logger.error(traceback.format_exc())
                                # 如果還是失敗，嘗試只發送文字訊息
                                await self.line_service.reply_text(
                                    event.reply_token, 
                                    f"您的照片已處理完成！圖片可在此查看：{cloudinary_url}\n請點選「列印設定」按鈕進行列印，或直接上傳新照片繼續處理。"
                                )
                    else:
                        # 對於橫式照片，先發送圖片，然後發送確認模板
                        logger.info(f"橫式照片: 使用 reply_message 發送圖片，然後發送確認模板")
                        
                        # 先發送圖片
                        await self.line_service.reply_message(
                            event.reply_token,
                            [image_message]
                        )
                        logger.info(f"橫式照片: 圖片發送成功")
                        
                        # 然後發送確認模板訊息
                        try:
                            await self.line_service.push_message(
                                event.source.user_id,
                                TemplateMessage(
                                    alt_text="請選擇下一步操作",
                                    template=ConfirmTemplate(
                                        text="您想要列印這張照片嗎？",
                                        actions=[
                                            MessageAction(label="列印設定", text="Print"),
                                            MessageAction(label="繼續上傳", text="繼續上傳")
                                        ]
                                    )
                                )
                            )
                            logger.info(f"橫式照片: 確認模板發送成功")
                        except Exception as template_error:
                            logger.error(f"發送確認模板失敗: {str(template_error)}")
                            logger.error(traceback.format_exc())
                            # 如果發送確認模板失敗，發送普通文字訊息
                            await self.line_service.push_message(
                                event.source.user_id,
                                TextMessage(text="請點選「列印設定」按鈕進行列印，或直接上傳新照片繼續處理。")
                            )
                except Exception as e:
                    logger.error(f"發送圖片訊息失敗：{str(e)}")
                    logger.error(traceback.format_exc())
                    # 如果發送失敗，嘗試只發送文字訊息
                    try:
                        logger.info(f"嘗試只發送文字訊息: {cloudinary_url}")
                        await self.line_service.reply_text(
                            event.reply_token, 
                            f"您的照片已處理完成！圖片可在此查看：{cloudinary_url}\n請點選「列印設定」按鈕進行列印，或直接上傳新照片繼續處理。"
                        )
                        logger.info(f"文字訊息發送成功: {cloudinary_url}")
                    except Exception as text_error:
                        logger.error(f"發送文字訊息也失敗：{str(text_error)}")
                        logger.error(traceback.format_exc())

            except Exception as e:
                logger.error(f"處理圖片時發生錯誤：{str(e)}")
                logger.error(traceback.format_exc())
                await self.line_service.reply_text(event.reply_token, "抱歉，處理圖片時發生錯誤。")
            
        except Exception as e:
            logger.error(f"處理圖片訊息時發生錯誤：{str(e)}")
            logger.error(traceback.format_exc())
            await self.line_service.reply_text(event.reply_token, "圖片處理失敗，請重新上傳。")
