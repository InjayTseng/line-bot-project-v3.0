# 使用 Python 3.11 作為基礎映像
FROM python:3.11-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt 並安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程序代碼
COPY . .

# 創建必要的目錄
RUN mkdir -p static/pdf tmp/uploads

# 設置環境變數
ENV PORT=5000
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 5000

# 啟動應用
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "5000"] 