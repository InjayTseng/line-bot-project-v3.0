import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# 設定 logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 添加 src 到 Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.printer_service import PrinterService
from src.services.print_service import PrintService

def get_test_image():
    """獲取測試圖片路徑"""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'samples', 'sample.jpeg')

async def main():
    try:
        # 載入環境變數
        load_dotenv()
        
        # 顯示設定
        logger.info("=== 印表機設定 ===")
        logger.info(f"Host: {os.getenv('PRINTER_HOST')}")
        logger.info(f"Client ID: {os.getenv('PRINTER_CLIENT_ID')}")
        logger.info(f"Email: {os.getenv('PRINTER_EMAIL')}")
        
        # 初始化服務
        printer_service = PrinterService()
        print_service = PrintService()
        
        # 測試圖片路徑
        image_path = get_test_image()
        logger.info(f"\n使用測試圖片: {image_path}")
        
        # 創建 4x6 照片 PDF
        logger.info("\n=== 創建 4x6 照片 PDF ===")
        pdf_path = printer_service.create_4x6_photo(image_path)
        logger.info(f"PDF 已創建: {pdf_path}")
        
        # 列印 PDF
        logger.info("\n=== 列印 4x6 照片 ===")
        await print_service.print_image(pdf_path)
        
        logger.info("\n測試完成！")
        
    except Exception as e:
        logger.error(f"\n測試失敗：{str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
