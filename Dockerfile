
FROM python:3.11-slim

# 2. Вимикаємо створення кеш-файлів .pyc (вони в контейнері не треба)
ENV PYTHONDONTWRITEBYCODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no--cache-dir -r requirements.txt

COPY . .

CMD ["uvicron","main:app","--host","0.0.0.0","--port","8000"]