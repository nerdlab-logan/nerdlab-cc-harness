"""Unit tests for scripts/run_phases.py — 3중 안전망 + reviewer YAML 파싱."""
from __future__ import annotations

import sys
import unittest
import unittest.mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_phases  # noqa: E402


class TestParseReviewerOutput(unittest.TestCase):
    def test_status_ok_no_issues(self):
        text = "status: ok\nsummary: 통과\nissues: []\n"
        result = run_phases._parse_reviewer_output(text)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["issue_ids"], [])

    def test_status_needs_fix_with_issues(self):
        text = (
            "status: needs-fix\n"
            "summary: blocking 2개\n"
            "issues:\n"
            "  - id: missing-test:foo\n"
            "    severity: blocking\n"
            "    location: scripts/run_phases.py:120\n"
            "    summary: 테스트 누락\n"
            "  - id: null-check:bar\n"
            "    severity: blocking\n"
            "    location: scripts/run_phases.py:200\n"
            "    summary: null 체크 빠짐\n"
        )
        result = run_phases._parse_reviewer_output(text)
        self.assertEqual(result["status"], "needs-fix")
        self.assertEqual(result["issue_ids"], ["missing-test:foo", "null-check:bar"])

    def test_status_missing_raises(self):
        text = "summary: 무언가\nissues: []\n"
        with self.assertRaises(ValueError):
            run_phases._parse_reviewer_output(text)

    def test_yaml_in_code_fence(self):
        text = (
            "리뷰 결과를 아래에 첨부합니다.\n"
            "```yaml\n"
            "status: escalate\n"
            "summary: 판단 불가\n"
            "issues:\n"
            "  - id: plan:unclear\n"
            "    severity: blocking\n"
            "    summary: plan 부실\n"
            "```\n"
            "끝.\n"
        )
        result = run_phases._parse_reviewer_output(text)
        self.assertEqual(result["status"], "escalate")
        self.assertEqual(result["issue_ids"], ["plan:unclear"])


class TestDecidePhaseOutcome(unittest.TestCase):
    def _review(self, status: str, ids: list[str]) -> dict:
        return {"status": status, "issue_ids": ids, "raw": ""}

    def test_status_ok_passed(self):
        outcome, reason = run_phases._decide_phase_outcome(
            self._review("ok", []), round_num=1, max_rounds=3, prev_issue_ids=set()
        )
        self.assertEqual(outcome, "passed")
        self.assertIsNone(reason)

    def test_status_escalate(self):
        outcome, reason = run_phases._decide_phase_outcome(
            self._review("escalate", ["plan:unclear"]),
            round_num=1,
            max_rounds=3,
            prev_issue_ids=set(),
        )
        self.assertEqual(outcome, "escalated")
        self.assertIn("escalate", reason or "")

    def test_max_rounds_reached(self):
        outcome, reason = run_phases._decide_phase_outcome(
            self._review("needs-fix", ["a:b"]),
            round_num=3,
            max_rounds=3,
            prev_issue_ids=set(),
        )
        self.assertEqual(outcome, "escalated")
        self.assertIn("max", (reason or "").lower())

    def test_repeated_issue_id_escalates(self):
        outcome, reason = run_phases._decide_phase_outcome(
            self._review("needs-fix", ["null-check:user", "fmt:x"]),
            round_num=2,
            max_rounds=3,
            prev_issue_ids={"null-check:user"},
        )
        self.assertEqual(outcome, "escalated")
        self.assertIn("null-check:user", reason or "")

    def test_needs_fix_continues(self):
        outcome, reason = run_phases._decide_phase_outcome(
            self._review("needs-fix", ["new:issue"]),
            round_num=1,
            max_rounds=3,
            prev_issue_ids={"old:issue"},
        )
        self.assertEqual(outcome, "continue")
        self.assertIsNone(reason)

    def test_coder_blocked_reason(self):
        outcome, reason = run_phases._decide_phase_outcome(
            self._review("escalate", ["coder:blocked"]),
            round_num=1,
            max_rounds=3,
            prev_issue_ids=set(),
        )
        self.assertEqual(outcome, "escalated")
        self.assertEqual(reason, "coder blocked")

    def test_reviewer_escalate_reason_unchanged(self):
        outcome, reason = run_phases._decide_phase_outcome(
            self._review("escalate", ["plan:unclear"]),
            round_num=1,
            max_rounds=3,
            prev_issue_ids=set(),
        )
        self.assertEqual(outcome, "escalated")
        self.assertEqual(reason, "reviewer escalate")


