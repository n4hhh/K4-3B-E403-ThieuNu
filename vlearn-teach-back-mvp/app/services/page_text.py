"""PageText model for PDF extraction.

This file provides backward-compatible access to PageText from both:
    - app.services.pdf_reader (old import location)
    - app.models.raw_document (new canonical location)
"""

from app.models.raw_document import PageText

__all__ = ["PageText"]
