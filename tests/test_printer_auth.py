import os
import sys
import asyncio
import logging
import json

# 添加專案根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.services.print_service import PrintService
from src.config import settings

# 設定日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_authentication():
    print_service = PrintService()
    
    # 列印設定資訊
    logger.info("=== 印表機設定 ===")
    logger.info(f"Host: {settings.PRINTER_HOST}")
    logger.info(f"Client ID: {settings.PRINTER_CLIENT_ID}")
    logger.info(f"Email: {settings.PRINTER_EMAIL}")
    
    try:
        logger.info("\n=== 開始認證 ===")
        result = await print_service.initial_authentication()
        
        logger.info("\n=== 認證結果 ===")
        logger.info(f"Access Token: {result['access_token']}")
        logger.info(f"Device ID: {result['device_id']}")
        
        print("\n認證成功！")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"\n認證失敗：{str(e)}")

if __name__ == "__main__":
    asyncio.run(test_authentication())
