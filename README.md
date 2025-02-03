# LINE Bot 相片框列印專案

## 專案簡介
這是一個基於 LINE Messaging API 開發的 Bot 應用程式，主要功能包括：
1. 上傳照片：使用者可以透過 LINE 傳送照片
2. 選擇相框：提供多種相框樣式供使用者選擇
3. 套用相框：將選定的相框套用在使用者的照片上
4. 列印功能：支援 Epson 印表機直接列印處理後的照片

## 系統需求
- Python 3.9+
- Flask 框架
- LINE Messaging API
- ngrok (用於開發環境)
- Epson 印表機驅動程式

## 安裝步驟
1. 安裝必要套件：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. 設定 LINE Bot 認證資訊：
- 在 LINE Developers Console 建立一個新的 Channel
- 取得 Channel Secret 和 Channel Access Token
- 將認證資訊更新到 `app.py` 中的相應變數

3. 啟動本地伺服器：
```bash
python3 app.py
```

4. 使用 ngrok 建立通道：
```bash
./ngrok http 8000
```

## 使用說明
1. 將 LINE Bot 加為好友
2. 傳送照片給 Bot
3. 根據 Bot 的提示選擇相框樣式
4. 確認完成後，照片將自動進行列印

## 功能特點
- 支援多種相框樣式
- 即時照片處理
- 自動列印功能
- 使用者友善的操作介面

## 開發者資訊
- 專案開發時間：2025年
- 開發環境：macOS
- 使用框架：Flask
- 程式語言：Python

## 注意事項
- 請確保印表機已正確連接並設定
- 建議在開發時使用 ngrok 進行測試
- 注意 LINE Messaging API 的使用限制

## 授權資訊
本專案採用 MIT 授權條款
