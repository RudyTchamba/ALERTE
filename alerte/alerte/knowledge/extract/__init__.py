"""Text extraction from any document: digital or scanned, with tables and pictures. See pipeline.extract_file."""

from alerte.knowledge.extract.pipeline import SUPPORTED, discover_files, extract_file, is_sidecar, sidecar_for  # noqa: F401
from alerte.knowledge.extract.result import ExtractionResult, PageResult  # noqa: F401
