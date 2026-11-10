# ALERTE container (works on any OS with Docker, and in cloud sandboxes)
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
WORKDIR /app/alerte
COPY requirements.txt requirements-full.txt ./
RUN pip install -r requirements.txt
COPY . .
RUN python -m alerte ingest --itu no
EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1
CMD ["python", "-m", "alerte", "ui", "--headless", "--port", "8501"]
