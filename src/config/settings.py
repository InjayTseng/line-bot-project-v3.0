import os
from dotenv import load_dotenv

load_dotenv()

# LINE Bot 設定
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', None)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)

# Cloudinary 設定
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', None)
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', None)
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', None)

# 印表機設定
PRINTER_HOST = os.getenv('PRINTER_HOST', None)
PRINTER_CLIENT_ID = os.getenv('PRINTER_CLIENT_ID', None)
PRINTER_SECRET = os.getenv('PRINTER_SECRET', None)
PRINTER_EMAIL = os.getenv('PRINTER_EMAIL', None)

# 應用程式設定
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tmp', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 確保上傳目錄存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 相框樣式設定
FRAME_STYLES = {
    '1': '可愛風格',
    '2': '復古風格',
    '3': '簡約風格'
}

# 相框文件設定
FRAME_FILES = {
    '可愛風格': 'cute.png',
    '復古風格': 'vintage.png',
    '簡約風格': 'only-frame.png'
}

# 方向相關相框設定
PORTRAIT_FRAME = 'only-frame-protrait.png'  # 直式相框
LANDSCAPE_FRAME = 'only-frame-land.png'     # 橫式相框

# 預設框架風格
DEFAULT_FRAME_STYLE = '簡約風格'

# 部署相關設定
IS_RENDER = os.getenv('RENDER', 'false').lower() == 'true'
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL', None)
NGROK_URL = os.getenv('NGROK_URL', None)

def get_base_url():
    """獲取基礎 URL"""
    # 從環境變數獲取 NGROK_URL，如果不存在則使用預設值
    current_ngrok_url = os.getenv('NGROK_URL', None)
    
    if IS_RENDER and RENDER_EXTERNAL_URL:
        return RENDER_EXTERNAL_URL
    elif current_ngrok_url:
        return current_ngrok_url
    return 'http://localhost:8080'
