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
            
            # 讀取圖片
            with Image.open(image_path) as user_image, Image.open(frame_path) as frame_image:
                # 調整框架大小以匹配用戶圖片
                frame_resized = frame_image.resize(user_image.size, Image.Resampling.LANCZOS)
                
                # 將用戶圖片轉換為 RGBA 模式
                user_image = user_image.convert('RGBA')
                frame_resized = frame_resized.convert('RGBA')
                
                # 合成圖片
                composite = Image.alpha_composite(user_image, frame_resized)
                
                # 生成新檔名
                timestamp = image_filename.split('_')[0]  # 取得時間戳記
                processed_filename = f"processed_{timestamp}_{image_filename}"
                processed_path = os.path.join(settings.UPLOAD_FOLDER, processed_filename)
                
                # 儲存處理後的圖片（轉換為 RGB 以移除透明度）
                composite = composite.convert('RGB')
                composite.save(processed_path, 'JPEG', quality=80)
                logger.info(f"圖片處理完成：{processed_path}")
                
                # 檢查檔案大小
                file_size = os.path.getsize(processed_path)
                logger.info(f"處理後的圖片大小：{file_size} bytes")
                
                return processed_filename
                
        except Exception as e:
            logger.error(f"處理圖片時發生錯誤：{str(e)}")
            return None

    @staticmethod
    def upload_to_cloudinary(image_path):
        """上傳圖片到 Cloudinary"""
        try:
            response = cloudinary.uploader.upload(
                image_path,
                folder="line-bot-frames",
                resource_type="image",
                quality="auto:good",
                fetch_format="auto"
            )
            return response['secure_url']
        except Exception as e:
            logger.error(f"上傳圖片到 Cloudinary 失敗：{str(e)}")
            raise
