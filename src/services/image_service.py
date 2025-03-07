import os
import logging
import traceback
from PIL import Image
import cloudinary
import cloudinary.uploader
import cloudinary.api
import asyncio
from io import BytesIO
import time
import math
from src.config import settings
import numpy as np

logger = logging.getLogger(__name__)

class ImageService:
    @staticmethod
    def allowed_file(filename):
        """檢查檔案是否為允許的類型"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in settings.ALLOWED_EXTENSIONS

    @staticmethod
    def is_portrait(image):
        """判斷圖片是否為直式（高度大於寬度）"""
        width, height = image.size
        is_portrait = height > width
        logger.info(f"判斷圖片方向: 寬度={width}, 高度={height}, 是否為直式={is_portrait}")
        return is_portrait

    @staticmethod
    def find_transparent_regions(frame_image):
        """
        分析相框圖片中的透明區域，找出挖空的位置
        
        Args:
            frame_image (PIL.Image): 相框圖片
            
        Returns:
            list: 透明區域的邊界框列表 [(x1, y1, x2, y2), ...]
        """
        try:
            # 記錄相框尺寸
            frame_width, frame_height = frame_image.size
            logger.info(f"相框尺寸: {frame_width}x{frame_height}")
            
            # 確保圖片是 RGBA 模式
            if frame_image.mode != 'RGBA':
                frame_image = frame_image.convert('RGBA')
                logger.info(f"將相框轉換為 RGBA 模式")
                
            # 獲取圖片的 alpha 通道
            alpha = np.array(frame_image.getchannel('A'))
            
            # 找出透明區域（alpha 值小於 128 的區域）
            transparent = alpha < 128
            
            # 獲取圖片尺寸
            height, width = transparent.shape
            
            # 初始化透明區域列表
            regions = []
            
            # 檢測連續的透明區域
            visited = np.zeros_like(transparent, dtype=bool)
            
            # 遍歷圖片的每個像素，使用較大的步長以提高效率
            step = 5  # 每5個像素檢查一次
            for y in range(0, height, step):
                for x in range(0, width, step):
                    # 如果該像素是透明的且未被訪問過
                    if transparent[y, x] and not visited[y, x]:
                        # 使用 BFS 找出連續的透明區域
                        queue = [(x, y)]
                        visited[y, x] = True
                        min_x, min_y, max_x, max_y = x, y, x, y
                        area_pixels = 0  # 計算區域包含的像素數
                        
                        while queue:
                            cx, cy = queue.pop(0)
                            area_pixels += 1
                            
                            # 更新邊界框
                            min_x = min(min_x, cx)
                            min_y = min(min_y, cy)
                            max_x = max(max_x, cx)
                            max_y = max(max_y, cy)
                            
                            # 檢查相鄰的像素，使用較大的步長
                            for dx, dy in [(0, step), (step, 0), (0, -step), (-step, 0)]:
                                nx, ny = cx + dx, cy + dy
                                if 0 <= nx < width and 0 <= ny < height and transparent[ny, nx] and not visited[ny, nx]:
                                    queue.append((nx, ny))
                                    visited[ny, nx] = True
                                    
                                    # 標記中間的像素為已訪問
                                    for i in range(1, step):
                                        if dx != 0 and 0 <= cx + i * dx // step < width:
                                            visited[cy, cx + i * dx // step] = True
                                        if dy != 0 and 0 <= cy + i * dy // step < height:
                                            visited[cy + i * dy // step, cx] = True
                        
                        # 計算區域面積
                        area = (max_x - min_x + 1) * (max_y - min_y + 1)
                        
                        # 計算區域的透明度比例
                        transparency_ratio = area_pixels / (area / (step * step))
                        
                        # 如果透明區域足夠大且透明度比例足夠高
                        min_area = frame_width * frame_height * 0.05  # 至少為總面積的5%
                        if area > min_area and transparency_ratio > 0.5:
                            # 擴展邊界以確保包含所有透明像素
                            margin = 5
                            min_x = max(0, min_x - margin)
                            min_y = max(0, min_y - margin)
                            max_x = min(width - 1, max_x + margin)
                            max_y = min(height - 1, max_y + margin)
                            
                            # 檢查是否為有效的矩形區域
                            if max_x > min_x and max_y > min_y:
                                regions.append((min_x, min_y, max_x, max_y))
                                logger.info(f"找到透明區域: ({min_x}, {min_y}, {max_x}, {max_y}), 面積: {area}, 透明度比例: {transparency_ratio:.2f}")
            
            # 如果沒有找到透明區域，嘗試使用預定義的區域
            if not regions:
                logger.warning("未找到透明區域，嘗試使用預定義的區域")
                
                # 檢查相框文件名以確定類型
                frame_filename = os.path.basename(frame_image.filename) if hasattr(frame_image, 'filename') else "unknown"
                
                if frame_filename == settings.PORTRAIT_FRAME:
                    # 直式相框 - 左右兩個區域
                    left_region_width = int(frame_width * 0.45)
                    left_region_height = int(frame_height * 0.8)
                    left_x = int(frame_width * 0.05)
                    left_y = (frame_height - left_region_height) // 2
                    
                    right_region_width = int(frame_width * 0.45)
                    right_region_height = int(frame_height * 0.8)
                    right_x = int(frame_width * 0.5)
                    right_y = (frame_height - right_region_height) // 2
                    
                    regions = [
                        (left_x, left_y, left_x + left_region_width, left_y + left_region_height),
                        (right_x, right_y, right_x + right_region_width, right_y + right_region_height)
                    ]
                    logger.info(f"使用預定義的直式相框區域: {regions}")
                else:
                    # 橫式相框 - 上下兩個區域
                    top_region_width = int(frame_width * 0.8)
                    top_region_height = int(frame_height * 0.45)
                    top_x = (frame_width - top_region_width) // 2
                    top_y = int(frame_height * 0.05)
                    
                    bottom_region_width = int(frame_width * 0.8)
                    bottom_region_height = int(frame_height * 0.45)
                    bottom_x = (frame_width - bottom_region_width) // 2
                    bottom_y = int(frame_height * 0.5)
                    
                    regions = [
                        (top_x, top_y, top_x + top_region_width, top_y + top_region_height),
                        (bottom_x, bottom_y, bottom_x + bottom_region_width, bottom_y + bottom_region_height)
                    ]
                    logger.info(f"使用預定義的橫式相框區域: {regions}")
            
            # 根據區域大小排序（從大到小）
            regions.sort(key=lambda r: (r[2] - r[0]) * (r[3] - r[1]), reverse=True)
            
            # 如果找到的區域太多，只保留最大的兩個
            if len(regions) > 2:
                regions = regions[:2]
                
            # 根據位置排序
            frame_filename = os.path.basename(frame_image.filename) if hasattr(frame_image, 'filename') else "unknown"
            if frame_filename == settings.PORTRAIT_FRAME:
                # 直式相框（用於直式照片）- 按 x 坐標排序（左右排列）
                regions.sort(key=lambda r: r[0])
                logger.info(f"直式相框 ({frame_filename}): 按 x 坐標排序透明區域")
            else:
                # 橫式相框（用於橫式照片）- 按 y 坐標排序（上下排列）
                regions.sort(key=lambda r: r[1])
                logger.info(f"橫式相框 ({frame_filename}): 按 y 坐標排序透明區域")
                
            logger.info(f"最終找到 {len(regions)} 個透明區域: {regions}")
            return regions
        except Exception as e:
            logger.error(f"分析透明區域時發生錯誤: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 發生錯誤時返回預設區域
            frame_width, frame_height = frame_image.size
            
            # 預設為橫式相框的上下兩個區域
            top_region_width = int(frame_width * 0.8)
            top_region_height = int(frame_height * 0.45)
            top_x = (frame_width - top_region_width) // 2
            top_y = int(frame_height * 0.05)
            
            bottom_region_width = int(frame_width * 0.8)
            bottom_region_height = int(frame_height * 0.45)
            bottom_x = (frame_width - bottom_region_width) // 2
            bottom_y = int(frame_height * 0.5)
            
            default_regions = [
                (top_x, top_y, top_x + top_region_width, top_y + top_region_height),
                (bottom_x, bottom_y, bottom_x + bottom_region_width, bottom_y + bottom_region_height)
            ]
            logger.info(f"使用預設區域: {default_regions}")
            return default_regions

    @staticmethod
    def fit_image_to_region(image, region_width, region_height, fill=True):
        """
        調整圖片大小以適應指定區域，保持原始比例
        
        Args:
            image (PIL.Image): 原始圖片
            region_width (int): 目標區域寬度
            region_height (int): 目標區域高度
            fill (bool): 是否填滿區域（True: 填滿但可能裁剪，False: 完整顯示但可能有空白）
            
        Returns:
            PIL.Image: 調整大小後的圖片
        """
        try:
            # 獲取原始圖片尺寸
            img_width, img_height = image.size
            logger.info(f"原始圖片尺寸: {img_width}x{img_height}, 目標區域尺寸: {region_width}x{region_height}")
            
            # 檢查圖片方向
            is_portrait = img_height > img_width
            logger.info(f"圖片方向: {'直式' if is_portrait else '橫式'}")
            
            # 計算縮放比例
            width_ratio = region_width / img_width
            height_ratio = region_height / img_height
            
            # 根據填充模式和圖片方向選擇縮放比例
            if fill:
                if is_portrait:
                    # 直式照片：優先考慮寬度填滿，但確保高度不會過度裁剪
                    # 如果高度比例太小（會導致過度裁剪），則使用高度比例
                    if height_ratio < width_ratio * 0.6:  # 如果高度比例小於寬度比例的60%
                        ratio = height_ratio
                        logger.info(f"直式照片填滿模式: 使用高度比例 {ratio} 避免過度裁剪")
                    else:
                        ratio = width_ratio
                        logger.info(f"直式照片填滿模式: 使用寬度比例 {ratio}")
                else:
                    # 橫式照片：優先考慮高度填滿，但確保寬度不會過度裁剪
                    # 如果寬度比例太小（會導致過度裁剪），則使用寬度比例
                    if width_ratio < height_ratio * 0.6:  # 如果寬度比例小於高度比例的60%
                        ratio = width_ratio
                        logger.info(f"橫式照片填滿模式: 使用寬度比例 {ratio} 避免過度裁剪")
                    else:
                        ratio = height_ratio
                        logger.info(f"橫式照片填滿模式: 使用高度比例 {ratio}")
            else:
                # 適應模式：選擇較小的比例，確保圖片完整顯示（可能有空白）
                ratio = min(width_ratio, height_ratio)
                logger.info(f"適應模式: 選擇較小的比例 {ratio}")
            
            # 計算新尺寸
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            logger.info(f"調整後的圖片尺寸: {new_width}x{new_height}")
            
            # 調整圖片大小
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 如果是填滿模式且圖片大於區域，進行裁剪
            if fill and (new_width > region_width or new_height > region_height):
                # 計算裁剪區域
                left = (new_width - region_width) // 2 if new_width > region_width else 0
                top = (new_height - region_height) // 2 if new_height > region_height else 0
                right = left + region_width if new_width > region_width else new_width
                bottom = top + region_height if new_height > region_height else new_height
                
                logger.info(f"裁剪區域: ({left}, {top}, {right}, {bottom})")
                
                # 裁剪圖片
                resized_image = resized_image.crop((left, top, right, bottom))
                logger.info(f"裁剪後的圖片尺寸: {resized_image.size}")
            
            # 如果圖片小於區域，創建一個透明背景並將圖片居中放置
            elif not fill and (new_width < region_width or new_height < region_height):
                # 創建透明背景
                background = Image.new('RGBA', (region_width, region_height), (0, 0, 0, 0))
                
                # 計算居中位置
                paste_x = (region_width - new_width) // 2
                paste_y = (region_height - new_height) // 2
                
                logger.info(f"將圖片放置在透明背景上，位置: ({paste_x}, {paste_y})")
                
                # 將調整後的圖片粘貼到背景上
                background.paste(resized_image, (paste_x, paste_y), resized_image.convert('RGBA'))
                resized_image = background
            
            return resized_image
        except Exception as e:
            logger.error(f"調整圖片大小時發生錯誤: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 發生錯誤時，嘗試簡單調整大小並返回
            try:
                # 使用簡單的縮放方法
                ratio = min(region_width / image.size[0], region_height / image.size[1])
                new_width = int(image.size[0] * ratio)
                new_height = int(image.size[1] * ratio)
                return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            except:
                # 如果仍然失敗，返回原始圖片
                return image

    @staticmethod
    async def process_image_with_frame(image_filename, frame_style=None):
        """
        將用戶的圖片與選擇的框架合成，自動判斷照片方向
        
        Args:
            image_filename (str): 原始圖片的檔名
            frame_style (str, optional): 選擇的框架樣式，如果為 None 則自動根據照片方向選擇
            
        Returns:
            str: 處理後的圖片檔名，如果處理失敗則返回 None
        """
        try:
            # 構建檔案路徑
            image_path = os.path.join(settings.UPLOAD_FOLDER, image_filename)
            
            # 檢查原始圖片是否存在
            if not os.path.exists(image_path):
                logger.error(f"找不到原始圖片：{image_path}")
                return None
            
            # 在線程池中執行同步的圖片處理操作
            def process_image():
                try:
                    # 讀取原始圖片
                    with Image.open(image_path) as user_image:
                        # 判斷圖片方向
                        is_portrait_image = ImageService.is_portrait(user_image)
                        logger.info(f"圖片方向: {'直式' if is_portrait_image else '橫式'}")
                        
                        # 根據圖片方向選擇相框
                        frame_filename = settings.PORTRAIT_FRAME if is_portrait_image else settings.LANDSCAPE_FRAME
                        frame_path = os.path.join('static', 'frames', frame_filename)
                        logger.info(f"選擇的相框: {frame_filename}, 路徑: {frame_path}")
                        
                        # 檢查相框圖片是否存在
                        if not os.path.exists(frame_path):
                            logger.error(f"找不到框架圖片：{frame_path}")
                            return None
                        
                        # 讀取相框圖片
                        with Image.open(frame_path) as frame_image:
                            # 獲取原始圖片和框架尺寸
                            user_width, user_height = user_image.size
                            frame_width, frame_height = frame_image.size
                            logger.info(f"用戶圖片尺寸: {user_width}x{user_height}, 相框尺寸: {frame_width}x{frame_height}")
                            
                            # 創建一個新的空白圖像，大小與框架相同
                            result = Image.new('RGBA', (frame_width, frame_height), (0, 0, 0, 0))
                            
                            # 分析相框中的透明區域
                            transparent_regions = ImageService.find_transparent_regions(frame_image)
                            
                            # 如果沒有找到透明區域，使用預設的位置
                            if not transparent_regions or len(transparent_regions) < 2:
                                logger.warning("未找到足夠的透明區域，使用預設位置")
                                
                                if is_portrait_image:
                                    # 直式照片 - 放在左右兩個框框中
                                    # 計算每個框框的大小（假設左右兩個框框大小相同）
                                    frame_box_width = int(frame_width * 0.45)  # 每個框框寬度約為總寬度的45%
                                    frame_box_height = int(frame_height * 0.8)  # 每個框框高度約為總高度的80%
                                    logger.info(f"使用預設位置 - 直式照片: 框框大小 {frame_box_width}x{frame_box_height}")
                                    
                                    # 計算縮放比例，保持原始照片的長寬比
                                    width_ratio = frame_box_width / user_width
                                    height_ratio = frame_box_height / user_height
                                    
                                    # 直式照片通常需要填滿寬度，所以使用寬度比例，但確保不超過高度
                                    ratio = min(width_ratio, height_ratio) * 0.95  # 縮小5%以確保有邊距
                                    logger.info(f"縮放比例: {ratio}")
                                    
                                    # 縮放用戶圖片
                                    new_width = int(user_width * ratio)
                                    new_height = int(user_height * ratio)
                                    user_image_resized = user_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                                    logger.info(f"縮放後的圖片尺寸: {new_width}x{new_height}")
                                    
                                    # 將用戶圖片轉換為 RGBA 模式
                                    user_image_resized = user_image_resized.convert('RGBA')
                                    
                                    # 計算左側框框的位置 - 水平居中，垂直居中
                                    x_offset_left = int(frame_width * 0.05)  # 左側框框的左側位置
                                    y_offset_left = (frame_height - new_height) // 2  # 垂直居中
                                    
                                    # 計算右側框框的位置 - 水平居中，垂直居中
                                    x_offset_right = int(frame_width * 0.5)  # 右側框框的左側位置
                                    y_offset_right = (frame_height - new_height) // 2  # 垂直居中
                                    
                                    logger.info(f"左側照片位置: ({x_offset_left}, {y_offset_left}), 右側照片位置: ({x_offset_right}, {y_offset_right})")
                                    
                                    # 將照片粘貼到結果圖像上
                                    result.paste(user_image_resized, (x_offset_left, y_offset_left), user_image_resized)
                                    result.paste(user_image_resized, (x_offset_right, y_offset_right), user_image_resized)
                                    
                                    logger.info(f"直式照片處理: 原始大小 ({user_width}x{user_height}), 縮放後 ({new_width}x{new_height})")
                                    logger.info(f"左側照片位置: ({x_offset_left}, {y_offset_left}), 右側照片位置: ({x_offset_right}, {y_offset_right})")
                                    
                                else:
                                    # 橫式照片 - 放在上下兩個框框中
                                    # 計算每個框框的大小（假設上下兩個框框大小相同）
                                    frame_box_width = int(frame_width * 0.8)  # 每個框框寬度約為總寬度的80%
                                    frame_box_height = int(frame_height * 0.45)  # 每個框框高度約為總高度的45%
                                    logger.info(f"使用預設位置 - 橫式照片: 框框大小 {frame_box_width}x{frame_box_height}")
                                    
                                    # 計算縮放比例，保持原始照片的長寬比
                                    width_ratio = frame_box_width / user_width
                                    height_ratio = frame_box_height / user_height
                                    
                                    # 橫式照片通常需要填滿寬度，所以使用寬度比例，但確保不超過高度
                                    ratio = min(width_ratio, height_ratio) * 0.95  # 縮小5%以確保有邊距
                                    logger.info(f"縮放比例: {ratio}")
                                    
                                    # 縮放用戶圖片
                                    new_width = int(user_width * ratio)
                                    new_height = int(user_height * ratio)
                                    user_image_resized = user_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                                    logger.info(f"縮放後的圖片尺寸: {new_width}x{new_height}")
                                    
                                    # 將用戶圖片轉換為 RGBA 模式
                                    user_image_resized = user_image_resized.convert('RGBA')
                                    
                                    # 計算上方框框的位置 - 水平居中，垂直位置固定
                                    x_offset_top = (frame_width - new_width) // 2  # 水平居中
                                    y_offset_top = int(frame_height * 0.05)  # 上方框框的頂部位置
                                    
                                    # 計算下方框框的位置 - 水平居中，垂直位置固定
                                    x_offset_bottom = (frame_width - new_width) // 2  # 水平居中
                                    y_offset_bottom = int(frame_height * 0.5)  # 下方框框的頂部位置
                                    
                                    logger.info(f"上方照片位置: ({x_offset_top}, {y_offset_top}), 下方照片位置: ({x_offset_bottom}, {y_offset_bottom})")
                                    
                                    # 將照片粘貼到結果圖像上
                                    result.paste(user_image_resized, (x_offset_top, y_offset_top), user_image_resized)
                                    result.paste(user_image_resized, (x_offset_bottom, y_offset_bottom), user_image_resized)
                                    
                                    logger.info(f"橫式照片處理: 原始大小 ({user_width}x{user_height}), 縮放後 ({new_width}x{new_height})")
                                    logger.info(f"上方照片位置: ({x_offset_top}, {y_offset_top}), 下方照片位置: ({x_offset_bottom}, {y_offset_bottom})")
                            else:
                                # 使用找到的透明區域來放置照片
                                region1, region2 = transparent_regions[:2]
                                
                                # 計算每個透明區域的尺寸
                                region1_width = region1[2] - region1[0]
                                region1_height = region1[3] - region1[1]
                                region2_width = region2[2] - region2[0]
                                region2_height = region2[3] - region2[1]
                                
                                logger.info(f"區域1尺寸: {region1_width}x{region1_height}, 區域2尺寸: {region2_width}x{region2_height}")
                                
                                # 使用改進的 fit_image_to_region 方法來調整圖片大小
                                # 為每個區域單獨調整圖片大小，使用填滿模式但保留一些邊距
                                # 直式照片使用較小的填充比例，避免過度裁剪
                                fill_mode = True  # 默認使用填滿模式
                                margin_ratio = 0.95  # 保留5%的邊距
                                
                                # 根據照片方向調整填充模式和邊距
                                if is_portrait_image:
                                    # 直式照片可能需要更多的邊距以避免過度裁剪
                                    margin_ratio = 0.9  # 保留10%的邊距
                                
                                # 調整區域尺寸以添加邊距
                                region1_width_with_margin = int(region1_width * margin_ratio)
                                region1_height_with_margin = int(region1_height * margin_ratio)
                                region2_width_with_margin = int(region2_width * margin_ratio)
                                region2_height_with_margin = int(region2_height * margin_ratio)
                                
                                logger.info(f"添加邊距後的區域1尺寸: {region1_width_with_margin}x{region1_height_with_margin}")
                                logger.info(f"添加邊距後的區域2尺寸: {region2_width_with_margin}x{region2_height_with_margin}")
                                
                                user_image_region1 = ImageService.fit_image_to_region(
                                    user_image, region1_width_with_margin, region1_height_with_margin, fill=fill_mode
                                )
                                user_image_region2 = ImageService.fit_image_to_region(
                                    user_image, region2_width_with_margin, region2_height_with_margin, fill=fill_mode
                                )
                                
                                # 將用戶圖片轉換為 RGBA 模式
                                user_image_region1 = user_image_region1.convert('RGBA')
                                user_image_region2 = user_image_region2.convert('RGBA')
                                
                                # 計算居中位置
                                region1_center_x = region1[0] + (region1_width - user_image_region1.width) // 2
                                region1_center_y = region1[1] + (region1_height - user_image_region1.height) // 2
                                region2_center_x = region2[0] + (region2_width - user_image_region2.width) // 2
                                region2_center_y = region2[1] + (region2_height - user_image_region2.height) // 2
                                
                                # 將照片粘貼到結果圖像上，精確放置在透明區域的中心
                                result.paste(user_image_region1, (region1_center_x, region1_center_y), user_image_region1)
                                result.paste(user_image_region2, (region2_center_x, region2_center_y), user_image_region2)
                                
                                logger.info(f"照片處理: 原始大小 ({user_width}x{user_height})")
                                logger.info(f"區域1照片大小: {user_image_region1.size}, 區域2照片大小: {user_image_region2.size}")
                                logger.info(f"區域1照片位置: ({region1_center_x}, {region1_center_y}), 區域2照片位置: ({region2_center_x}, {region2_center_y})")
                            
                            # 將框架粘貼到結果圖像上
                            result.paste(frame_image, (0, 0), frame_image)
                            
                            # 生成新檔名
                            timestamp = image_filename.split('_')[0]  # 取得時間戳記
                            orientation = "portrait" if is_portrait_image else "landscape"
                            processed_filename = f"processed_{timestamp}_{orientation}_{image_filename}"
                            processed_path = os.path.join(settings.UPLOAD_FOLDER, processed_filename)
                            logger.info(f"生成的新檔名: {processed_filename}")
                            
                            # 檢查結果圖片的尺寸
                            result_width, result_height = result.size
                            logger.info(f"處理後的圖片尺寸: {result_width}x{result_height}")
                            
                            # 確保圖片尺寸不超過 LINE 平台的限制
                            max_width = 1024
                            max_height = 1024
                            needs_resize = False
                            
                            if result_width > max_width:
                                ratio = max_width / result_width
                                new_width = max_width
                                new_height = int(result_height * ratio)
                                needs_resize = True
                            elif result_height > max_height:
                                ratio = max_height / result_height
                                new_height = max_height
                                new_width = int(result_width * ratio)
                                needs_resize = True
                            
                            if needs_resize:
                                logger.info(f"調整最終圖片尺寸為: {new_width}x{new_height}")
                                result = result.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            
                            # 儲存處理後的圖片（轉換為 RGB 以移除透明度）
                            result = result.convert('RGB')
                            
                            # 使用適當的質量設置，直式照片使用較低的質量以減小文件大小
                            quality = 85 if is_portrait_image else 90
                            result.save(processed_path, 'JPEG', quality=quality, optimize=True)
                            
                            # 檢查文件大小，如果太大則進一步壓縮
                            file_size = os.path.getsize(processed_path)
                            logger.info(f"初始處理後的圖片大小：{file_size} bytes")
                            
                            # 如果文件仍然太大，進一步降低質量
                            max_size = 500000  # 500KB
                            if file_size > max_size:
                                with Image.open(processed_path) as img:
                                    for q in [80, 75, 70, 65]:
                                        img.save(processed_path, 'JPEG', quality=q, optimize=True)
                                        new_size = os.path.getsize(processed_path)
                                        logger.info(f"進一步壓縮照片，質量={q}，新大小={new_size} bytes")
                                        if new_size <= max_size:
                                            break
                            
                            # 記錄最終處理後的圖片大小
                            final_size = os.path.getsize(processed_path)
                            logger.info(f"圖片處理完成：{processed_path}")
                            logger.info(f"最終處理後的圖片大小：{final_size} bytes")
                            
                            return processed_filename
                except Exception as e:
                    logger.error(f"處理圖片時發生錯誤：{str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return None
            
            # 在線程池中執行同步操作
            return await asyncio.to_thread(process_image)
                
        except Exception as e:
            logger.error(f"處理圖片時發生錯誤：{str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
            
            # 檢查是否為直式照片 - 通過實際檢查圖片尺寸而不僅僅依賴文件名
            is_portrait = False
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                    is_portrait = height > width
                    logger.info(f"照片方向檢查: 尺寸={width}x{height}, 是否為直式={is_portrait}")
            except Exception as e:
                logger.error(f"檢查圖片方向時發生錯誤: {str(e)}")
                # 如果無法檢查尺寸，則回退到使用文件名判斷
                is_portrait = "portrait" in os.path.basename(image_path)
                logger.info(f"使用文件名判斷照片方向: {'直式' if is_portrait else '橫式'}")
            
            # 處理圖片，確保符合 LINE 平台的要求
            try:
                with Image.open(image_path) as img:
                    # 檢查圖片尺寸
                    width, height = img.size
                    logger.info(f"原始圖片尺寸: {width}x{height}")
                    
                    # 調整圖片大小
                    max_width = 1024  # LINE 平台的最大寬度限制
                    max_height = 1024  # 設置一個合理的最大高度
                    
                    # 計算新尺寸，保持原始比例
                    if is_portrait:
                        # 直式照片 - 確保寬度不超過限制
                        if width > max_width:
                            ratio = max_width / width
                            new_width = max_width
                            new_height = int(height * ratio)
                            # 確保高度也不超過限制
                            if new_height > max_height:
                                ratio = max_height / new_height
                                new_height = max_height
                                new_width = int(new_width * ratio)
                            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            logger.info(f"調整後的直式照片尺寸: {new_width}x{new_height}")
                    else:
                        # 橫式照片 - 確保高度不超過限制
                        if height > max_height:
                            ratio = max_height / height
                            new_height = max_height
                            new_width = int(width * ratio)
                            # 確保寬度也不超過限制
                            if new_width > max_width:
                                ratio = max_width / new_width
                                new_width = max_width
                                new_height = int(new_height * ratio)
                            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            logger.info(f"調整後的橫式照片尺寸: {new_width}x{new_height}")
                    
                    # 確保圖片是 RGB 模式（移除透明度）
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                        logger.info("圖片已轉換為 RGB 模式")
                    
                    # 保存為 JPEG 格式，使用適當的質量
                    quality = 85 if is_portrait else 90  # 直式照片使用稍低的質量以減小文件大小
                    img.save(image_path, 'JPEG', quality=quality, optimize=True)
                    new_size = os.path.getsize(image_path)
                    logger.info(f"照片已調整，新大小：{new_size} bytes")
                    
                    # 如果文件仍然太大，進一步降低質量
                    max_size = 500000  # 500KB
                    if new_size > max_size:
                        for q in [80, 75, 70, 65]:
                            img.save(image_path, 'JPEG', quality=q, optimize=True)
                            new_size = os.path.getsize(image_path)
                            logger.info(f"進一步壓縮照片，質量={q}，新大小={new_size} bytes")
                            if new_size <= max_size:
                                break
            except Exception as e:
                logger.error(f"調整照片失敗：{str(e)}")
                logger.error(traceback.format_exc())
            
            logger.info(f"開始上傳到 Cloudinary：{image_path}")
            
            # 配置 Cloudinary
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET
            )
            
            # 上傳到 Cloudinary，添加轉換選項
            try:
                # 為直式照片添加特殊的轉換選項
                transformation = []
                if is_portrait:
                    transformation = [
                        {"width": 1024, "crop": "scale"},  # 確保寬度不超過 1024 像素
                        {"quality": "auto:good"},          # 使用較高質量
                        {"fetch_format": "auto"}           # 自動選擇最佳格式
                    ]
                else:
                    transformation = [
                        {"quality": "auto:good"},  # 使用較高質量
                        {"fetch_format": "auto"}   # 自動選擇最佳格式
                    ]
                
                # 添加更多的錯誤處理和重試邏輯
                max_retries = 3
                retry_count = 0
                last_error = None
                
                while retry_count < max_retries:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            image_path,
                            folder="line-bot-frames",
                            transformation=transformation,
                            timeout=30  # 設置超時時間
                        )
                        cloudinary_url = upload_result.get('secure_url')
                        logger.info(f"Cloudinary 上傳成功：{cloudinary_url}")
                        return cloudinary_url
                    except Exception as e:
                        last_error = e
                        retry_count += 1
                        logger.warning(f"Cloudinary 上傳失敗 (嘗試 {retry_count}/{max_retries}): {str(e)}")
                        if retry_count < max_retries:
                            # 等待一段時間後重試
                            await asyncio.sleep(1)
                
                # 如果所有重試都失敗
                logger.error(f"所有 Cloudinary 上傳嘗試都失敗: {str(last_error)}")
                # 嘗試使用本地 URL
                base_url = settings.get_base_url()
                local_url = f"{base_url}/tmp/uploads/{os.path.basename(image_path)}"
                logger.info(f"使用本地 URL 替代：{local_url}")
                return local_url
            except Exception as e:
                logger.error(f"Cloudinary 上傳失敗：{str(e)}")
                # 嘗試使用本地 URL
                base_url = settings.get_base_url()
                local_url = f"{base_url}/tmp/uploads/{os.path.basename(image_path)}"
                logger.info(f"使用本地 URL 替代：{local_url}")
                return local_url
        except Exception as e:
            logger.error(f"上傳到 Cloudinary 過程中發生錯誤：{str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
