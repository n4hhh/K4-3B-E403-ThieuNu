"""Generate a small synthetic PDF for tests using only the standard library.

We build a minimal valid PDF (PDF 1.4) from raw bytes. Each entry in
``pages`` becomes its own Page object so multi-page PDFs work for the
section / chunk pipeline tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import List


def _escape_pdf_string(s: str) -> str:
    """Escape characters that have a special meaning inside PDF string literals."""
    return (
        s.replace("\\", "\\\\")
         .replace("(", "\\(")
         .replace(")", "\\)")
    )


def _make_page_stream(lines: List[str]) -> bytes:
    """Return the content stream for a single page that draws ``lines``."""
    parts = ["BT", "/F1 12 Tf", "50 750 Td"]
    for line in lines:
        parts.append(f"({_escape_pdf_string(line)}) Tj")
        parts.append("0 -14 Td")
    parts.append("ET")
    return " ".join(parts).encode("latin-1", errors="replace")


def _make_pdf_bytes(pages: List[List[str]]) -> bytes:
    """Return the raw bytes of a minimal multi-page PDF.

    Each element of ``pages`` becomes one Page object with one content stream.
    """
    objects: List[bytes] = []

    n_pages = max(1, len(pages))
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n_pages))

    # 1. Catalog
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    # 2. Pages
    objects.append(
        f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode("latin-1")
    )

    # 3..(3+2n-1) : alternating Page and Contents
    for i, lines in enumerate(pages or [[]]):
        page_obj_num = 3 + 2 * i
        content_obj_num = page_obj_num + 1
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_obj_num} 0 R "
            f"/Resources << /Font << /F1 {3 + 2 * n_pages} 0 R >> >> >>"
        ).encode("latin-1")
        objects.append(page_dict)

        stream = _make_page_stream(lines)
        content_dict = (
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
            + stream + b"\nendstream"
        )
        objects.append(content_dict)

    # Font (last object)
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode()
        out += obj
        out += b"\nendobj\n"

    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode()
    out += f"startxref\n{xref_pos}\n%%EOF\n".encode()
    return bytes(out)


def write_synthetic_pdf(out_path: Path, pages) -> Path:
    """Write a multi-page PDF to ``out_path`` and return it.

    ``pages`` may be a list of strings (one per page) or a list of lists
    of strings (multiple lines per page).
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Normalize: ``["a", "b"]`` → [["a"], ["b"]]
    if pages and isinstance(pages[0], str):
        pages = [[p] for p in pages]

    out_path.write_bytes(_make_pdf_bytes(pages))
    return out_path
