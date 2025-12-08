FROM python:3.11-slim

WORKDIR /app

# 安裝依賴
COPY sms-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY sms-service/src/ ./src/

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# 執行應用
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 src.main:app
