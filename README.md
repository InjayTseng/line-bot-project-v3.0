# LINE Bot 相片列印服務

這是一個 LINE Bot 應用程式，可以接收用戶上傳的照片，讓用戶選擇相框樣式，並將處理後的照片傳回給用戶。

## 功能特點

- 接收並儲存用戶上傳的圖片
- 支援多種圖片格式（PNG、JPG、JPEG、GIF）
- 提供多種相框樣式供用戶選擇
- 即時處理圖片並回傳結果

## 已完成功能

- [x] 基本的 LINE Bot 設定和連接
- [x] 處理用戶上傳的圖片
- [x] 實現框架選擇功能
- [x] 圖片處理和回傳功能

## 待完成功能

- [ ] 添加更多相框樣式
- [ ] 實現圖片列印功能
- [ ] 優化圖片處理效果
- [ ] 添加用戶使用說明

## 技術需求

- Python 3.9+
- Flask
- LINE Messaging API
- Pillow (用於圖片處理)
- ngrok (用於開發測試)

## 環境變數設置

1. 複製 `.env.example` 到 `.env`：
   ```bash
   cp .env.example .env
   ```

2. 編輯 `.env` 文件，填入您的 LINE Channel 資訊：
   ```
   LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token_here
   LINE_CHANNEL_SECRET=your_channel_secret_here
   ```

3. 在 Render.com 部署時，請在環境變數設置中添加相同的變數。

## 安裝說明

1. 安裝所需套件：
   ```bash
   pip install -r requirements.txt
   ```

2. 設定 LINE Bot 頻道：
   - 在 LINE Developers Console 建立一個新的 Provider 和 Channel
   - 設定 Webhook URL
   - 更新程式碼中的 Channel Access Token 和 Channel Secret

3. 啟動應用程式：
   ```bash
   python app.py
   ```

## 開發注意事項

- 使用 ngrok 進行本地開發時，需要更新 LINE Developer Console 中的 Webhook URL
- 圖片 URL 必須使用 HTTPS
- 上傳的圖片會暫存在 `static/uploads` 目錄中

## 專案結構

```
line-bot-project-v3.0/
├── app.py              # 主程式
├── requirements.txt    # 相依套件
├── static/            
│   └── uploads/       # 圖片上傳目錄
└── README.md          # 說明文件
