"""Verify published.json contents."""
import json
from pathlib import Path

pub = json.loads(Path("data/processed/day-1/published.json").read_text(encoding="utf-8"))
lesson = pub["lesson"]

print("=== PUBLISHED.JSON VERIFICATION ===")
print(f"Schema version: {pub.get('schema_version')}")
print(f"Validation status: {pub.get('validation_status')}")
print(f"Source SHA256: {pub.get('source_sha256')}")
print(f"Documentizer version: {pub.get('documentizer_version')}")
print(f"Generated at: {pub.get('created_at')}")
print()
print(f"Title: {lesson.get('title')}")
print(f"Language: {lesson.get('language')}")
print(f"Summary (first 200 chars): {lesson.get('summary', '')[:200]}")
print()
print(f"Sections: {len(lesson.get('sections', []))}")
print(f"Concepts: {len(lesson.get('concepts', []))}")
print(f"Chunks: {len(lesson.get('chunks', []))}")

print()
print("=== CONCEPTS SAMPLE ===")
for i, con in enumerate(lesson.get("concepts", [])[:5]):
    print(f"  {i+1}. {con.get('name')} [{con.get('kind')}] - pages {con.get('source_pages')}")

print()
print("=== TEACH-BACK SAMPLE (first 3 chunks) ===")
chunks = lesson.get("chunks", [])
for i, chunk in enumerate(chunks[:3]):
    tback = chunk.get("teach_back", {})
    print(f"Chunk {i+1}: {chunk.get('title', '(no title)')[:80]}")
    print(f"  page_start={chunk.get('page_start')}, page_end={chunk.get('page_end')}")
    mu = tback.get("must_understand", [])
    print(f"  must_understand (count={len(mu)}): {mu[:2]}")
    ae = tback.get("acceptable_explanation", "")
    print(f"  acceptable_explanation: {ae[:100]}")
    cm = tback.get("common_misconception")
    ct = tback.get("clarification_trigger")
    print(f"  common_misconception: {repr(cm)[:80]}")
    print(f"  clarification_trigger: {repr(ct)[:80]}")
    print()

print("=== SOURCE PAGES VALIDATION ===")
all_pages = []
for sec in lesson.get("sections", []):
    for blk in sec.get("blocks", []):
        all_pages.extend(blk.get("source_pages", []))
for con in lesson.get("concepts", []):
    all_pages.extend(con.get("source_pages", []))
for chunk in chunks:
    for kp in chunk.get("key_points", []):
        all_pages.extend(kp.get("source_pages", []))
    for ex in chunk.get("examples", []):
        all_pages.extend(ex.get("source_pages", []))

if all_pages:
    max_page = max(all_pages)
    min_page = min(all_pages)
    all_valid = all(1 <= p <= 32 for p in all_pages)
    print(f"Page range: {min_page} - {max_page}")
    print(f"All within 1-32: {all_valid} ({len(all_pages)} total refs)")
else:
    print("WARNING: No source_pages found!")

print()
print("=== VALIDATION JSON SUMMARY ===")
val_path = Path("data/processed/day-1/validation.json")
if val_path.exists():
    val = json.loads(val_path.read_text(encoding="utf-8"))
    print(f"Status: {val.get('status')}")
    print(f"Grounding score: {val.get('grounding_score', 'N/A')}")
    print(f"Schema OK: {val.get('schema_ok')}")
    print(f"Total issues: {len(val.get('issues', []))}")
    for issue in val.get("issues", [])[:5]:
        print(f"  [{issue.get('severity')}] {issue.get('code')}: {issue.get('detail', '')[:80]}")
