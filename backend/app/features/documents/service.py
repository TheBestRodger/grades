from __future__ import annotations

from .links import set_work_document_link
from .quality import get_work_document_source, review_work_document_quality
from .registry import get_document_registry, get_manager_document_registry
from .upload import upload_work_document

__all__ = [
    "get_document_registry",
    "get_manager_document_registry",
    "get_work_document_source",
    "review_work_document_quality",
    "set_work_document_link",
    "upload_work_document",
]
