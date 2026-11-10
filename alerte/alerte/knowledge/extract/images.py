"""Image files (PNG, JPEG, TIFF incl. multi-page, BMP, WebP, GIF): every frame is a page read by OCR."""

from __future__ import annotations

import numpy as np
from pathlib import Path

from alerte.knowledge.extract import ocr
from alerte.knowledge.extract.result import ExtractionResult, PageResult

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".gif", ".jp2"}


def extract_image(path: Path, language: str | None = None, thorough: bool = False) -> ExtractionResult:
    from PIL import Image, ImageOps, ImageSequence
    res = ExtractionResult(path=str(path))
    try:
        im = Image.open(path)
    except Exception as e:
        res.failed = f"cannot open image: {e}"
        return res
    st = ocr.status()
    langs = ocr.langs_for(language)
    for n, frame in enumerate(ImageSequence.Iterator(im), 1):
        fr = ImageOps.exif_transpose(frame.convert("RGBA" if "A" in frame.getbands() else "RGB"))
        arr = np.array(fr)
        if arr.ndim == 3:
            arr = arr[:, :, ::-1].copy() if arr.shape[2] == 3 else arr
        if not st.available:
            res.pages.append(PageResult(n, "", "none", None, None, 0, 0, ["NEEDS-OCR-ENGINE: install Tesseract (python -m alerte ocr-setup)"]))
            continue
        try:
            r = ocr.ocr_page_image(arr, langs, thorough)
            res.pages.append(PageResult(n, r.text, "ocr", round(r.confidence, 1), round(r.agreement, 3), r.tables, 0, r.flags))
        except Exception as e:
            res.pages.append(PageResult(n, "", "none", None, None, 0, 0, [f"OCR-FAILED: {e}"]))
    if not res.text.strip():
        res.failed = "no text found in the image"
    return res
