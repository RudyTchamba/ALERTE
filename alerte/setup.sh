#!/usr/bin/env bash
# ALERTE setup for macOS and Linux. Run once:  bash setup.sh
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Python 3.10+ is required: https://www.python.org/downloads/"; exit 1
fi
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' || { echo "Python 3.10 or newer is required"; exit 1; }
"$PY" -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
# OCR engine (Tesseract) for scanned documents
if ! command -v tesseract >/dev/null 2>&1; then
  echo "Installing the Tesseract OCR program ..."
  if command -v brew >/dev/null 2>&1; then brew install tesseract || true
  elif command -v apt-get >/dev/null 2>&1; then (sudo -n apt-get install -y tesseract-ocr || sudo apt-get install -y tesseract-ocr) || true
  elif command -v dnf >/dev/null 2>&1; then sudo dnf install -y tesseract || true
  fi
fi
python -m alerte ocr-setup || echo "OCR is not ready: install Tesseract (see the message above), then run: python -m alerte ocr-setup"
[ -f .env ] || cp .env.example .env
python -m alerte ingest
python -m alerte run ae-core
echo
echo "Done. Next time:  source .venv/bin/activate && python -m alerte ui"
