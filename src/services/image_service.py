import os
import logging
from PIL import Image
import cloudinary
import cloudinary.uploader
from src.config import settings

logger = logging.getLogger(__name__)

class ImageService:
    @staticmethod
    def allowed_file(filename):
        """檢查檔案是否為允許的類型"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in settings.ALLOWED_EXTENSIONS

    @staticmethod
    async def process_image_with_frame(image_filename, frame_style):
        """
        將用戶的圖片與選擇的框架合成
        
        Args:
            image_filename (str): 原始圖片的檔名
            frame_style (str): 選擇的框架樣式
            
        Returns:
            str: 處理後的圖片檔名，如果處理失敗則返回 None
        """
        try:
            import asyncio
            # 構建檔案路徑
            image_path = os.path.join(settings.UPLOAD_FOLDER, image_filename)
            frame_filename = settings.FRAME_FILES.get(frame_style)
            if not frame_filename:
                logger.error(f"找不到對應的框架檔案：{frame_style}")
                return None
                
            frame_path = os.path.join('static', 'frames', frame_filename)
            
            # 檢查檔案是否存在
            if not os.path.exists(image_path):
                logger.error(f"找不到原始圖片：{image_path}")
                return None
            if not os.path.exists(frame_path):
                logger.error(f"找不到框架圖片：{frame_path}")
                return None
            
            # 在線程池中執行同步的圖片處理操作
            def process_image():
                # 讀取圖片
                with Image.open(image_path) as user_image, Image.open(frame_path) as frame_image:
                    # 獲取原始圖片和框架尺寸
                    user_width, user_height = user_image.size
                    frame_width, frame_height = frame_image.size
                    
                    # 創建一個新的空白圖像，大小與框架相同
                    result = Image.new('RGBA', (frame_width, frame_height), (0, 0, 0, 0))
                    
                    # 計算單個照片在框架中的最大可用寬度和高度
                    # 我們將框架高度的一半作為單個照片的最大高度（上下排列）
                    max_photo_width = frame_width
                    max_photo_height = frame_height // 2
                    
                    # 計算縮放比例，保持原始照片的長寬比
                    width_ratio = max_photo_width / user_width
                    height_ratio = max_photo_height / user_height
                    ratio = min(width_ratio, height_ratio) * 0.9  # 縮小10%以確保有邊距
                    
                    # 縮放用戶圖片
                    new_width = int(user_width * ratio)
                    new_height = int(user_height * ratio)
                    user_image_resized = user_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # 將用戶圖片轉換為 RGBA 模式
                    user_image_resized = user_image_resized.convert('RGBA')
                    
                    # 計算第一張照片的位置（上方）
                    x_offset = (frame_width - new_width) // 2
                    y_offset_top = (max_photo_height - new_height) // 2
                    
                    # 計算第二張照片的位置（下方）
                    y_offset_bottom = max_photo_height + (max_photo_height - new_height) // 2
                    
                    # 將第一張照片粘貼到結果圖像上（上方）
                    result.paste(user_image_resized, (x_offset, y_offset_top), user_image_resized)
                    
                    # 將第二張照片粘貼到結果圖像上（下方）
                    result.paste(user_image_resized, (x_offset, y_offset_bottom), user_image_resized)
                    
                    # 將框架粘貼到結果圖像上
                    result.paste(frame_image, (0, 0), frame_image)
                    
                    # 生成新檔名
                    timestamp = image_filename.split('_')[0]  # 取得時間戳記
                    processed_filename = f"processed_{timestamp}_{image_filename}"
                    processed_path = os.path.join(settings.UPLOAD_FOLDER, processed_filename)
                    
                    # 縮小圖片尺寸以減小文件大小
                    max_size = (1024, 1024)  # 最大尺寸為 1024x1024
                    result.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # 儲存處理後的圖片（轉換為 RGB 以移除透明度）
                    result = result.convert('RGB')
                    result.save(processed_path, 'JPEG', quality=85, optimize=True)  # 降低品質以減小文件大小
                    
                    # 記錄處理後的圖片大小
                    file_size = os.path.getsize(processed_path)
                    logger.info(f"圖片處理完成：{processed_path}")
                    logger.info(f"處理後的圖片大小：{file_size} bytes")
                    
                    return processed_filename
            
            # 在線程池中執行同步操作
            return await asyncio.to_thread(process_image)
                
        except Exception as e:
            logger.error(f"處理圖片時發生錯誤：{str(e)}")
            return None

    @staticmethod
    async def upload_to_cloudinary(image_path):
        """上傳圖片到 Cloudinary"""
        try:
            # 檢查 Cloudinary 配置是否完整
            if not all([settings.CLOUDINARY_CLOUD_NAME, settings.CLOUDINARY_API_KEY, settings.CLOUDINARY_API_SECRET]):
                logger.error("Cloudinary 配置不完整")
                return None
                
            # 檢查文件是否存在
            if not os.path.exists(image_path):
                logger.error(f"找不到要上傳的文件：{image_path}")
                return None
                
            # 記錄文件大小
            file_size = os.path.getsize(image_path)
            logger.info(f"準備上傳到 Cloudinary 的文件大小：{file_size} bytes")
            
            # 如果文件太大，進一步壓縮
            if file_size > 1000000:  # 如果大於 1MB
                try:
                    with Image.open(image_path) as img:
                        # 縮小尺寸
                        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                        # 保存為較低質量
                        img = img.convert('RGB')
                        img.save(image_path, 'JPEG', quality=75, optimize=True)
                        logger.info(f"圖片已進一步壓縮，新大小：{os.path.getsize(image_path)} bytes")
                except Exception as e:
                    logger.error(f"壓縮圖片失敗：{str(e)}")
            
            logger.info(f"開始上傳到 Cloudinary：{image_path}")
            
            # 配置 Cloudinary
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET
            )
            
            # 上傳到 Cloudinary，添加轉換選項
            try:
                upload_result = cloudinary.uploader.upload(
                    image_path,
                    folder="line-bot-frames",
                    transformation=[
                        {"quality": "auto:low"},  # 自動優化質量
                        {"fetch_format": "auto"}   # 自動選擇最佳格式
                    ]
                )
                cloudinary_url = upload_result.get('secure_url')
                logger.info(f"Cloudinary 上傳成功：{cloudinary_url}")
                return cloudinary_url
            except Exception as e:
                logger.error(f"Cloudinary 上傳失敗：{str(e)}")
                # 嘗試使用本地 URL
                base_url = settings.get_base_url()
                local_url = f"{base_url}/tmp/uploads/{os.path.basename(image_path)}"
                logger.info(f"使用本地 URL 替代：{local_url}")
                return local_url
        except Exception as e:
            logger.error(f"上傳到 Cloudinary 過程中發生錯誤：{str(e)}")
            return None
