import os
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
import logging

logger = logging.getLogger(__name__)

class PrinterService:
    def __init__(self):
        self.pdf_dir = 'static/pdf'
        os.makedirs(self.pdf_dir, exist_ok=True)
        
        # A6 紙張尺寸（105mm x 148mm，1英吋 = 25.4mm）
        self.PHOTO_WIDTH = 105 / 25.4 * inch  # 105mm
        self.PHOTO_HEIGHT = 148 / 25.4 * inch  # 148mm
        
    def create_a4_pdf(self, image_path, output_filename=None):
        """將圖片轉換為 A4 大小的 PDF"""
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"找不到圖片：{image_path}")
                
            # 如果沒有指定輸出檔名，使用原檔名
            if output_filename is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_filename = f"{base_name}.pdf"
            
            output_path = os.path.join(self.pdf_dir, output_filename)
            
            # 開啟圖片
            img = Image.open(image_path)
            
            # 獲取圖片尺寸
            img_width, img_height = img.size
            
            # 計算縮放比例（保持長寬比）
            # A4 尺寸為 210mm x 297mm，轉換為像素（以 72dpi 為例）
            a4_width, a4_height = A4
            width_ratio = a4_width / img_width
            height_ratio = a4_height / img_height
            ratio = min(width_ratio, height_ratio) * 0.95  # 留一些邊距
            
            # 計算縮放後的尺寸
            new_width = img_width * ratio
            new_height = img_height * ratio
            
            # 計算在 A4 上的位置（置中）
            x = (a4_width - new_width) / 2
            y = (a4_height - new_height) / 2
            
            # 創建 PDF
            c = canvas.Canvas(output_path, pagesize=A4)
            c.drawImage(image_path, x, y, width=new_width, height=new_height)
            c.save()
            
            logger.info(f"成功創建 PDF：{output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"創建 PDF 時發生錯誤：{str(e)}")
            raise
            
    def create_4x6_photo(self, image_path, output_filename=None):
        """將圖片轉換為 4x6 英吋的照片 PDF"""
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"找不到圖片：{image_path}")
                
            # 如果沒有指定輸出檔名，使用原檔名
            if output_filename is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_filename = f"{base_name}_4x6.pdf"
            
            output_path = os.path.join(self.pdf_dir, output_filename)
            
            # 開啟圖片
            img = Image.open(image_path)
            
            # 獲取圖片尺寸
            img_width, img_height = img.size
            
            # 計算縮放比例（保持長寬比）
            width_ratio = self.PHOTO_WIDTH / img_width
            height_ratio = self.PHOTO_HEIGHT / img_height
            ratio = min(width_ratio, height_ratio)  # 完全填滿
            
            # 計算縮放後的尺寸
            new_width = img_width * ratio
            new_height = img_height * ratio
            
            # 計算在 A6 上的位置（置中）
            x = (self.PHOTO_WIDTH - new_width) / 2
            y = (self.PHOTO_HEIGHT - new_height) / 2
            
            # 創建 PDF（直向 A6）
            c = canvas.Canvas(output_path, pagesize=(self.PHOTO_WIDTH, self.PHOTO_HEIGHT))
            c.drawImage(image_path, x, y, width=new_width, height=new_height)
            c.save()
            
            logger.info(f"成功創建 4x6 照片 PDF：{output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"創建 4x6 照片 PDF 時發生錯誤：{str(e)}")
            raise