class TestComposeSystemPrompt(unittest.TestCase):
    def _mock_read(self, name: str) -> str:
        mapping = {
            "coder.md": "BASE_CODER",
            "reviewer.md": "BASE_REVIEWER",
            "coder_tdd.md": "TDD_CODER_RULE",
            "reviewer_tdd.md": "TDD_REVIEWER_RULE",
        }
        if name not in mapping:
            raise FileNotFoundError(name)
        return mapping[name]

    def test_tdd_off_returns_base_only(self):
        with unittest.mock.patch.object(run_phases, "_read_prompt", side_effect=self._mock_read):
            result = run_phases._compose_system_prompt("coder", tdd=False)
        self.assertEqual(result, "BASE_CODER")

    def test_tdd_on_appends_tdd_prompt(self):
        with unittest.mock.patch.object(run_phases, "_read_prompt", side_effect=self._mock_read):
            result = run_phases._compose_system_prompt("coder", tdd=True)
        self.assertIn("BASE_CODER", result)
        self.assertIn("TDD_CODER_RULE", result)
        self.assertIn("---", result)

    def test_role_coder_vs_reviewer(self):
        with unittest.mock.patch.object(run_phases, "_read_prompt", side_effect=self._mock_read):
            coder_result = run_phases._compose_system_prompt("coder", tdd=True)
            reviewer_result = run_phases._compose_system_prompt("reviewer", tdd=True)
        self.assertIn("BASE_CODER", coder_result)
        self.assertIn("TDD_CODER_RULE", coder_result)
        self.assertIn("BASE_REVIEWER", reviewer_result)
        self.assertIn("TDD_REVIEWER_RULE", reviewer_result)
        self.assertNotIn("BASE_REVIEWER", coder_result)
        self.assertNotIn("BASE_CODER", reviewer_result)


class TestIsCoderBlocked(unittest.TestCase):
    def test_blocked_first_line(self):
        self.assertTrue(run_phases._is_coder_blocked("BLOCKED: plan 에 결정 없음"))

    def test_blocked_with_leading_whitespace(self):
        self.assertTrue(run_phases._is_coder_blocked("  BLOCKED: 모호한 요구사항"))

    def test_not_blocked_normal_output(self):
        self.assertFalse(run_phases._is_coder_blocked("변경: scripts/run_phases.py\n요약: 수정 완료"))

    def test_not_blocked_empty_string(self):
        self.assertFalse(run_phases._is_coder_blocked(""))

    def test_not_blocked_second_line_only(self):
        self.assertFalse(run_phases._is_coder_blocked("변경: foo.py\nBLOCKED: 이건 두 번째 줄"))


