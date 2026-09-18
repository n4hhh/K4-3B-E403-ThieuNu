"""Tests for the Phase 3A.5 CLI (``python -m app.cli_documentize``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.cli_documentize import (
    cmd_phase3a,
    cmd_phase3a5,
    cmd_all,
    build_parser,
)
from app.services.phase3a_pipeline import Phase3APipeline


def test_parser_has_subcommands():
    p = build_parser()
    args = p.parse_args(["phase3a"])
    assert args.command == "phase3a"
    args = p.parse_args(
        ["phase3a5", "--document", "demo", "--provider", "mock"]
    )
    assert args.document == "demo"
    assert args.provider == "mock"


def test_cli_phase3a_runs(tmp_path: Path, monkeypatch):
    from app import config as config_module
    from app.services import raw_document_service
    from app.services import pdf_reader
    from app.services import phase3a_pipeline
    from app.repositories import published_lesson_repository as pub_mod
    from app.routers import documentizer as doc_router_module
    from tests._make_pdf import write_synthetic_pdf

    lesson_dir = tmp_path / "lesson"
    processed_dir = tmp_path / "processed"
    lesson_dir.mkdir()
    write_synthetic_pdf(lesson_dir / "demo.pdf", [["L1", "topic"], ["L2", "topic"]])

    monkeypatch.setattr(config_module, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(config_module, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(raw_document_service, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(raw_document_service, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(pub_mod, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(pub_mod, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(pdf_reader, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(phase3a_pipeline, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(phase3a_pipeline, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(doc_router_module, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(doc_router_module, "LESSON_DIR", lesson_dir)

    rc = cmd_phase3a(
        type("Args", (), {
            "lesson_dir": str(lesson_dir),
            "processed_dir": str(processed_dir),
        })()
    )
    assert rc == 0


def test_cli_phase3a5_publishes(tmp_path: Path, monkeypatch):
    from app import config as config_module
    from app.services import raw_document_service
    from app.services import pdf_reader
    from app.services import phase3a_pipeline
    from app.repositories import published_lesson_repository as pub_mod
    from app.routers import documentizer as doc_router_module
    from tests._make_pdf import write_synthetic_pdf

    lesson_dir = tmp_path / "lesson"
    processed_dir = tmp_path / "processed"
    lesson_dir.mkdir()
    write_synthetic_pdf(
        lesson_dir / "demo.pdf",
        [
            ["REST", "REST is an architectural style"],
            ["Methods", "GET retrieves a resource"],
        ],
    )
    monkeypatch.setattr(config_module, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(config_module, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(raw_document_service, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(raw_document_service, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(pub_mod, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(pub_mod, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(pdf_reader, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(phase3a_pipeline, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(phase3a_pipeline, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(doc_router_module, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(doc_router_module, "LESSON_DIR", lesson_dir)

    Phase3APipeline().run()

    args = type("Args", (), {
        "document": "demo",
        "provider": "mock",
        "max_attempts": 2,
        "language": "auto",
        "with_page_images": False,
        "no_publish": False,
        "lesson_dir": str(lesson_dir),
        "processed_dir": str(processed_dir),
    })()

    rc = cmd_phase3a5(args)
    assert rc == 0
    assert (processed_dir / "demo" / "published.json").exists()


def test_cli_phase3a5_requires_document():
    args = type("Args", (), {
        "document": None,
        "provider": "mock",
        "max_attempts": 3,
        "language": "auto",
        "with_page_images": False,
        "no_publish": False,
        "lesson_dir": None,
        "processed_dir": None,
    })()
    rc = cmd_phase3a5(args)
    assert rc == 2  # missing argument


def test_cli_phase3a5_no_publish(tmp_path: Path, monkeypatch):
    from app import config as config_module
    from app.services import raw_document_service
    from app.services import pdf_reader
    from app.services import phase3a_pipeline
    from app.repositories import published_lesson_repository as pub_mod
    from app.routers import documentizer as doc_router_module
    from tests._make_pdf import write_synthetic_pdf

    lesson_dir = tmp_path / "lesson"
    processed_dir = tmp_path / "processed"
    lesson_dir.mkdir()
    write_synthetic_pdf(
        lesson_dir / "demo.pdf",
        [
            ["REST", "REST is an architectural style"],
            ["Methods", "GET retrieves a resource"],
        ],
    )
    monkeypatch.setattr(config_module, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(config_module, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(raw_document_service, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(raw_document_service, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(pub_mod, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(pub_mod, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(pdf_reader, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(phase3a_pipeline, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(phase3a_pipeline, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(doc_router_module, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(doc_router_module, "LESSON_DIR", lesson_dir)

    Phase3APipeline().run()

    args = type("Args", (), {
        "document": "demo",
        "provider": "mock",
        "max_attempts": 2,
        "language": "auto",
        "with_page_images": False,
        "no_publish": True,
        "lesson_dir": str(lesson_dir),
        "processed_dir": str(processed_dir),
    })()

    rc = cmd_phase3a5(args)
    assert rc == 0
    assert not (processed_dir / "demo" / "published.json").exists()