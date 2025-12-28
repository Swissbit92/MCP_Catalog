# src/coordinator/services/__init__.py
"""Service layer for business logic.

Phase 2 Core Refactoring: Extracted services from llm_client.py
- LLMCompletionService: Basic LLM completion
- ToolCallingService: Autonomous tool calling orchestration
- CitationService: Citation generation and validation
"""

# Phase 2: New extracted services
from .llm_completion_service import LLMCompletionService
from .tool_calling_service import ToolCallingService
from .citation_service import CitationService

# Legacy function exports (for backward compatibility)
from .first_person_service import (
    detect_third_person,
    rewrite_to_first_person,
    post_process_first_person
)

__all__ = [
    # Phase 2: New service classes
    "LLMCompletionService",
    "ToolCallingService",
    "CitationService",
    # Legacy functions
    "detect_third_person",
    "rewrite_to_first_person",
    "post_process_first_person",
]
