# LINE Bot 相片列印服務

這是一個 LINE Bot 應用程式，可以接收用戶上傳的照片，套用精美相框，並將處理後的照片傳回給用戶。使用 Cloudinary 進行圖片存儲和處理，確保高效且穩定的服務。

## 功能特點

- 接收並處理用戶上傳的圖片
- 支援多種圖片格式（PNG、JPG、JPEG、GIF）
- 提供精選相框樣式：
  - 可愛風格
  - 復古風格
- 使用 Cloudinary 進行圖片存儲和處理
- 模組化的程式架構，易於維護和擴展

## 已完成功能

- [x] 基本的 LINE Bot 設定和連接
- [x] 完整的圖片上傳和處理流程
- [x] 整合 Cloudinary 圖片服務
- [x] 實現框架選擇功能
- [x] 優化圖片處理效果
- [x] 模組化程式架構

## 技術需求

- Python 3.9+
- Flask 2.3.3
- LINE Messaging API SDK 3.5.0
- Pillow 10.0.0 (圖片處理)
- Cloudinary 1.36.0 (圖片存儲)
- python-dotenv 1.0.0 (環境變數管理)

## 環境變數設置

1. 複製 `.env.example` 到 `.env`：
   ```bash
   cp .env.example .env
   ```

2. 編輯 `.env` 文件，填入必要的設定：
   ```
   # LINE Bot 設定
   LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token_here
   LINE_CHANNEL_SECRET=your_channel_secret_here

   # Cloudinary 設定
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret

   # 部署設定（Render.com）
   RENDER=true
   RENDER_EXTERNAL_URL=your-app-name.onrender.com
   ```

## 安裝和部署

1. 安裝所需套件：
   ```bash
   pip install -r requirements.txt
   ```

2. 本地開發：
   ```bash
   python run.py
   ```

3. 部署到 Render.com：
   - 使用 `render.yaml` 進行設定
   - 確保所有環境變數都已正確設置

## 專案結構

```
line-bot-project-v3.0/
├── src/                    # 主要程式碼
│   ├── __init__.py
│   ├── app.py             # 應用程式入口
│   ├── config/            # 設定檔
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── handlers/          # 訊息處理器
│   │   ├── __init__.py
│   │   └── message_handler.py
│   ├── services/          # 服務層
│   │   ├── __init__.py
│   │   ├── image_service.py
│   │   └── line_service.py
│   └── utils/             # 工具函數
│       └── __init__.py
├── static/                # 靜態資源
│   └── frames/           # 相框圖片
├── tmp/                   # 暫存目錄
│   └── uploads/          # 上傳的圖片
├── .env.example          # 環境變數範例
├── requirements.txt      # 相依套件
├── render.yaml           # Render.com 設定
└── run.py               # 啟動腳本
```

## 開發注意事項

- 本地開發時使用 `run.py` 啟動應用程式
- 確保 Cloudinary 和 LINE Bot 的設定正確
- 圖片處理時會自動處理 RGBA/RGB 轉換
- 相框圖片存放在 `static/frames` 目錄
- 上傳的圖片暫存在 `tmp/uploads` 目錄

## 貢獻指南

1. Fork 專案
2. 建立功能分支
3. 提交變更
4. 發送 Pull Request

## 授權

本專案採用 MIT 授權條款。詳見 LICENSE 文件。
