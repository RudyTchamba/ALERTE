# Image « application » d'ALERTE : API FastAPI + interface React (servie par l'API) + Tesseract (OCR fra/eng/ara).
# Construire depuis alerte-platform/ :  docker build -f deploy/docker/Dockerfile -t alerte-app .
# Les MODÈLES d'IA ne sont PAS dans cette image : ils sont joints par URL (ALERTE_LLM_BASE_URL, ALERTE_EMBED_BASE_URL).
# STATUT : écrit à partir des fichiers du dépôt ; la construction complète n'a pas été exécutée dans cet environnement (voir docs/deploiement/).

FROM node:22-slim AS web
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS app
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng tesseract-ocr-ara \
        libpango-1.0-0 libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
# L'API sert frontend/dist si le dossier existe (backend/app/main.py) : même arborescence relative que dans le dépôt.
COPY --from=web /src/frontend/dist /app/frontend/dist
# Donnée persistante dans un volume (jamais dans l'image) ; l'OCR utilise les langues installées ci-dessus.
ENV ALERTE_DATA_DIR=/data \
    ALERTE_LOG_JSON=true \
    PYTHONUNBUFFERED=1
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status==200 else 1)"
CMD ["python", "-m", "uvicorn", "app.main:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000"]
