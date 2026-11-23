# ALERTE setup for Windows (PowerShell). Run once:
#   powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = "py"
if (-not (Get-Command $py -ErrorAction SilentlyContinue)) { $py = "python" }
if (-not (Get-Command $py -ErrorAction SilentlyContinue)) {
  Write-Host "Python 3.10+ is required: https://www.python.org/downloads/ (tick 'Add python.exe to PATH')"; exit 1
}
& $py -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if ($LASTEXITCODE -ne 0) { Write-Host "Python 3.10 or newer is required"; exit 1 }
& $py -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
# OCR engine (Tesseract) for scanned documents
$tess = (Get-Command tesseract -ErrorAction SilentlyContinue) -or (Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe")
if (-not $tess) {
  Write-Host "Installing the Tesseract OCR program ..."
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget install --id UB-Mannheim.TesseractOCR -e --accept-source-agreements --accept-package-agreements
  } else {
    Write-Host "Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki then run: .\.venv\Scripts\python.exe -m alerte ocr-setup"
  }
}
& .\.venv\Scripts\python.exe -m alerte ocr-setup
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
& .\.venv\Scripts\python.exe -m alerte ingest
& .\.venv\Scripts\python.exe -m alerte run ae-core
Write-Host ""
Write-Host "Done. Next time:  .\.venv\Scripts\python.exe -m alerte ui"
