import os
import threading
import asyncio
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
import logging
from src.services.print_service import PrintService
import traceback

logger = logging.getLogger(__name__)

class PrinterService:
    def __init__(self):
        self.pdf_dir = 'static/pdf'
        os.makedirs(self.pdf_dir, exist_ok=True)
        
        # A6 紙張尺寸（105mm x 148mm，1英吋 = 25.4mm）
        self.PHOTO_WIDTH = 105 / 25.4 * inch  # 105mm
        self.PHOTO_HEIGHT = 148 / 25.4 * inch  # 148mm
        
        # 列印服務
        self.print_service = PrintService()
        
    async def create_a4_pdf(self, image_path, output_filename=None):
        """將圖片轉換為 A4 大小的 PDF"""
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"找不到圖片：{image_path}")
                
            # 如果沒有指定輸出檔名，使用原檔名
            if output_filename is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_filename = f"{base_name}.pdf"
            
            output_path = os.path.join(self.pdf_dir, output_filename)
            
            # 在線程池中執行同步操作
            import asyncio
            def process_pdf():
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
                
                # 計算新的尺寸
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                
                # 計算居中位置
                x = (a4_width - new_width) / 2
                y = (a4_height - new_height) / 2
                
                # 建立 PDF
                c = canvas.Canvas(output_path, pagesize=A4)
                c.drawImage(image_path, x, y, width=new_width, height=new_height)
                c.save()
                
                return output_path
            
            return await asyncio.to_thread(process_pdf)
            
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
            
    async def print_photo(self, image_path, on_complete=None):
        """列印照片"""
        try:
            # 創建 4x6 照片 PDF
            pdf_path = await self.create_4x6_photo(image_path)
            if not pdf_path:
                raise Exception("PDF 轉換失敗")
            
            try:
                # 初始化列印服務
                await self.print_service.authenticate_device()
                
                # 設定照片列印參數
                photo_print_settings = {
                    'media_size': 'ms_a6',  # A6 照片尺寸
                    'media_type': 'mt_photopaper',  # 照片紙
                    'borderless': False,  # 有邊框
                    'print_quality': 'high',  # 高品質
                    'color_mode': 'color',  # 彩色
                    'copies': 1
                }
                
                # 創建列印任務
                job_info = await self.print_service.create_print_job(photo_print_settings)
                
                # 上傳文件
                await self.print_service.upload_print_file(pdf_path, job_info['upload_uri'])
                
                # 執行列印
                await self.print_service.execute_print(job_info['job_id'])
                
                # 檢查列印狀態
                start_time = asyncio.get_event_loop().time()
                while True:
                    status = await self.print_service.get_job_status(job_info['job_id'])
                    
                    if status == 'completed':
                        if on_complete:
                            await on_complete()
                        break
                    elif status == 'failed':
                        raise Exception("列印失敗")
                    
                    # 檢查是否超過 1 分鐘
                    if asyncio.get_event_loop().time() - start_time > 60:
                        raise Exception("印表機無法回應")
                    
                    # 等待 5 秒後再檢查
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"列印過程發生錯誤：{str(e)}")
                raise
            finally:
                # 清理臨時檔案
                try:
                    os.remove(pdf_path)
                    logger.info(f"已刪除臨時 PDF：{pdf_path}")
                except:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"列印照片時發生錯誤：{str(e)}")
            raise
            
    async def create_4x6_photo(self, image_path, output_filename=None):
        """將圖片轉換為 4x6 英吋的照片 PDF"""
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"找不到圖片：{image_path}")
                
            # 如果沒有指定輸出檔名，使用原檔名
            if output_filename is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_filename = f"{base_name}_4x6.pdf"
            
            output_path = os.path.join(self.pdf_dir, output_filename)
            
            # 在線程池中執行同步操作
            import asyncio
            def process_pdf():
                try:
                    # 開啟圖片
                    img = Image.open(image_path)
                    
                    # 獲取圖片尺寸
                    img_width, img_height = img.size
                    logger.info(f"原始圖片尺寸: {img_width}x{img_height}")
                    
                    # 4x6 英吋照片尺寸（以 72dpi 為例）
                    # 4 英吋 = 4 * 72 = 288 像素，6 英吋 = 6 * 72 = 432 像素
                    # 但我們使用更高的 DPI 以獲得更好的列印質量
                    dpi = 300
                    photo_width = 4 * dpi  # 4 英吋
                    photo_height = 6 * dpi  # 6 英吋
                    
                    # 確定照片方向
                    is_portrait = img_height > img_width
                    
                    # 根據照片方向調整 PDF 尺寸
                    if is_portrait:
                        # 直式照片：使用 4x6 直向
                        pdf_width = photo_width
                        pdf_height = photo_height
                    else:
                        # 橫式照片：使用 6x4 橫向
                        pdf_width = photo_height
                        pdf_height = photo_width
                    
                    logger.info(f"PDF 尺寸: {pdf_width}x{pdf_height}, 方向: {'直式' if is_portrait else '橫式'}")
                    
                    # 計算縮放比例（保持長寬比）
                    width_ratio = (pdf_width * 0.9) / img_width  # 留 10% 邊距
                    height_ratio = (pdf_height * 0.9) / img_height  # 留 10% 邊距
                    ratio = min(width_ratio, height_ratio)
                    
                    # 計算新的尺寸
                    new_width = int(img_width * ratio)
                    new_height = int(img_height * ratio)
                    logger.info(f"縮放後的圖片尺寸: {new_width}x{new_height}, 縮放比例: {ratio}")
                    
                    # 縮放圖片
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # 計算居中位置
                    x = (pdf_width - new_width) / 2
                    y = (pdf_height - new_height) / 2
                    
                    # 建立 PDF
                    c = canvas.Canvas(output_path, pagesize=(pdf_width, pdf_height))
                    
                    # 添加白色背景
                    c.setFillColorRGB(1, 1, 1)  # 白色
                    c.rect(0, 0, pdf_width, pdf_height, fill=True, stroke=False)
                    
                    # 繪製圖片
                    c.drawImage(image_path, x, y, width=new_width, height=new_height)
                    
                    # 保存 PDF
                    c.save()
                    
                    logger.info(f"成功創建 4x6 照片 PDF：{output_path}")
                    return output_path
                except Exception as e:
                    logger.error(f"處理 PDF 時發生錯誤：{str(e)}")
                    logger.error(traceback.format_exc())
                    raise
            
            return await asyncio.to_thread(process_pdf)
            
        except Exception as e:
            logger.error(f"創建 4x6 照片 PDF 時發生錯誤：{str(e)}")
            logger.error(traceback.format_exc())
            raise
