"""Result types shared by every extractor."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

EXTRACTOR_VERSION = "2.2"


@dataclass
class PageResult:
    page: int
    text: str
    method: str                       # text-layer | ocr | text-layer+image-ocr | text-layer (verified by OCR) | native | human-corrected
    confidence: float | None = None   # mean OCR word confidence 0-100; None = exact characters from the file itself
    agreement: float | None = None    # agreement between two readings of the page (0-1), when two exist
    tables: int = 0
    images_ocr: int = 0
    flags: list[str] = field(default_factory=list)

    @property
    def chars(self) -> int:
        return len(self.text.replace(" ", "").replace("\n", ""))


@dataclass
class ExtractionResult:
    path: str
    pages: list[PageResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failed: str = ""                  # non-empty: the reason no usable text could be obtained
    sha256: str = ""
    version: str = EXTRACTOR_VERSION
    corrected: bool = False           # a human-corrected sidecar replaced the machine reading
    cached: bool = False

    @property
    def text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip()).strip()

    @property
    def ocr_pages(self) -> int:
        return sum(1 for p in self.pages if p.confidence is not None)

    @property
    def tables(self) -> int:
        return sum(p.tables for p in self.pages)

    @property
    def mean_confidence(self) -> float | None:
        v = [p.confidence for p in self.pages if p.confidence is not None]
        return round(sum(v) / len(v), 1) if v else None

    @property
    def review_pages(self) -> list[int]:
        return [p.page for p in self.pages if p.flags and not self.corrected]

    @property
    def needs_review(self) -> bool:
        return bool(self.failed) or bool(self.review_pages)

    @property
    def method(self) -> str:
        if self.corrected:
            return "human-corrected"
        kinds = {p.method.split(" ")[0] for p in self.pages}
        return "+".join(sorted(kinds)) or "none"

    def label(self) -> str:
        """Short provenance string stored on each passage."""
        if self.corrected:
            return "human-corrected"
        if self.ocr_pages:
            return f"{self.method} (OCR {self.mean_confidence}%, {self.ocr_pages}/{len(self.pages)} pages)"
        return self.method

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> "ExtractionResult":
        pages = [PageResult(**p) for p in d.get("pages", [])]
        return ExtractionResult(path=d["path"], pages=pages, warnings=d.get("warnings", []), failed=d.get("failed", ""),
                                sha256=d.get("sha256", ""), version=d.get("version", ""), corrected=d.get("corrected", False))

    def report_row(self) -> dict[str, Any]:
        return {"file": self.path, "method": self.method, "pages": len(self.pages), "ocr_pages": self.ocr_pages,
                "tables": self.tables, "mean_ocr_confidence": self.mean_confidence, "chars": len(self.text),
                "review_pages": self.review_pages, "failed": self.failed, "warnings": self.warnings,
                "page_details": [{"page": p.page, "method": p.method, "confidence": p.confidence, "agreement": p.agreement,
                                  "tables": p.tables, "flags": p.flags, "chars": p.chars} for p in self.pages]}
