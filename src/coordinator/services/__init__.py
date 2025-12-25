# src/coordinator/services/__init__.py
"""Service layer for business logic."""

from .citation_service import validate_citations
from .first_person_service import (
    detect_third_person,
    rewrite_to_first_person,
    post_process_first_person
)

__all__ = [
    "validate_citations",
    "detect_third_person",
    "rewrite_to_first_person",
    "post_process_first_person",
]
