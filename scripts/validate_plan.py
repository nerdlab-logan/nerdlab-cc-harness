#!/usr/bin/env python3
"""validate_plan.py — plan.md ★ 섹션 (이번에 안 할 것 / 트레이드오프 / Phase 분해 / Context) 빈/placeholder 검증."""
from __future__ import annotations

import re
import sys
from pathlib import Path

SECTION_NOT_DOING: str = "이번에 안 할 것"
SECTION_TRADEOFF: str = "트레이드오프"
SECTION_PHASES: str = "Phase 분해"
SECTION_CONTEXT: str = "Context"
SECTION_EVALUATE: str = "## Evaluate ★"

_EMPTY_CODEBASE_LITERAL: str = "none (empty codebase)"
_EVALUATE_NONE_LITERAL: str = "none"

_PLACEHOLDER_WORDS = frozenset({"TBD", "없음", "-", ""})


def _slice_section(text: str, name: str) -> str | None:
    """섹션 이름으로 본문을 추출한다. 없으면 None.
    행 시작 앵커(`^`)로 본문 안 백틱 인용된 헤더(`` `## Foo` ``)를 무시한다."""
    pattern = (
        r"^##\s+(?:\d+\.\s+)?"
        + re.escape(name)
        + r"[^\n]*\n(.*?)(?=\n^##\s|\Z)"
    )
    m = re.search(pattern, text, re.DOTALL | re.MULTILINE)
    return m.group(1).strip() if m else None


def _is_separator_row(row: str) -> bool:
    """Markdown 표 구분자 행인지 판정 (|---|---| 형식, 연속 3개 이상 dash 필요)."""
    if re.search(r"[^\s\-|:]", row):
        return False
    return bool(re.search(r"---", row))


def _split_table_data_rows(body: str) -> list[str]:
    """표 본문에서 데이터 행만 추출한다 (헤더 + 구분자 제외)."""
    rows = [line.strip() for line in body.splitlines() if line.strip().startswith("|")]
    data_rows: list[str] = []
    past_sep = False
    for row in rows:
        if _is_separator_row(row):
            past_sep = True
        elif past_sep:
            data_rows.append(row)
    return data_rows


def _row_all_placeholder(row: str) -> bool:
    """표 데이터 행의 모든 열이 placeholder(-/TBD/빈값)인지 판정."""
    parts = row.split("|")
    data_cols = [c.strip() for c in parts[1:-1]]
    return all(c in _PLACEHOLDER_WORDS for c in data_cols)


def _is_section_3_empty(body: str) -> bool:
    """이번에 안 할 것 섹션이 비었는지 판정."""
    if not body:
        return True
    if body.strip() in _PLACEHOLDER_WORDS:
        return True
    items = re.findall(r"^\s*(?:[-*]|\d+\.)\s+(.*?)\s*$", body, re.MULTILINE)
    if not items:
        return True
    return all(item.strip() in _PLACEHOLDER_WORDS for item in items)


def _is_section_4_empty(body: str) -> bool:
    """트레이드오프 섹션이 비었는지 판정 (표 헤더만 / 모든 행이 placeholder)."""
    if not body:
        return True
    has_pipe = any(line.strip().startswith("|") for line in body.splitlines())
    if not has_pipe:
        return True
    data_rows = _split_table_data_rows(body)
    if not data_rows:
        return True
    return all(_row_all_placeholder(row) for row in data_rows)


def _is_section_context_empty(body: str) -> bool:
    """Context 섹션이 비었는지 판정. `none (empty codebase)` 한 줄은 합법(False).
    그 외는 본문에 영향 파일 / 관련 시그니처 / 기존 패턴 ★ 3개 헤더 또는 항목이
    하나라도 있어야 비지 않은 것으로 본다."""
    if not body:
        return True
    stripped = body.strip()
    if stripped == _EMPTY_CODEBASE_LITERAL:
        return False
    if stripped in _PLACEHOLDER_WORDS:
        return True
    has_star_header = bool(
        re.search(r"###\s+(?:영향 파일|관련 시그니처|기존 패턴)\s*★", body)
    )
    if has_star_header:
        return False
    items = re.findall(r"^\s*-\s*(.+?)\s*$", body, re.MULTILINE)
    real_items = [i for i in items if i.strip() not in _PLACEHOLDER_WORDS]
    return not real_items


def _is_section_10_empty(body: str) -> bool:
    """Phase 분해 섹션이 비었는지 판정 (표 헤더만 / 범위 칸이 모두 빈/TBD)."""
    if not body:
        return True
    has_pipe = any(line.strip().startswith("|") for line in body.splitlines())
    if not has_pipe:
        return True
    data_rows = _split_table_data_rows(body)
    if not data_rows:
        return True

    def _range_col_empty(row: str) -> bool:
        parts = row.split("|")
        # | 번호 | 이름 | 범위 한 줄 | 의존 | → parts[3] = 범위
        if len(parts) < 6:
            return True
        return parts[3].strip() in _PLACEHOLDER_WORDS

    return all(_range_col_empty(row) for row in data_rows)


def _is_section_evaluate_empty(body: str) -> bool:
    """Evaluate ★ 섹션 빈 판정. `none` 한 줄은 합법 (실행할 명령 없음 명시)."""
    if not body:
        return True
    stripped = body.strip()
    if stripped == _EVALUATE_NONE_LITERAL:
        return False
    if stripped in _PLACEHOLDER_WORDS:
        return True
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    return not lines


def validate_plan_stars(plan_path: str | Path) -> list[str]:
    """반환: 빈 ★ 섹션명 리스트. 검증 대상 5개 (이번에 안 할 것 / 트레이드오프
    / Phase 분해 / Context / Evaluate). 모두 채워졌으면 []."""
    text = Path(plan_path).read_text(encoding="utf-8")
    empty: list[str] = []

    body3 = _slice_section(text, SECTION_NOT_DOING)
    if body3 is None or _is_section_3_empty(body3):
        empty.append(SECTION_NOT_DOING)

    body4 = _slice_section(text, SECTION_TRADEOFF)
    if body4 is None or _is_section_4_empty(body4):
        empty.append(SECTION_TRADEOFF)

    body10 = _slice_section(text, SECTION_PHASES)
    if body10 is None or _is_section_10_empty(body10):
        empty.append(SECTION_PHASES)

    body_context = _slice_section(text, SECTION_CONTEXT)
    if body_context is None or _is_section_context_empty(body_context):
        empty.append(SECTION_CONTEXT)

    body_evaluate = _slice_section(text, "Evaluate")
    if body_evaluate is None or _is_section_evaluate_empty(body_evaluate):
        empty.append(SECTION_EVALUATE)

    return empty


def main(argv: list[str]) -> int:
    """CLI: validate_plan.py <plan_path>. 빈 섹션 발견 시 stdout 통지 + exit 0
    (진행 차단 X). plan 파일 없거나 읽기 실패 시 stderr + exit 2."""
    if len(argv) != 1:
        print("사용: validate_plan.py <plan_path>", file=sys.stderr)
        return 2

    plan_path = Path(argv[0])

    try:
        missing = validate_plan_stars(plan_path)
    except FileNotFoundError:
        print(f"오류: {plan_path} 파일을 찾을 수 없습니다.", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"오류: {plan_path} 읽기 실패 — {e}", file=sys.stderr)
        return 2

    if missing:
        print(f"빈 ★ 섹션: {', '.join(missing)}")
    else:
        print("★ 섹션 검증 통과")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
