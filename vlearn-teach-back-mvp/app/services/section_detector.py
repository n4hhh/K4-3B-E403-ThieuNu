"""SectionDetector — identify logical sections in extracted PDF pages.

Heuristic
---------
We look for headings on each page. A line is treated as a heading when it
matches one of these patterns (after stripping):

    * ``Chapter N`` / ``CHAPTER N``
    * ``Section N.M`` / ``SECTION N.M``
    * Numbered headings like ``1. Introduction`` or ``2.3 Subtopic``
    * ALL-CAPS lines (3–80 chars, mostly letters)

If no heading is found, the section continues with the previous heading
(or ``"Introduction"`` for the first section).

The detector never modifies the source PDF; it only inspects already
extracted text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from app.models.raw_document import PageText


# Lines that are mostly uppercase letters (with digits and a few symbols
# allowed) are considered ALL-CAPS headings.
ALL_CAPS_RE = re.compile(r"^[A-ZÀ-Ỹ0-9][A-ZÀ-Ỹ0-9 \.\-:&\(\)/]{2,80}$")

CHAPTER_RE = re.compile(
    r"^\s*(?:chapter|chương|chuong)\s+([0-9]+|[ivxlcdm]+)\b[ \t\-:]*(.*)$",
    re.IGNORECASE,
)
SECTION_RE = re.compile(
    r"^\s*(?:section|phần|phan)\s+([0-9]+(?:\.[0-9]+)*)\b[ \t\-:]*(.*)$",
    re.IGNORECASE,
)
NUMBERED_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)*)\.?\s+([A-ZÀ-Ỹ][^\.]{2,80})$")


@dataclass
class DetectedSection:
    """A section discovered in the PDF text."""

    title: str
    start_page: int
    end_page: int = 0
    pages: List[PageText] = field(default_factory=list)

    @property
    def content(self) -> str:
        """Combined normalized text from all pages in the section."""
        return "\n\n".join(p.text for p in self.pages if p.text)

    @property
    def page_count(self) -> int:
        return len(self.pages)


class SectionDetector:
    """Detect logical sections from extracted page text."""

    def detect(self, pages: List[PageText]) -> List[DetectedSection]:
        """Group pages into sections based on detected headings.

        If no headings can be detected at all, each page becomes its own
        section with a generic title like ``"Page 3"``.
        """
        if not pages:
            return []

        sections: List[DetectedSection] = []
        current: DetectedSection | None = None
        headings_found = 0

        for page in pages:
            heading = self._find_heading(page.text)
            if heading:
                # Close out the previous section
                if current is not None:
                    current.end_page = page.page_number - 1
                    if current.page_count > 0:
                        sections.append(current)
                current = DetectedSection(
                    title=heading,
                    start_page=page.page_number,
                    pages=[page],
                )
                headings_found += 1
            else:
                if current is None:
                    current = DetectedSection(
                        title=f"Section starting at page {page.page_number}",
                        start_page=page.page_number,
                        pages=[page],
                    )
                else:
                    current.pages.append(page)

        # Close out the final section
        if current is not None:
            current.end_page = pages[-1].page_number
            if current.page_count > 0:
                sections.append(current)

        # If we never found a heading, fall back to per-page sections.
        if headings_found == 0:
            return [
                DetectedSection(
                    title=f"Page {p.page_number}",
                    start_page=p.page_number,
                    end_page=p.page_number,
                    pages=[p],
                )
                for p in pages
                if p.text.strip()
            ]

        return sections

    # ------------------------------------------------------------------
    # Heading detection
    # ------------------------------------------------------------------

    def _find_heading(self, page_text: str) -> str | None:
        """Return a heading string if one is detected on the page."""
        if not page_text:
            return None

        # Look at the first ~20 lines only (headings are usually near the top).
        lines = page_text.split("\n")[:20]
        for raw in lines:
            line = raw.strip()
            if not line:
                continue

            m = CHAPTER_RE.match(line)
            if m:
                title = line.strip()
                return self._clean_title(title)

            m = SECTION_RE.match(line)
            if m:
                title = line.strip()
                return self._clean_title(title)

            m = NUMBERED_RE.match(line)
            if m:
                return self._clean_title(f"{m.group(1)}. {m.group(2)}")

            if self._looks_like_all_caps_heading(line):
                return self._clean_title(line)

        return None

    @staticmethod
    def _looks_like_all_caps_heading(line: str) -> bool:
        """Detect ALL-CAPS headings without false positives."""
        if not ALL_CAPS_RE.match(line):
            return False
        # Must contain at least 3 letters to avoid matching things like "1.0"
        letters = sum(1 for c in line if c.isalpha())
        return letters >= 3

    @staticmethod
    def _clean_title(title: str) -> str:
        """Trim and tidy a detected heading."""
        title = title.strip()
        # Remove trailing punctuation like "."
        title = title.rstrip(".:;,-")
        # Collapse repeated whitespace
        return " ".join(title.split())
