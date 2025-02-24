import os
import sys
import asyncio
import logging
from PIL import Image
from dotenv import load_dotenv

# 設定 logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 添加 src 到 Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.print_service import PrintService

def get_test_document():
    """獲取測試文件路徑"""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'samples', 'SampleDoc.pdf')

async def main():
    try:
        # 載入環境變數
        load_dotenv()
        
        # 顯示設定
        logger.info("=== 印表機設定 ===")
        logger.info(f"Host: {os.getenv('PRINTER_HOST')}")
        logger.info(f"Client ID: {os.getenv('PRINTER_CLIENT_ID')}")
        logger.info(f"Email: {os.getenv('PRINTER_EMAIL')}")
        
        # 初始化印表機服務
        printer = PrintService()
        
        logger.info("\n=== 取得印表機資訊 ===")
        
        # 取得印表機資訊
        printer_info = await printer.get_printer_info()
        
        if printer_info:
            logger.info("\n=== 檢查印表機狀態 ===")
            # 檢查印表機狀態
            await printer.check_printer_status()
            
            # 測試列印
            logger.info("\n=== 測試列印 ===")
            doc_path = get_test_document()
            logger.info(f"使用測試文件: {doc_path}")
            await printer.print_image(doc_path)
        
        logger.info("\n測試完成！")
        
    except Exception as e:
        logger.error(f"\n測試失敗：{str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
