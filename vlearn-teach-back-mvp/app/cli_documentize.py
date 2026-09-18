"""Phase 3A.5 CLI — end-to-end development entry point.

Usage (from the ``vlearn-teach-back-mvp`` directory):

    python -m app.cli_documentize phase3a              # run Phase 3A only
    python -m app.cli_documentize phase3a5 --document sample
    python -m app.cli_documentize all --document sample
    python -m app.cli_documentize phase3a5 --document sample --provider mock
    python -m app.cli_documentize phase3a5 --document sample --no-publish

This is the developer command requested in the Phase 3A.5 spec. It
chains the Phase 3A PDF to RawDocument pipeline with the Phase 3A.5
RawDocument to published.json pipeline.

The CLI never reads ``GEMINI_API_KEY`` directly — it goes through the
``GeminiProvider``, which reads the env at construction.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Optional, Sequence

from app.config import LESSON_DIR, PROCESSED_DIR
from app.repositories.published_lesson_repository import (
    PublishedLessonRepository,
)
from app.services.ai import build_provider
from app.services.documentizer_pipeline import (
    DocumentizerFailedError,
    DocumentizerPipeline,
    DocumentizerPipelineConfig,
)
from app.services.phase3a_pipeline import Phase3APipeline


logger = logging.getLogger("vlearn.cli")


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------


def cmd_phase3a(args: argparse.Namespace) -> int:
    pipeline = Phase3APipeline(
        lesson_dir=_resolve_lesson_dir(args),
        processed_dir=_resolve_processed_dir(args),
    )
    results = pipeline.run()
    print(f"Phase 3A: discovered {len(results)} document(s).")
    for r in results:
        if r.raw_document:
            print(
                f"  OK: {r.source_file} -> {r.document_id} "
                f"({r.page_count} pages, {r.total_words} words)"
            )
        else:
            print(f"  FAIL: {r.source_file} -> error: {r.error}")
    return 0


def cmd_phase3a5(args: argparse.Namespace) -> int:
    if not args.document:
        print("ERROR: --document is required for phase3a5", file=sys.stderr)
        return 2

    try:
        provider = build_provider(args.provider)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: provider unavailable: {exc}", file=sys.stderr)
        return 3

    config = DocumentizerPipelineConfig(
        max_attempts=args.max_attempts,
        language=args.language,
        emit_page_images=args.with_page_images,
    )
    pipeline = DocumentizerPipeline(
        provider=provider,
        config=config,
    )
    pipeline._published_repo._processed_dir = _resolve_processed_dir(args)
    pipeline._published_repo._lesson_dir = _resolve_lesson_dir(args)
    pipeline._raw_service._processed_dir = _resolve_processed_dir(args)
    pipeline._raw_service._lesson_dir = _resolve_lesson_dir(args)

    try:
        result = pipeline.process(args.document, publish=not args.no_publish)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4
    except DocumentizerFailedError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        if exc.report is not None:
            print(json.dumps(exc.report.model_dump(mode="json"), indent=2))
        return 5

    print(
        f"Phase 3A.5: status={result.validation.status.value} "
        f"grounding={result.validation.grounding_score:.3f} "
        f"attempts={result.attempts}"
    )
    print(
        f"  chunks={len(result.lesson.chunks)} "
        f"concepts={len(result.lesson.concepts)}"
    )
    if result.published_path:
        print(f"  published.json: {result.published_path}")
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    rc = cmd_phase3a(args)
    if rc != 0:
        return rc
    return cmd_phase3a5(args)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_lesson_dir(args: argparse.Namespace):
    from pathlib import Path

    if args.lesson_dir:
        return Path(args.lesson_dir)
    return LESSON_DIR


def _resolve_processed_dir(args: argparse.Namespace):
    from pathlib import Path

    if args.processed_dir:
        return Path(args.processed_dir)
    return PROCESSED_DIR


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m app.cli_documentize",
        description="VLearn Teach-Back MVP — Phase 3A / 3A.5 CLI",
    )
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--lesson-dir", default=None)
    common.add_argument("--processed-dir", default=None)

    p3a = sub.add_parser(
        "phase3a", parents=[common], help="Run Phase 3A only (PDF to RawDocument)"
    )
    p3a.set_defaults(func=cmd_phase3a)

    p3a5 = sub.add_parser(
        "phase3a5",
        parents=[common],
        help="Run Phase 3A.5 (RawDocument to published.json)",
    )
    p3a5.add_argument("--document", required=True, help="Document id (RawDocument id)")
    p3a5.add_argument(
        "--provider",
        default=None,
        help="Provider override (gemini | mock); defaults to AI_PROVIDER env var",
    )
    p3a5.add_argument("--max-attempts", type=int, default=3)
    p3a5.add_argument("--language", default="auto")
    p3a5.add_argument(
        "--with-page-images", action="store_true", help="Render page images"
    )
    p3a5.add_argument(
        "--no-publish",
        action="store_true",
        help="Do everything except write published.json",
    )
    p3a5.set_defaults(func=cmd_phase3a5)

    pall = sub.add_parser(
        "all", parents=[common], help="Run Phase 3A then Phase 3A.5 for one document"
    )
    pall.add_argument("--document", required=True)
    pall.add_argument("--provider", default=None)
    pall.add_argument("--max-attempts", type=int, default=3)
    pall.add_argument("--language", default="auto")
    pall.add_argument("--with-page-images", action="store_true")
    pall.add_argument("--no-publish", action="store_true")
    pall.set_defaults(func=cmd_all)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())