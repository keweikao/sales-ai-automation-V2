FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY web-service/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY web-service/src ./src
COPY web-service/templates ./templates
COPY web-service/static ./static

CMD ["gunicorn", "-b", "0.0.0.0:8080", "src.main:app"]
