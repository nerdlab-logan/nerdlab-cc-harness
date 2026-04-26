"""Unit tests for scripts/validate_plan.py — ★ 섹션 빈/placeholder 검증."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_plan import (  # noqa: E402
    SECTION_CONTEXT,
    SECTION_EVALUATE,
    SECTION_NOT_DOING,
    SECTION_PHASES,
    SECTION_TRADEOFF,
    _is_section_3_empty,
    _is_section_4_empty,
    _is_section_10_empty,
    _is_section_context_empty,
    _is_section_evaluate_empty,
    main,
    validate_plan_stars,
)

# ---------------------------------------------------------------------------
# 픽스처 헬퍼
# ---------------------------------------------------------------------------

_FILLED_S3 = "- Context Gather 본구현\n- prompts 변경"
_FILLED_S4 = (
    "| 결정 | 이유 | 포기한 것 |\n"
    "|------|------|-----------|\n"
    "| 별도 모듈 | 책임 분리 | 공유 상수 |"
)
_FILLED_S10 = (
    "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
    "|------|------|-----------|------|\n"
    "| 1 | setup | 헬퍼 신규 작성 | — |"
)
_FILLED_S11 = (
    "### 영향 파일 ★\n"
    "- scripts/validate_plan.py — 헬퍼 추가\n\n"
    "### 관련 시그니처 ★\n"
    "- scripts/validate_plan.py:96 `def validate_plan_stars(plan_path: Path) -> list[str]` — 4-섹션 확장\n\n"
    "### 기존 패턴 ★\n"
    "- 섹션 빈 판정 패턴 — _is_section_3_empty 참조"
)
_FILLED_S12 = "none"


def _make_plan(
    s3: str = _FILLED_S3,
    s4: str = _FILLED_S4,
    s10: str = _FILLED_S10,
    s11: str = _FILLED_S11,
    s12: str = _FILLED_S12,
) -> str:
    return (
        "# test-plan\n\n"
        "## 1. 목표\n\n테스트 목표\n\n"
        f"## 3. 이번에 안 할 것 ★\n\n{s3}\n\n"
        f"## 4. 트레이드오프 ★\n\n{s4}\n\n"
        "## 5. TDD\n\nno\n\n"
        f"## 10. Phase 분해 ★\n\n{s10}\n\n"
        f"## 11. Context ★\n\n{s11}\n\n"
        f"## Evaluate ★\n\n{s12}\n"
    )


def _write_tmp(text: str) -> Path:
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    )
    f.write(text)
    f.close()
    return Path(f.name)


# ---------------------------------------------------------------------------
# _is_section_3_empty
# ---------------------------------------------------------------------------


class TestIsSection3Empty(unittest.TestCase):

    def test_real_items_not_empty(self):
        self.assertFalse(_is_section_3_empty("- 항목 A\n- 항목 B"))

    def test_empty_string_is_empty(self):
        self.assertTrue(_is_section_3_empty(""))

    def test_tbd_bare_is_empty(self):
        self.assertTrue(_is_section_3_empty("TBD"))

    def test_없음_bare_is_empty(self):
        self.assertTrue(_is_section_3_empty("없음"))

    def test_single_dash_bare_is_empty(self):
        self.assertTrue(_is_section_3_empty("-"))

    def test_bullet_tbd_is_empty(self):
        self.assertTrue(_is_section_3_empty("- TBD"))

    def test_bullet_없음_is_empty(self):
        self.assertTrue(_is_section_3_empty("- 없음"))

    def test_no_bullet_lines_is_empty(self):
        self.assertTrue(_is_section_3_empty("그냥 텍스트만"))

    def test_numbered_list_not_empty(self):
        self.assertFalse(_is_section_3_empty("1. 항목 A\n2. 항목 B"))

    def test_numbered_list_placeholder_is_empty(self):
        self.assertTrue(_is_section_3_empty("1. TBD\n2. 없음"))

    def test_asterisk_bullet_not_empty(self):
        self.assertFalse(_is_section_3_empty("* 항목 A\n* 항목 B"))

    def test_mixed_real_and_placeholder_not_empty(self):
        self.assertFalse(_is_section_3_empty("- 실제 항목\n- TBD"))


# ---------------------------------------------------------------------------
# _is_section_4_empty
# ---------------------------------------------------------------------------


class TestIsSection4Empty(unittest.TestCase):

    def test_filled_table_not_empty(self):
        body = "| 결정 | 이유 | 포기 |\n|------|------|------|\n| A | B | C |"
        self.assertFalse(_is_section_4_empty(body))

    def test_empty_string_is_empty(self):
        self.assertTrue(_is_section_4_empty(""))

    def test_header_only_is_empty(self):
        body = "| 결정 | 이유 | 포기 |\n|------|------|------|"
        self.assertTrue(_is_section_4_empty(body))

    def test_all_dash_data_row_is_empty(self):
        body = "| 결정 | 이유 | 포기 |\n|------|------|------|\n| - | - | - |"
        self.assertTrue(_is_section_4_empty(body))

    def test_no_table_at_all_is_empty(self):
        self.assertTrue(_is_section_4_empty("텍스트만 있음"))

    def test_partial_placeholder_not_empty(self):
        body = "| 결정 | 이유 | 포기 |\n|------|------|------|\n| 실제결정 | - | - |"
        self.assertFalse(_is_section_4_empty(body))

    def test_tbd_all_columns_is_empty(self):
        body = "| 결정 | 이유 | 포기 |\n|------|------|------|\n| TBD | TBD | TBD |"
        self.assertTrue(_is_section_4_empty(body))


# ---------------------------------------------------------------------------
# _is_section_10_empty
# ---------------------------------------------------------------------------


class TestIsSection10Empty(unittest.TestCase):

    def test_filled_table_not_empty(self):
        body = (
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|-----------|------|\n"
            "| 1 | phase | 뭔가 한다 | — |"
        )
        self.assertFalse(_is_section_10_empty(body))

    def test_empty_string_is_empty(self):
        self.assertTrue(_is_section_10_empty(""))

    def test_header_only_is_empty(self):
        body = "| 번호 | 이름 | 범위 한 줄 | 의존 |\n|------|------|-----------|------|"
        self.assertTrue(_is_section_10_empty(body))

    def test_tbd_range_col_is_empty(self):
        body = (
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|-----------|------|\n"
            "| 1 | phase | TBD | — |"
        )
        self.assertTrue(_is_section_10_empty(body))

    def test_blank_range_col_is_empty(self):
        body = (
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|-----------|------|\n"
            "| 1 | phase |  | — |"
        )
        self.assertTrue(_is_section_10_empty(body))

    def test_no_table_is_empty(self):
        self.assertTrue(_is_section_10_empty("텍스트만"))

    def test_multiple_rows_one_real_not_empty(self):
        body = (
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|-----------|------|\n"
            "| 1 | phase | TBD | — |\n"
            "| 2 | phase2 | 실제 범위 설명 | 1 |"
        )
        self.assertFalse(_is_section_10_empty(body))


# ---------------------------------------------------------------------------
# _is_section_context_empty
# ---------------------------------------------------------------------------


class TestIsSectionContextEmpty(unittest.TestCase):

    def test_filled_three_headers_not_empty(self):
        body = (
            "### 영향 파일 ★\n- foo.py — 수정\n\n"
            "### 관련 시그니처 ★\n- foo:10 `def bar()` — 설명\n\n"
            "### 기존 패턴 ★\n- 패턴명 — 설명"
        )
        self.assertFalse(_is_section_context_empty(body))

    def test_empty_codebase_literal_not_empty(self):
        self.assertFalse(_is_section_context_empty("none (empty codebase)"))

    def test_empty_codebase_literal_with_whitespace_not_empty(self):
        self.assertFalse(_is_section_context_empty("  none (empty codebase)  "))

    def test_empty_string_is_empty(self):
        self.assertTrue(_is_section_context_empty(""))

    def test_tbd_is_empty(self):
        self.assertTrue(_is_section_context_empty("TBD"))

    def test_없음_is_empty(self):
        self.assertTrue(_is_section_context_empty("없음"))

    def test_no_headers_no_real_items_is_empty(self):
        self.assertTrue(_is_section_context_empty("텍스트만 있음"))

    def test_single_star_header_present_not_empty(self):
        self.assertFalse(_is_section_context_empty("### 영향 파일 ★\n- foo.py — bar"))

    def test_관련_시그니처_header_not_empty(self):
        self.assertFalse(_is_section_context_empty("### 관련 시그니처 ★\n- foo:1 `def x()` — y"))

    def test_기존_패턴_header_not_empty(self):
        self.assertFalse(_is_section_context_empty("### 기존 패턴 ★\n- 패턴 — 설명"))

    def test_real_bullet_items_without_header_not_empty(self):
        self.assertFalse(_is_section_context_empty("- foo.py — 관련 파일\n- bar.py — 다른 파일"))

    def test_placeholder_bullets_only_is_empty(self):
        self.assertTrue(_is_section_context_empty("- TBD\n- -"))


# ---------------------------------------------------------------------------
# _is_section_evaluate_empty
# ---------------------------------------------------------------------------


class TestIsSectionEvaluateEmpty(unittest.TestCase):

    def test_empty_string_is_empty(self):
        self.assertTrue(_is_section_evaluate_empty(""))

    def test_none_literal_not_empty(self):
        self.assertFalse(_is_section_evaluate_empty("none"))

    def test_none_with_whitespace_not_empty(self):
        self.assertFalse(_is_section_evaluate_empty("  none  "))

    def test_single_command_not_empty(self):
        self.assertFalse(_is_section_evaluate_empty("python -m pytest"))

    def test_multiple_commands_not_empty(self):
        self.assertFalse(_is_section_evaluate_empty("python -m mypy .\npython -m pytest"))

    def test_tbd_is_empty(self):
        self.assertTrue(_is_section_evaluate_empty("TBD"))

    def test_없음_is_empty(self):
        self.assertTrue(_is_section_evaluate_empty("없음"))

    def test_dash_is_empty(self):
        self.assertTrue(_is_section_evaluate_empty("-"))


# ---------------------------------------------------------------------------
# validate_plan_stars (통합)
# ---------------------------------------------------------------------------


class TestValidatePlanStars(unittest.TestCase):

    def setUp(self) -> None:
        self._paths: list[Path] = []

    def tearDown(self) -> None:
        for p in self._paths:
            try:
                p.unlink()
            except FileNotFoundError:
                pass

    def _write(self, text: str) -> Path:
        p = _write_tmp(text)
        self._paths.append(p)
        return p

    def test_all_filled_returns_empty_list(self):
        p = self._write(_make_plan())
        self.assertEqual(validate_plan_stars(p), [])

    def test_section3_empty_detected(self):
        p = self._write(_make_plan(s3=""))
        result = validate_plan_stars(p)
        self.assertIn(SECTION_NOT_DOING, result)
        self.assertNotIn(SECTION_TRADEOFF, result)
        self.assertNotIn(SECTION_PHASES, result)

    def test_section4_header_only_detected(self):
        s4 = "| 결정 | 이유 | 포기 |\n|------|------|------|"
        p = self._write(_make_plan(s4=s4))
        result = validate_plan_stars(p)
        self.assertIn(SECTION_TRADEOFF, result)
        self.assertNotIn(SECTION_NOT_DOING, result)
        self.assertNotIn(SECTION_PHASES, result)

    def test_section10_tbd_range_detected(self):
        s10 = (
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|-----------|------|\n"
            "| 1 | p | TBD | — |"
        )
        p = self._write(_make_plan(s10=s10))
        result = validate_plan_stars(p)
        self.assertIn(SECTION_PHASES, result)
        self.assertNotIn(SECTION_NOT_DOING, result)
        self.assertNotIn(SECTION_TRADEOFF, result)

    def test_all_sections_empty_returns_all_five(self):
        s4_empty = "| 결정 | 이유 | 포기 |\n|------|------|------|"
        s10_empty = "| 번호 | 이름 | 범위 한 줄 | 의존 |\n|------|------|-----------|------|"
        p = self._write(_make_plan(s3="TBD", s4=s4_empty, s10=s10_empty, s11="TBD", s12="TBD"))
        result = validate_plan_stars(p)
        self.assertEqual(
            sorted(result),
            sorted([SECTION_NOT_DOING, SECTION_TRADEOFF, SECTION_PHASES, SECTION_CONTEXT, SECTION_EVALUATE]),
        )

    def test_missing_section_counts_as_empty(self):
        text = (
            "# test\n\n"
            "## 3. 이번에 안 할 것 ★\n\n- 항목\n\n"
            "## 4. 트레이드오프 ★\n\n"
            "| a | b | c |\n|---|---|---|\n| x | y | z |\n"
        )
        p = self._write(text)
        result = validate_plan_stars(p)
        self.assertIn(SECTION_PHASES, result)

    def test_context_filled_not_detected(self):
        p = self._write(_make_plan())
        result = validate_plan_stars(p)
        self.assertNotIn(SECTION_CONTEXT, result)

    def test_context_tbd_detected(self):
        p = self._write(_make_plan(s11="TBD"))
        result = validate_plan_stars(p)
        self.assertIn(SECTION_CONTEXT, result)
        self.assertNotIn(SECTION_NOT_DOING, result)
        self.assertNotIn(SECTION_TRADEOFF, result)
        self.assertNotIn(SECTION_PHASES, result)

    def test_context_empty_codebase_literal_not_detected(self):
        p = self._write(_make_plan(s11="none (empty codebase)"))
        result = validate_plan_stars(p)
        self.assertNotIn(SECTION_CONTEXT, result)

    def test_context_missing_section_detected(self):
        text = (
            "# test\n\n"
            "## 3. 이번에 안 할 것 ★\n\n- 항목\n\n"
            "## 4. 트레이드오프 ★\n\n"
            "| a | b | c |\n|---|---|---|\n| x | y | z |\n\n"
            "## 10. Phase 분해 ★\n\n"
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|-----------|------|\n"
            "| 1 | p | 뭔가 한다 | — |\n"
        )
        p = self._write(text)
        result = validate_plan_stars(p)
        self.assertIn(SECTION_CONTEXT, result)

    def test_evaluate_empty_detected(self):
        p = self._write(_make_plan(s12=""))
        result = validate_plan_stars(p)
        self.assertIn(SECTION_EVALUATE, result)
        self.assertNotIn(SECTION_NOT_DOING, result)
        self.assertNotIn(SECTION_TRADEOFF, result)
        self.assertNotIn(SECTION_PHASES, result)

    def test_evaluate_none_not_detected(self):
        p = self._write(_make_plan(s12="none"))
        result = validate_plan_stars(p)
        self.assertNotIn(SECTION_EVALUATE, result)

    def test_evaluate_command_not_detected(self):
        p = self._write(_make_plan(s12="python -m pytest"))
        result = validate_plan_stars(p)
        self.assertNotIn(SECTION_EVALUATE, result)

    def test_evaluate_tbd_detected(self):
        p = self._write(_make_plan(s12="TBD"))
        result = validate_plan_stars(p)
        self.assertIn(SECTION_EVALUATE, result)

    def test_evaluate_missing_section_detected(self):
        text = (
            "# test\n\n"
            "## 3. 이번에 안 할 것 ★\n\n- 항목\n\n"
            "## 4. 트레이드오프 ★\n\n"
            "| a | b | c |\n|---|---|---|\n| x | y | z |\n\n"
            "## 10. Phase 분해 ★\n\n"
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|-----------|------|\n"
            "| 1 | p | 뭔가 한다 | — |\n\n"
            "## 11. Context ★\n\nnone (empty codebase)\n"
        )
        p = self._write(text)
        result = validate_plan_stars(p)
        self.assertIn(SECTION_EVALUATE, result)

    def test_file_not_found_raises(self):
        with self.assertRaises(FileNotFoundError):
            validate_plan_stars(Path("/nonexistent/plan.md"))

    def test_actual_plan_passes_original_three(self):
        actual = REPO_ROOT / "tasks" / "clarify-helper-impl" / "plan.md"
        if actual.exists():
            result = validate_plan_stars(actual)
            original_three = [s for s in result if s not in (SECTION_CONTEXT, SECTION_EVALUATE)]
            self.assertEqual(original_three, [], f"실제 plan.md 에서 빈 섹션 발견: {original_three}")


# ---------------------------------------------------------------------------
# main (CLI)
# ---------------------------------------------------------------------------


class TestMain(unittest.TestCase):

    def setUp(self) -> None:
        self._paths: list[Path] = []

    def tearDown(self) -> None:
        for p in self._paths:
            try:
                p.unlink()
            except FileNotFoundError:
                pass

    def _write(self, text: str) -> Path:
        p = _write_tmp(text)
        self._paths.append(p)
        return p

    def test_passing_plan_exits_0(self):
        p = self._write(_make_plan())
        self.assertEqual(main([str(p)]), 0)

    def test_missing_file_exits_2(self):
        self.assertEqual(main(["/nonexistent/path/plan.md"]), 2)

    def test_no_args_exits_2(self):
        self.assertEqual(main([]), 2)

    def test_too_many_args_exits_2(self):
        self.assertEqual(main(["a", "b"]), 2)

    def test_empty_section_plan_exits_0_not_2(self):
        s4_empty = "| 결정 | 이유 | 포기 |\n|------|------|------|"
        p = self._write(_make_plan(s4=s4_empty))
        self.assertEqual(main([str(p)]), 0)


class TestSliceSectionHeaderAnchor(unittest.TestCase):
    """본문 안 백틱 인용된 헤더가 진짜 섹션을 가리지 않는지 회귀 테스트.

    부트스트랩 3회차: plan 본문이 `` `## Context` `` 처럼 다른 섹션 헤더를
    백틱 인용하면 _slice_section 정규식이 잘못 첫 매치를 잡아 본문이 비어 보임.
    행 시작 앵커(`^`) + re.MULTILINE 로 해결.
    """

    def test_inline_backtick_context_header_in_body_is_ignored(self):
        text = (
            "# test\n\n"
            "## 1. 목표\n\n"
            "이번 작업은 `## Context` 섹션을 plan.md 에 추가한다. `## Context` 본문 검증도 한다.\n\n"
            "## 3. 이번에 안 할 것 ★\n\n- 빈 코드 실호출\n\n"
            "## 4. 트레이드오프 ★\n\n"
            "| 결정 | 이유 | 포기한 것 |\n"
            "|------|------|-----------|\n"
            "| 별도 모듈 | 책임 분리 | 공유 상수 |\n\n"
            "## 10. Phase 분해 ★\n\n"
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|-----------|------|\n"
            "| 1 | setup | 헬퍼 신규 | — |\n\n"
            "## 11. Context ★\n\n"
            "none (empty codebase)\n\n"
            "## Evaluate ★\n\n"
            "none\n"
        )
        p = _write_tmp(text)
        try:
            missing = validate_plan_stars(p)
            self.assertNotIn(SECTION_CONTEXT, missing)
            self.assertEqual(missing, [])
        finally:
            p.unlink()


if __name__ == "__main__":
    unittest.main()
