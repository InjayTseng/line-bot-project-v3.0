import os
import base64
import json
import logging
import aiohttp
from urllib.parse import urlencode
from src.config import settings

logger = logging.getLogger(__name__)

class PrintService:
    def __init__(self):
        self.host = settings.PRINTER_HOST
        self.client_id = settings.PRINTER_CLIENT_ID
        self.secret = settings.PRINTER_SECRET
        self.email = settings.PRINTER_EMAIL
        self.base_url = f'https://{self.host}/api/1/printing'
        self._access_token = None
        self._device_id = None
        self._subject_id = None
        
    def _get_basic_auth(self):
        """獲取 Basic Auth Header"""
        auth = base64.b64encode(
            f"{self.client_id}:{self.secret}".encode()
        ).decode()
        return f'Basic {auth}'

    def _get_device_id(self):
        """獲取印表機設備 ID"""
        return 'selinnaowen@print.epsonconnect.com'

    async def authenticate_device(self):
        """使用設備 ID 進行認證"""
        try:
            self._device_id = self._get_device_id()
            logger.info(f"使用設備 ID: {self._device_id}")

            headers = {
                'Authorization': self._get_basic_auth(),
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
                'Accept': 'application/json;charset=utf-8'
            }
            logger.debug(f"認證標頭: {headers}")

            data = {
                'grant_type': 'password',
                'username': self._device_id,  # 使用設備 ID
                'password': ''  # 空密碼
            }

            auth_uri = f'{self.base_url}/oauth2/auth/token?subject=printer'
            query_string = urlencode(data)
            logger.debug(f"發送認證請求到: {auth_uri}")
            logger.debug(f"請求參數: {query_string}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    auth_uri,
                    headers=headers,
                    data=query_string.encode('utf-8')
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"回應狀態: {response.status}")
                    logger.debug(f"回應內容: {response_text}")

                    if response.status != 200:
                        logger.error(f"認證失敗: {response.status} - {response_text}")
                        raise Exception(f"認證失敗: {response.status} - {response_text}")

                    result = json.loads(response_text)
                    self._access_token = result.get('access_token')
                    self._subject_id = result.get('subject_id')
                    logger.info(f"認證成功，subject_id: {self._subject_id}")

                    return {
                        'access_token': self._access_token,
                        'device_id': self._device_id
                    }

        except Exception as e:
            logger.error(f"認證過程發生錯誤: {str(e)}")
            raise

    async def initial_authentication(self):
        """初始認證，獲取 access_token 和 device_id"""
        return await self.authenticate_device()

    async def create_print_job(self):
        """創建列印任務"""
        try:
            if not self._access_token:
                await self.authenticate_device()

            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json;charset=utf-8'
            }

            data = {
                'job_name': 'LINE Bot Print Job',
                'print_mode': 'document',  # 使用 document 模式
                'print_setting': {
                    'media_size': 'ms_a4',
                    'media_type': 'mt_plainpaper',
                    'borderless': False,
                    'print_quality': 'normal',
                    'source': 'auto',
                    'color_mode': 'color',
                    'reverse_order': False,
                    'copies': 1,
                    'collate': False
                }
            }

            job_uri = f'{self.base_url}/printers/{self._subject_id}/jobs?subject=printer'
            logger.debug(f"發送創建列印任務請求到: {job_uri}")
            logger.debug(f"請求參數: {json.dumps(data)}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    job_uri,
                    headers=headers,
                    json=data
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"回應狀態: {response.status}")
                    logger.debug(f"回應內容: {response_text}")

                    if response.status != 201:  # 創建成功應該返回 201
                        logger.error(f"創建列印任務失敗: {response.status} - {response_text}")
                        raise Exception(f"創建列印任務失敗: {response.status}")

                    result = json.loads(response_text)
                    logger.info("創建列印任務成功")
                    return {
                        'job_id': result.get('id'),
                        'upload_uri': result.get('upload_uri')
                    }

        except Exception as e:
            logger.error(f"創建列印任務過程發生錯誤: {str(e)}")
            raise

    async def upload_print_file(self, file_path, upload_uri):
        """上傳列印文件"""
        try:
            # 從檔案路徑獲取副檔名
            _, ext = os.path.splitext(file_path)
            file_name = f'1{ext}'  # 使用簡單的檔案名

            # 添加檔案名到 upload_uri
            upload_uri = f"{upload_uri}&File={file_name}"

            # 準備檔案大小
            file_size = os.path.getsize(file_path)

            headers = {
                'Content-Length': str(file_size),
                'Content-Type': 'application/octet-stream'
            }

            logger.debug(f"發送上傳文件請求到: {upload_uri}")
            logger.debug(f"檔案路徑: {file_path}")
            logger.debug(f"檔案大小: {file_size} bytes")

            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as f:
                    async with session.post(
                        upload_uri,
                        headers=headers,
                        data=f
                    ) as response:
                        response_text = await response.text()
                        logger.debug(f"回應狀態: {response.status}")
                        logger.debug(f"回應內容: {response_text}")

                        if response.status != 200:
                            logger.error(f"上傳文件失敗: {response.status} - {response_text}")
                            raise Exception(f"上傳文件失敗: {response.status}")

                        logger.info("上傳文件成功")
                        return True

        except Exception as e:
            logger.error(f"上傳文件過程發生錯誤: {str(e)}")
            raise

    async def execute_print(self, job_id):
        """執行列印"""
        try:
            if not self._access_token:
                await self.authenticate_device()

            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json;charset=utf-8'
            }

            print_uri = f'{self.base_url}/printers/{self._subject_id}/jobs/{job_id}/print?subject=printer'
            logger.debug(f"發送執行列印請求到: {print_uri}")

            async with aiohttp.ClientSession() as session:
                data = json.dumps({})
                headers['Content-Type'] = 'application/json; charset=utf-8'
                async with session.post(
                    print_uri,
                    headers=headers,
                    data=data
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"回應狀態: {response.status}")
                    logger.debug(f"回應內容: {response_text}")

                    if response.status != 200:
                        logger.error(f"執行列印失敗: {response.status} - {response_text}")
                        raise Exception(f"執行列印失敗: {response.status}")

                    logger.info("執行列印成功")
                    return True

        except Exception as e:
            logger.error(f"執行列印過程發生錯誤: {str(e)}")
            raise

    async def get_printer_info(self):
        """搜尋可用的印表機"""
        try:
            if not self._access_token:
                await self.authenticate_device()

            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Accept': 'application/json;charset=utf-8'
            }

            info_uri = f'{self.base_url}/printers/{self._subject_id}?subject=printer'
            logger.debug(f"發送印表機資訊請求到: {info_uri}")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    info_uri,
                    headers=headers
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"回應狀態: {response.status}")
                    logger.debug(f"回應內容: {response_text}")

                    if response.status != 200:
                        logger.error(f"取得印表機資訊失敗: {response.status} - {response_text}")
                        raise Exception(f"取得印表機資訊失敗: {response.status}")

                    result = json.loads(response_text)
                    if not result:
                        logger.warning("未取得印表機資訊")
                        return None
                        
                    logger.info("印表機資訊:")
                    logger.info(f"- 名稱: {result.get('printer_name')}")
                    logger.info(f"- 序號: {result.get('serial_no')}")
                    logger.info(f"- 連線狀態: {result.get('ec_connected')}")

                    # 如果印表機未連線，記錄警告
                    if not result.get('ec_connected'):
                        logger.warning("印表機未連線到 Epson Connect")

                    return result

        except Exception as e:
            logger.error(f"取得印表機資訊過程發生錯誤: {str(e)}")
            raise

    async def check_printer_status(self):
        """檢查印表機狀態"""
        try:
            if not self._access_token:
                await self.authenticate_device()

            # 先取得印表機資訊
            printer_info = await self.get_printer_info()
            if not printer_info:
                raise Exception("未取得印表機資訊，請確保印表機已開機並連線")
            
            # 檢查印表機連線狀態
            if not printer_info.get('ec_connected'):
                raise Exception("印表機未連線到 Epson Connect，請確保印表機已開機並連線到網路")

            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'Accept': 'application/json;charset=utf-8'
            }

            status_uri = f'{self.base_url}/printers/{self._subject_id}?subject=printer'
            logger.debug(f"發送狀態查詢請求到: {status_uri}")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    status_uri,
                    headers=headers
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"回應狀態: {response.status}")
                    logger.debug(f"回應內容: {response_text}")

                    if response.status != 200:
                        logger.error(f"狀態查詢失敗: {response.status} - {response_text}")
                        raise Exception(f"狀態查詢失敗: {response.status}")

                    result = json.loads(response_text)
                    # 詳細記錄印表機狀態
                    logger.info("印表機狀態:")
                    logger.info(f"- 名稱: {result.get('printer_name')}")
                    logger.info(f"- 序號: {result.get('serial_no')}")
                    logger.info(f"- 連線狀態: {result.get('ec_connected')}")

                    return result

        except Exception as e:
            logger.error(f"狀態查詢過程發生錯誤: {str(e)}")
            raise

    async def print_image(self, image_path):
        """完整的列印流程"""
        try:
            # 1. 認證
            logger.info("步驟 1/5: 認證中...")
            await self.authenticate_device()

            # 2. 檢查印表機狀態
            logger.info("步驟 2/5: 檢查印表機狀態...")
            printer_status = await self.check_printer_status()
            
            if not printer_status.get('ec_connected'):
                raise Exception("印表機未連線到 Epson Connect")

            # 3. 創建列印任務
            logger.info("步驟 3/5: 創建列印任務...")
            job_info = await self.create_print_job()

            # 4. 上傳文件
            logger.info("步驟 4/5: 上傳圖片...")
            await self.upload_print_file(image_path, job_info['upload_uri'])

            # 5. 執行列印
            logger.info("步驟 5/5: 執行列印...")
            await self.execute_print(job_info['job_id'])

            logger.info("列印流程完成")
            return True

        except Exception as e:
            logger.error(f"列印流程發生錯誤: {str(e)}")
            raise