class TestRunInline(unittest.TestCase):
    def _make_plan(self, tmp_path: Path, phase_rows: list[str], changed_lines: list[str]) -> Path:
        phase_table = (
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|-----------|------|\n"
        ) + "\n".join(phase_rows)
        changed_section = "## 변경 파일\n\n" + "\n".join(changed_lines) if changed_lines else ""
        content = f"# Test Plan\n\n## Phase 분해 ★\n\n{phase_table}\n\n{changed_section}\n"
        plan = tmp_path / "plan.md"
        plan.write_text(content, encoding="utf-8")
        return plan

    def test_single_phase_single_file_returns_zero(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = self._make_plan(
                Path(d),
                ["| 1 | 구현 | 뭔가를 한다 | — |"],
                ["- [수정] scripts/run_phases.py — 변경 설명"],
            )
            phases = run_phases.parse_phases(plan)
            rc = run_phases.run_inline(plan, phases)
        self.assertEqual(rc, 0)

    def test_multiple_phases_returns_invalid(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = self._make_plan(
                Path(d),
                [
                    "| 1 | 구현1 | 뭔가1 | — |",
                    "| 2 | 구현2 | 뭔가2 | 1 |",
                ],
                ["- [수정] scripts/run_phases.py — 변경 설명"],
            )
            phases = run_phases.parse_phases(plan)
            rc = run_phases.run_inline(plan, phases)
        self.assertEqual(rc, run_phases.EXIT_CODE_INLINE_INVALID)

    def test_multiple_changed_files_returns_invalid(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = self._make_plan(
                Path(d),
                ["| 1 | 구현 | 뭔가를 한다 | — |"],
                [
                    "- [수정] scripts/run_phases.py — 변경 설명",
                    "- [신규] tests/test_run_phases.py — 테스트 추가",
                ],
            )
            phases = run_phases.parse_phases(plan)
            rc = run_phases.run_inline(plan, phases)
        self.assertEqual(rc, run_phases.EXIT_CODE_INLINE_INVALID)


class TestParsePhasesHeaderAnchor(unittest.TestCase):
    """## Phase 분해 매칭은 행 시작 앵커여야 한다 (docstring 안의 백틱 인용은 무시)."""

    def _write(self, dir_: Path, body: str) -> Path:
        p = dir_ / "plan.md"
        p.write_text(body, encoding="utf-8")
        return p

    def test_inline_backtick_phase_header_in_signature_is_ignored(self):
        import tempfile
        body = (
            "# Plan: x\n\n"
            "## 시그니처\n\n"
            "```python\n"
            "def f():\n"
            '    """plan_text 의 `## Phase 분해` 섹션 표 ..."""\n'
            "```\n\n"
            "## Phase 분해\n\n"
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|------------|------|\n"
            "| 1 | 단일 | 어떤 작업 | — |\n"
        )
        with tempfile.TemporaryDirectory() as d:
            plan = self._write(Path(d), body)
            phases = run_phases.parse_phases(plan)
        self.assertEqual(len(phases), 1)
        self.assertEqual(phases[0].number, 1)
        self.assertEqual(phases[0].name, "단일")

    def test_numbered_section_prefix_is_accepted(self):
        import tempfile
        body = (
            "# Plan: x\n\n"
            "## 10. Phase 분해 ★\n\n"
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|------------|------|\n"
            "| 1 | helper | 헬퍼 작성 | — |\n"
            "| 2 | wiring | 문서 연결 | 1 |\n"
        )
        with tempfile.TemporaryDirectory() as d:
            plan = self._write(Path(d), body)
            phases = run_phases.parse_phases(plan)
            sliced = run_phases._slice_phase_table(plan.read_text(), 2)
        self.assertEqual([p.number for p in phases], [1, 2])
        self.assertEqual(phases[1].depends_on, [1])
        self.assertIn("| 2 | wiring", sliced)
        self.assertNotIn("| 1 | helper", sliced)


class TestParsePhasesDependsColumn(unittest.TestCase):
    """의존 컬럼은 '없음' 한국어 키워드와 '1 (괄호 부가설명)' 형식을 모두 빈/정수로 처리해야 한다."""

    def _write(self, dir_: Path, rows: str) -> Path:
        body = (
            "# Plan: x\n\n"
            "## Phase 분해\n\n"
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|------------|------|\n"
            f"{rows}"
        )
        p = dir_ / "plan.md"
        p.write_text(body, encoding="utf-8")
        return p

    def test_korean_keyword_없음_treated_as_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = self._write(Path(d), "| 1 | a | 작업 | 없음 |\n")
            phases = run_phases.parse_phases(plan)
        self.assertEqual(phases[0].depends_on, [])

    def test_int_with_paren_explanation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = self._write(
                Path(d),
                "| 1 | a | 작업 | — |\n"
                "| 2 | b | 작업 | 1 (a 의 결과 필요) |\n",
            )
            phases = run_phases.parse_phases(plan)
        self.assertEqual(phases[1].depends_on, [1])

    def test_em_dash_still_works(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = self._write(Path(d), "| 1 | a | 작업 | — |\n")
            phases = run_phases.parse_phases(plan)
        self.assertEqual(phases[0].depends_on, [])

    def test_multiple_ints_still_works(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = self._write(
                Path(d),
                "| 1 | a | 작업 | — |\n"
                "| 2 | b | 작업 | — |\n"
                "| 3 | c | 작업 | 1, 2 |\n",
            )
            phases = run_phases.parse_phases(plan)
        self.assertEqual(phases[2].depends_on, [1, 2])

    def test_paren_with_inner_numbers_ignored(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = self._write(
                Path(d),
                "| 1 | a | 작업 | — |\n"
                "| 2 | b | 작업 | 1 (issue #42 참고) |\n",
            )
            phases = run_phases.parse_phases(plan)
        self.assertEqual(phases[1].depends_on, [1])  # 괄호 안의 42 무시


class TestSlicePhaseTable(unittest.TestCase):
    def _make_plan(self, rows: list[str]) -> str:
        header = (
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|------------|------|\n"
        )
        table = header + "\n".join(rows)
        return f"# 테스트 Plan\n\n## Phase 분해\n\n{table}\n\n## 다음 섹션\n\n내용\n"

    def test_keeps_only_matching_row(self):
        plan = self._make_plan([
            "| 1 | 준비 | 준비 작업 | — |",
            "| 2 | 구현 | 핵심 구현 | 1 |",
            "| 3 | 검증 | 테스트 | 2 |",
        ])
        result = run_phases._slice_phase_table(plan, 2)
        self.assertIn("| 2 | 구현 | 핵심 구현 | 1 |", result)
        self.assertNotIn("| 1 | 준비 |", result)
        self.assertNotIn("| 3 | 검증 |", result)

    def test_keeps_header_rows(self):
        plan = self._make_plan([
            "| 1 | 단일 | 작업 | — |",
        ])
        result = run_phases._slice_phase_table(plan, 1)
        self.assertIn("| 번호 | 이름 |", result)
        self.assertIn("|------|", result)

    def test_single_row_table(self):
        plan = self._make_plan([
            "| 1 | 단일 | 작업 | — |",
        ])
        result = run_phases._slice_phase_table(plan, 1)
        self.assertIn("| 1 | 단일 | 작업 | — |", result)

    def test_row_not_found_raises(self):
        plan = self._make_plan([
            "| 1 | 단일 | 작업 | — |",
        ])
        with self.assertRaises(ValueError):
            run_phases._slice_phase_table(plan, 99)

    def test_section_not_found_raises(self):
        plan = "# Plan\n\n## 다른 섹션\n\n내용\n"
        with self.assertRaises(ValueError):
            run_phases._slice_phase_table(plan, 1)

    def test_rest_of_plan_preserved(self):
        plan = self._make_plan([
            "| 1 | 단일 | 작업 | — |",
            "| 2 | 다음 | 작업2 | 1 |",
        ])
        result = run_phases._slice_phase_table(plan, 1)
        self.assertIn("# 테스트 Plan", result)
        self.assertIn("## 다음 섹션", result)
        self.assertIn("내용", result)

    def test_first_row_selected(self):
        plan = self._make_plan([
            "| 1 | A | 작업A | — |",
            "| 2 | B | 작업B | 1 |",
        ])
        result = run_phases._slice_phase_table(plan, 1)
        self.assertIn("| 1 | A | 작업A | — |", result)
        self.assertNotIn("| 2 | B |", result)


class TestBuildReviewerPrompt(unittest.TestCase):
    def _make_plan_file(self, tmp_path: Path, rows: list[str]) -> Path:
        header = (
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|------------|------|\n"
        )
        table = header + "\n".join(rows)
        content = f"# 테스트 Plan\n\n## Phase 분해\n\n{table}\n"
        plan = tmp_path / "plan.md"
        plan.write_text(content, encoding="utf-8")
        return plan

    def test_guide_line_at_start(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = self._make_plan_file(
                Path(d),
                ["| 1 | 단일 | 작업 | — |"],
            )
            phase = run_phases.Phase(number=1, name="단일", scope="작업")
            prompt = run_phases._build_reviewer_prompt(plan, phase, round_num=1)
        self.assertTrue(
            prompt.startswith("이번 라운드는 phase 1 (단일) 의 변경사항만 검증한다.")
        )

    def test_sliced_table_excludes_other_phases(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = self._make_plan_file(
                Path(d),
                [
                    "| 1 | 준비 | 준비 작업 | — |",
                    "| 2 | 구현 | 핵심 구현 | 1 |",
                ],
            )
            phase = run_phases.Phase(number=2, name="구현", scope="핵심 구현")
            prompt = run_phases._build_reviewer_prompt(plan, phase, round_num=2)
        self.assertIn("| 2 | 구현 | 핵심 구현 | 1 |", prompt)
        self.assertNotIn("| 1 | 준비 |", prompt)

    def test_round_num_in_prompt(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = self._make_plan_file(
                Path(d),
                ["| 3 | 검증 | 테스트 작업 | 2 |"],
            )
            phase = run_phases.Phase(number=3, name="검증", scope="테스트 작업")
            prompt = run_phases._build_reviewer_prompt(plan, phase, round_num=2)
        self.assertIn("라운드 2", prompt)

    def test_phase_name_in_guide(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = self._make_plan_file(
                Path(d),
                ["| 1 | 단일 | 어떤 작업 | — |"],
            )
            phase = run_phases.Phase(number=1, name="단일", scope="어떤 작업")
            prompt = run_phases._build_reviewer_prompt(plan, phase, round_num=1)
        self.assertIn("phase 1 (단일)", prompt.splitlines()[0])


class TestRunEvaluate(unittest.TestCase):
    """_run_evaluate 단위 테스트."""

    def _make_proc(self, returncode: int, stdout: str = "", stderr: str = "") -> unittest.mock.MagicMock:
        proc = unittest.mock.MagicMock()
        proc.returncode = returncode
        proc.stdout = stdout
        proc.stderr = stderr
        return proc

    def test_empty_commands_returns_success(self):
        with unittest.mock.patch("subprocess.run") as mock_run:
            ok, log = run_phases._run_evaluate([], cwd=Path("/tmp"))
        self.assertTrue(ok)
        self.assertEqual(log, "")
        mock_run.assert_not_called()

    def test_all_commands_succeed(self):
        """다중 직렬: 모든 명령 성공 → (True, log)"""
        with unittest.mock.patch("subprocess.run", return_value=self._make_proc(0, "ok\n")) as mock_run:
            ok, log = run_phases._run_evaluate(["/bin/true", "/bin/true"], cwd=Path("/tmp"))
        self.assertTrue(ok)
        self.assertEqual(mock_run.call_count, 2)
        self.assertIn("/bin/true", log)

    def test_first_failure_stops_execution(self):
        """첫 실패 stop: 첫 명령 rc!=0 → 두 번째 미실행"""
        with unittest.mock.patch("subprocess.run", return_value=self._make_proc(1, "", "error")) as mock_run:
            ok, log = run_phases._run_evaluate(["/bin/false", "/bin/true"], cwd=Path("/tmp"))
        self.assertFalse(ok)
        self.assertEqual(mock_run.call_count, 1)

    def test_exit_code_in_log(self):
        """exit code 전파: rc 가 log 에 포함"""
        with unittest.mock.patch("subprocess.run", return_value=self._make_proc(42)):
            ok, log = run_phases._run_evaluate(["some-cmd"], cwd=Path("/tmp"))
        self.assertFalse(ok)
        self.assertIn("42", log)


class TestParseEvalCommands(unittest.TestCase):
    """_parse_eval_commands: '## Evaluate ★' 섹션 헤더는 numbered prefix(`## 12. Evaluate ★`)도 인식해야 한다."""

    def _write(self, dir_: Path, body: str) -> Path:
        p = dir_ / "plan.md"
        p.write_text(body, encoding="utf-8")
        return p

    def test_plain_header_parses_commands(self):
        import tempfile
        body = (
            "# Plan: x\n\n"
            "## Evaluate ★\n\n"
            "```\n"
            "mypy src\n"
            "pytest -q\n"
            "```\n"
        )
        with tempfile.TemporaryDirectory() as d:
            plan = self._write(Path(d), body)
            cmds = run_phases._parse_eval_commands(plan)
        self.assertEqual(cmds, ["mypy src", "pytest -q"])

    def test_fenced_block_marker_is_ignored(self):
        """``` 펜스 마커는 명령으로 취급되면 안 된다 (회귀)."""
        import tempfile
        body = (
            "# Plan: x\n\n"
            "## Evaluate ★\n\n"
            "```bash\n"
            "echo hi\n"
            "```\n"
        )
        with tempfile.TemporaryDirectory() as d:
            plan = self._write(Path(d), body)
            cmds = run_phases._parse_eval_commands(plan)
        self.assertEqual(cmds, ["echo hi"])

    def test_numbered_prefix_header_parses_commands(self):
        """planner 가 만드는 `## 12. Evaluate ★` 형태도 매칭되어야 한다 (회귀)."""
        import tempfile
        body = (
            "# Plan: x\n\n"
            "## 12. Evaluate ★\n\n"
            "```\n"
            ".venv/bin/mypy src tests\n"
            ".venv/bin/ruff check .\n"
            ".venv/bin/pytest -q\n"
            "```\n"
        )
        with tempfile.TemporaryDirectory() as d:
            plan = self._write(Path(d), body)
            cmds = run_phases._parse_eval_commands(plan)
        self.assertEqual(
            cmds,
            [".venv/bin/mypy src tests", ".venv/bin/ruff check .", ".venv/bin/pytest -q"],
        )

    def test_none_returns_empty_list(self):
        import tempfile
        body = (
            "# Plan: x\n\n"
            "## 12. Evaluate ★\n\n"
            "none\n"
        )
        with tempfile.TemporaryDirectory() as d:
            plan = self._write(Path(d), body)
            cmds = run_phases._parse_eval_commands(plan)
        self.assertEqual(cmds, [])

    def test_missing_section_returns_empty_list(self):
        import tempfile
        body = "# Plan: x\n\n## 1. 목표\n\n잡소리\n"
        with tempfile.TemporaryDirectory() as d:
            plan = self._write(Path(d), body)
            cmds = run_phases._parse_eval_commands(plan)
        self.assertEqual(cmds, [])


class TestMakeEvalReview(unittest.TestCase):
    """_make_eval_review 단위 테스트."""

    def test_needs_fix_below_max_rounds(self):
        result = run_phases._make_eval_review("log text", round_num=1, max_rounds=3)
        self.assertEqual(result["status"], "needs-fix")
        self.assertEqual(result["issue_ids"], ["eval-fail"])
        self.assertEqual(result["raw"], "log text")

    def test_escalate_at_max_rounds(self):
        result = run_phases._make_eval_review("log text", round_num=3, max_rounds=3)
        self.assertEqual(result["status"], "escalate")
        self.assertEqual(result["issue_ids"], ["eval-fail"])

    def test_escalate_above_max_rounds(self):
        result = run_phases._make_eval_review("log text", round_num=4, max_rounds=3)
        self.assertEqual(result["status"], "escalate")


class TestRunPhaseEvalGate(unittest.TestCase):
    """run_phase eval 게이트 통합 테스트."""

    def _make_plan(self, tmp_path: Path, eval_section: str = "python -m pytest") -> Path:
        content = (
            "# Test Plan\n\n"
            "## Phase 분해 ★\n\n"
            "| 번호 | 이름 | 범위 한 줄 | 의존 |\n"
            "|------|------|-----------|------|\n"
            "| 1 | 구현 | 테스트 작업 | — |\n\n"
            f"## Evaluate ★\n\n{eval_section}\n"
        )
        plan = tmp_path / "plan.md"
        plan.write_text(content, encoding="utf-8")
        return plan

    def test_eval_failure_reruns_coder(self):
        """reviewer ok + eval 실패 → 다음 round coder 재호출"""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            task_dir = Path(d)
            plan_path = self._make_plan(task_dir)
            phase = run_phases.Phase(number=1, name="구현", scope="테스트 작업")

            round_calls = []

            def mock_run_round(ph, rn, td, pp, prev_review=None, tdd=False):
                round_calls.append(rn)
                return {"status": "ok", "issue_ids": [], "raw": ""}

            eval_calls = [0]

            def mock_run_evaluate(commands, cwd):
                eval_calls[0] += 1
                return (False, "test failed") if eval_calls[0] == 1 else (True, "ok")

            with unittest.mock.patch.object(run_phases, "run_round", side_effect=mock_run_round):
                with unittest.mock.patch.object(run_phases, "_run_evaluate", side_effect=mock_run_evaluate):
                    result = run_phases.run_phase(phase, task_dir, max_rounds=3, plan_path=plan_path)

        self.assertEqual(result.state, "passed")
        self.assertEqual(len(round_calls), 2)
        self.assertEqual(eval_calls[0], 2)

    def test_eval_failure_at_max_rounds_escalates(self):
        """eval 실패 + round == max_rounds → escalated"""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            task_dir = Path(d)
            plan_path = self._make_plan(task_dir)
            phase = run_phases.Phase(number=1, name="구현", scope="테스트 작업")

            def mock_run_round(ph, rn, td, pp, prev_review=None, tdd=False):
                return {"status": "ok", "issue_ids": [], "raw": ""}

            def mock_run_evaluate(commands, cwd):
                return (False, "test failed")

            with unittest.mock.patch.object(run_phases, "run_round", side_effect=mock_run_round):
                with unittest.mock.patch.object(run_phases, "_run_evaluate", side_effect=mock_run_evaluate):
                    result = run_phases.run_phase(phase, task_dir, max_rounds=1, plan_path=plan_path)

        self.assertEqual(result.state, "escalated")

    def test_no_eval_commands_passes_directly(self):
        """Evaluate=none → eval 스킵, 바로 passed"""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            task_dir = Path(d)
            plan_path = self._make_plan(task_dir, eval_section="none")
            phase = run_phases.Phase(number=1, name="구현", scope="테스트 작업")

            def mock_run_round(ph, rn, td, pp, prev_review=None, tdd=False):
                return {"status": "ok", "issue_ids": [], "raw": ""}

            with unittest.mock.patch.object(run_phases, "run_round", side_effect=mock_run_round):
                with unittest.mock.patch.object(run_phases, "_run_evaluate") as mock_eval:
                    result = run_phases.run_phase(phase, task_dir, max_rounds=3, plan_path=plan_path)

        self.assertEqual(result.state, "passed")
        mock_eval.assert_not_called()


class TestGitGuard(unittest.TestCase):
    def test_check_git_state_no_git_dir(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            ok, msg = run_phases._check_git_state(Path(d))
        self.assertFalse(ok)
        self.assertIn(".git", msg)
        self.assertIn("/nl-setup", msg)

    def test_check_git_state_dirty_tree(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".git").mkdir()
            with unittest.mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = unittest.mock.MagicMock(
                    stdout="M  some_file.py\n", stderr="", returncode=0
                )
                ok, msg = run_phases._check_git_state(Path(d))
        self.assertFalse(ok)
        self.assertIn("dirty", msg)
        self.assertIn("git stash", msg)

    def test_check_git_state_clean_tree(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".git").mkdir()
            with unittest.mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = unittest.mock.MagicMock(
                    stdout="", stderr="", returncode=0
                )
                ok, msg = run_phases._check_git_state(Path(d))
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_ensure_feature_branch_on_main(self):
        branch_proc = unittest.mock.MagicMock(stdout="main\n", returncode=0)
        checkout_proc = unittest.mock.MagicMock(stdout="", returncode=0)
        with unittest.mock.patch("subprocess.run", side_effect=[branch_proc, checkout_proc]):
            result = run_phases._ensure_feature_branch("my-task", Path("/fake/repo"))
        self.assertEqual(result, "feat/my-task")

    def test_ensure_feature_branch_on_non_main(self):
        branch_proc = unittest.mock.MagicMock(stdout="feat/other-task\n", returncode=0)
        with unittest.mock.patch("subprocess.run", return_value=branch_proc):
            result = run_phases._ensure_feature_branch("my-task", Path("/fake/repo"))
        self.assertEqual(result, "feat/other-task")

    def test_render_failure_report_format(self):
        phase = run_phases.Phase(number=2, name="main-통합", scope="main() hook 연결")
        report = run_phases._render_failure_report(phase, "abc1234", "eval 실패")
        self.assertIn("phase 2 (main-통합) 실패: eval 실패", report)
        self.assertIn("last_good_commit: abc1234", report)
        self.assertIn("git reset --hard abc1234", report)

    def test_render_failure_report_no_auto_reset(self):
        phase = run_phases.Phase(number=1, name="스펙", scope="spec 작성")
        report = run_phases._render_failure_report(phase, "deadbeef", "reviewer escalate")
        lines = report.splitlines()
        self.assertTrue(any("reset --hard" in line for line in lines))
        self.assertNotIn("subprocess", report)


if __name__ == "__main__":
    unittest.main()
