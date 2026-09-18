"""Run the Teach-Back golden set and report the quality bar.

    python -m eval.run_eval                    # full set, live model
    python -m eval.run_eval --provider mock    # offline smoke run
    python -m eval.run_eval --case G05 G07     # a subset while tuning
    python -m eval.run_eval --json report.json # machine-readable output

What is measured
----------------

``verdict``      Did the agent accept / ask back as it should? This is the
                 headline number, because getting it wrong in either
                 direction breaks the exercise: a false pass teaches
                 nothing, a false gap makes the agent look broken.

``gap_type``     For cases where the *kind* of gap matters — the agent
                 must not answer a contradiction with a "you forgot to
                 mention…" question.

``no-leak``      Did the ask-back avoid stating the missing point? Checked
                 both with the leak heuristic and with per-case forbidden
                 substrings.

``grounded``     Share of transcript-lesson verdicts that cite a real
                 passage code.

Quality bar (fixed at spec freeze, see SPEC.md §7):

    verdict ≥ 85%, no-leak = 100%, and no case where a wrong explanation
    is accepted (false pass).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow `python eval/run_eval.py` as well as `python -m eval.run_eval`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.models.lesson import Lesson, LessonChunk  # noqa: E402
from app.repositories.lesson_repository import LessonRepository  # noqa: E402
from app.services.ai.chat_provider import build_chat_provider_safe  # noqa: E402
from app.services.ai_validator_service import (  # noqa: E402
    AIValidatorService,
    leaks_answer,
)
from app.services.lesson_prep_service import LessonPrepService  # noqa: E402
from app.services.transcript_lesson_service import (  # noqa: E402
    TranscriptLessonService,
)

GOLDEN_SET = Path(__file__).resolve().parent / "golden_set.json"

# Placeholder in the golden set meaning "use this chunk's own source text",
# so pasted-source cases work without copying the data pack into the repo.
CHUNK_CONTENT_MARKER = "__CHUNK_CONTENT__"


@dataclass
class CaseResult:
    case_id: str
    layer: str
    hard_test: str
    lesson_id: str
    chunk_title: str
    expected: str
    actual: str
    verdict_ok: bool
    gap_type_expected: Optional[str]
    gap_type_actual: str
    gap_type_ok: Optional[bool]
    leaked: bool
    grounded: bool
    evaluator: str
    ask_back: str
    latency_s: float
    notes: List[str] = field(default_factory=list)

    @property
    def false_pass(self) -> bool:
        """Accepted an explanation that should have been questioned."""
        return self.expected == "gap" and self.actual == "pass"


def build_catalogue() -> Dict[str, Lesson]:
    repository = LessonRepository(
        json_fallback=settings.json_fallback_file,
        transcript_service=TranscriptLessonService(
            transcript_dir=settings.transcript_dir,
            max_chunks=settings.teach_back_max_chunks,
        ),
    )
    lessons = {lesson.id: lesson for lesson in repository.list_lessons()}

    # The demo lesson lives in the JSON fallback, which the repository only
    # reads when nothing else produced a lesson. Load it explicitly so the
    # golden set can mix both sources.
    if "rest-api-http-methods" not in lessons:
        json_only = LessonRepository(lessons_file=settings.json_fallback_file)
        for lesson in json_only.list_lessons():
            lessons.setdefault(lesson.id, lesson)
    return lessons


def resolve_chunk(lesson: Lesson, case: Dict[str, Any]) -> Optional[LessonChunk]:
    chunk_id = case.get("chunk_id")
    if chunk_id:
        return next((c for c in lesson.chunks if c.id == chunk_id), None)
    index = case.get("chunk_index")
    if index is None or index >= len(lesson.chunks):
        return None
    return lesson.chunks[index]


def run_case(
    case: Dict[str, Any],
    lessons: Dict[str, Lesson],
    validator: AIValidatorService,
    prep: LessonPrepService,
) -> Optional[CaseResult]:
    lesson = lessons.get(case["lesson_id"])
    if lesson is None:
        print(f"  ! bỏ qua {case['id']}: không có bài '{case['lesson_id']}'")
        return None

    chunk = resolve_chunk(lesson, case)
    if chunk is None:
        print(f"  ! bỏ qua {case['id']}: không tìm được chunk")
        return None

    prep.ensure_chunk(lesson, chunk)

    explanation = case["explanation"]
    if explanation == CHUNK_CONTENT_MARKER:
        explanation = chunk.content

    started = time.time()
    result = validator.validate(
        chunk,
        explanation,
        attempt=1,
        lesson_title=lesson.title,
    )
    latency = time.time() - started

    actual = "pass" if result.passed else "gap"
    expected = case["expect"]["verdict"]
    expected_gap = case["expect"].get("gap_type")

    notes: List[str] = []
    leaked = False
    if not result.passed and result.ask_back:
        if leaks_answer(result.ask_back, chunk.key_points):
            leaked = True
            notes.append("ask_back lặp lại nội dung key point")
        for forbidden in case.get("must_not_appear", []):
            if forbidden.lower() in result.ask_back.lower():
                leaked = True
                notes.append(f"ask_back chứa '{forbidden}'")

    return CaseResult(
        case_id=case["id"],
        layer=case.get("layer", ""),
        hard_test=case.get("hard_test", ""),
        lesson_id=lesson.id,
        chunk_title=chunk.title,
        expected=expected,
        actual=actual,
        verdict_ok=actual == expected,
        gap_type_expected=expected_gap,
        gap_type_actual=result.gap_type.value,
        gap_type_ok=(
            None if expected_gap is None else result.gap_type.value == expected_gap
        ),
        leaked=leaked,
        grounded=bool(result.citations),
        evaluator=result.evaluator,
        ask_back=result.ask_back,
        latency_s=latency,
        notes=notes,
    )


def percentage(part: int, whole: int) -> float:
    return 100.0 * part / whole if whole else 0.0


def report(results: List[CaseResult]) -> Dict[str, Any]:
    total = len(results)
    verdict_ok = sum(1 for r in results if r.verdict_ok)
    gap_typed = [r for r in results if r.gap_type_ok is not None]
    gap_ok = sum(1 for r in gap_typed if r.gap_type_ok)
    asked_back = [r for r in results if r.actual == "gap"]
    no_leak = sum(1 for r in asked_back if not r.leaked)
    transcript_cases = [r for r in results if r.lesson_id.startswith("transcript-")]
    grounded = sum(1 for r in transcript_cases if r.grounded)
    false_passes = [r for r in results if r.false_pass]
    ai_graded = sum(1 for r in results if r.evaluator == "ai")

    print("\n" + "=" * 78)
    print(f"{'CASE':<32}{'EXPECT':<8}{'GOT':<8}{'GAP TYPE':<16}{'':<4}")
    print("-" * 78)
    for r in results:
        flag = "OK " if r.verdict_ok else "SAI"
        if r.leaked:
            flag = "LỘ!"
        gap_cell = r.gap_type_actual
        if r.gap_type_expected and not r.gap_type_ok:
            gap_cell = f"{r.gap_type_actual}≠{r.gap_type_expected}"
        print(f"{r.case_id:<32}{r.expected:<8}{r.actual:<8}{gap_cell:<16}{flag}")

    print("=" * 78)
    print(f"Verdict đúng      {verdict_ok}/{total}  ({percentage(verdict_ok, total):.0f}%)")
    if gap_typed:
        print(
            f"Gap type đúng     {gap_ok}/{len(gap_typed)}  "
            f"({percentage(gap_ok, len(gap_typed)):.0f}%)"
        )
    if asked_back:
        print(
            f"Không lộ đáp án   {no_leak}/{len(asked_back)}  "
            f"({percentage(no_leak, len(asked_back)):.0f}%)"
        )
    if transcript_cases:
        print(
            f"Có trích nguồn    {grounded}/{len(transcript_cases)}  "
            f"({percentage(grounded, len(transcript_cases)):.0f}%)"
        )
    print(f"Chấm bằng AI      {ai_graded}/{total}")
    print(f"False pass        {len(false_passes)}  " + (
        "(" + ", ".join(r.case_id for r in false_passes) + ")" if false_passes else ""
    ))

    bar_passed = (
        percentage(verdict_ok, total) >= 85.0
        and (not asked_back or no_leak == len(asked_back))
        and not false_passes
    )
    print(
        "\nQuality bar (≥85% verdict · 100% không lộ đáp án · 0 false pass): "
        + ("ĐẠT" if bar_passed else "CHƯA ĐẠT")
    )

    for r in results:
        if r.notes:
            print(f"  · {r.case_id}: {'; '.join(r.notes)}")

    return {
        "total": total,
        "verdict_accuracy": percentage(verdict_ok, total),
        "gap_type_accuracy": percentage(gap_ok, len(gap_typed)) if gap_typed else None,
        "no_leak_rate": percentage(no_leak, len(asked_back)) if asked_back else None,
        "grounded_rate": (
            percentage(grounded, len(transcript_cases)) if transcript_cases else None
        ),
        "false_passes": [r.case_id for r in false_passes],
        "quality_bar_passed": bar_passed,
        "cases": [
            {
                "id": r.case_id,
                "layer": r.layer,
                "hard_test": r.hard_test,
                "lesson_id": r.lesson_id,
                "chunk": r.chunk_title,
                "expected": r.expected,
                "actual": r.actual,
                "gap_type_expected": r.gap_type_expected,
                "gap_type_actual": r.gap_type_actual,
                "leaked": r.leaked,
                "grounded": r.grounded,
                "evaluator": r.evaluator,
                "ask_back": r.ask_back,
                "latency_s": round(r.latency_s, 2),
                "notes": r.notes,
            }
            for r in results
        ],
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m eval.run_eval",
        description="Run the Teach-Back golden set.",
    )
    parser.add_argument("--provider", default=None, help="Override TEACH_BACK_PROVIDER")
    parser.add_argument("--case", nargs="*", help="Run only cases whose id starts with")
    parser.add_argument("--json", dest="json_out", help="Write the report to this file")
    args = parser.parse_args(argv)

    payload = json.loads(GOLDEN_SET.read_text(encoding="utf-8"))
    cases = payload["cases"]
    if args.case:
        prefixes = tuple(args.case)
        cases = [c for c in cases if c["id"].startswith(prefixes)]
        if not cases:
            print("Không có case nào khớp.")
            return 1

    provider = build_chat_provider_safe(args.provider or settings.teach_back_provider)
    ai_enabled = getattr(provider, "name", "mock") != "mock"
    print(
        f"Provider: {getattr(provider, 'name', '?')} "
        f"(model={getattr(provider, 'model', '?')}, ai={ai_enabled})"
    )
    if not ai_enabled:
        print("CẢNH BÁO: đang chạy offline — kết quả chỉ để smoke test.")

    lessons = build_catalogue()
    prep = LessonPrepService(
        provider=provider, cache_dir=settings.cache_dir, enabled=ai_enabled
    )
    validator = AIValidatorService(
        provider=provider,
        max_attempts=settings.teach_back_max_attempts,
        enabled=ai_enabled,
    )

    results: List[CaseResult] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']} …", flush=True)
        result = run_case(case, lessons, validator, prep)
        if result is not None:
            results.append(result)

    if not results:
        print("Không chạy được case nào.")
        return 1

    summary = report(results)

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nĐã ghi báo cáo vào {args.json_out}")

    return 0 if summary["quality_bar_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
