#!/usr/bin/env python3
"""run_phases.py — nerdlab-harness phase orchestrator.

plan 의 `Phase 분해` 표를 파싱해 phase 직렬 실행 + 각 phase 별로 coder(Sonnet) ↔
reviewer(Opus) 헤드리스 루프를 돌리고 3중 안전망(status==ok / max-rounds /
동일 issue id 2회 연속) 으로 종료를 판정한다.

사용:
    python scripts/run_phases.py <plan_path> [--resume] [--max-rounds N] [--task-dir PATH]

설계 참조:
    docs/spec/plan-template.md (Phase 분해 표 형식)
    docs/spec/reviewer-output.md (status 매핑)
    tasks/run-phases-implement/plan.md (본구현 plan)
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

PhaseState = Literal["pending", "in_progress", "passed", "failed", "escalated"]
PhaseOutcome = Literal["passed", "escalated", "continue"]

SCHEMA_VERSION = 1
DEFAULT_MAX_ROUNDS = 3
STATUS_FILE = "status.json"
PHASE_TABLE_HEADER = "Phase 분해"

CODER_MODEL = "sonnet"
REVIEWER_MODEL = "opus"
PROMPTS_DIR_NAME = "prompts"
CODER_PROMPT = "coder.md"
REVIEWER_PROMPT = "reviewer.md"
CODER_PROMPT_TDD = "coder_tdd.md"
REVIEWER_PROMPT_TDD = "reviewer_tdd.md"
CODER_ALLOWED_TOOLS = "Read,Edit,Write,Glob,Grep,Bash"
REVIEWER_ALLOWED_TOOLS = "Read,Glob,Grep,Bash"

EXIT_CODE_INLINE_INVALID = 5  # --inline 인데 phase ≥ 2 또는 변경 파일 ≥ 2
EXIT_CODE_GIT_GUARD = 6  # git 상태 검증 실패 (.git 없음 또는 dirty tree)
EVAL_TIMEOUT = 300  # eval 명령 1개당 타임아웃(초)

_EVALUATE_SECTION_RE = re.compile(r"^##\s+Evaluate\s+★", re.MULTILINE)


@dataclass
class Phase:
    number: int
    name: str
    scope: str
    depends_on: list[int] = field(default_factory=list)


@dataclass
class PhaseStatus:
    number: int
    name: str
    state: PhaseState
    rounds: int = 0
    last_run_at: Optional[str] = None
    failure_reason: Optional[str] = None
    repeated_issue_id: Optional[str] = None


@dataclass
class RunStatus:
    schema_version: int
    plan_path: str
    task_name: str
    max_rounds: int
    current_phase: int
    phases: list[PhaseStatus]
    started_at: str
    updated_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_phases.py",
        description="nerdlab-harness phase orchestrator",
    )
    parser.add_argument(
        "plan_path",
        type=Path,
        help="plan.md 경로 (예: tasks/<task-name>/plan.md)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="기존 status.json 을 읽어 이어서 실행",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=DEFAULT_MAX_ROUNDS,
        help=f"한 phase 안의 최대 라운드 (기본 {DEFAULT_MAX_ROUNDS})",
    )
    parser.add_argument(
        "--task-dir",
        type=Path,
        default=None,
        help="status.json 등 산출물 저장 디렉토리 (기본: plan.md 의 부모 디렉토리)",
    )
    parser.add_argument(
        "--tdd",
        action="store_true",
        help="TDD 모드: 실패 테스트 작성 → 구현 → 통과 룰을 시스템 프롬프트에 추가",
    )
    parser.add_argument(
        "--inline",
        action="store_true",
        help="Inline 모드: phase 1개·변경 파일 1개 plan 을 메인이 직접 처리하는 분기",
    )
    return parser.parse_args(argv)


def task_dir_for(plan_path: Path) -> Path:
    return plan_path.resolve().parent


def parse_phases(plan_path: Path) -> list[Phase]:
    text = plan_path.read_text(encoding="utf-8")
    header_re = re.compile(
        rf"^##\s+(?:\d+\.\s+)?{re.escape(PHASE_TABLE_HEADER)}.*?\n",
        re.MULTILINE,
    )
    m = header_re.search(text)
    if not m:
        raise ValueError(f"plan 에서 '{PHASE_TABLE_HEADER}' 섹션을 찾지 못함: {plan_path}")
    after = text[m.end():]

    table_lines: list[str] = []
    for line in after.splitlines():
        stripped = line.strip()
        if stripped.startswith("##"):
            break
        if not stripped:
            if table_lines:
                break
            continue
        if stripped.startswith("|"):
            table_lines.append(stripped)

    if len(table_lines) < 3:
        raise ValueError(f"plan 의 Phase 분해 표가 비어 있음: {plan_path}")
    data_lines = table_lines[2:]

    phases: list[Phase] = []
    for raw in data_lines:
        cells = [c.strip() for c in raw.strip("|").split("|")]
        if len(cells) < 4:
            raise ValueError(f"Phase 분해 행의 컬럼이 4개 미만: {raw!r}")
        try:
            number = int(cells[0])
        except ValueError as e:
            raise ValueError(f"Phase 번호 파싱 실패: {cells[0]!r}") from e
        name = cells[1]
        scope = cells[2]
        depends_raw = cells[3]
        # 괄호 이후 부가설명 제거 (예: "1 (plan-template 형식 ...)" → "1")
        depends_clean = re.sub(r"\s*\(.*$", "", depends_raw).strip()
        depends_on: list[int] = []
        # 빈 키워드: "—"/"-"/"–"(em/en/figure dash) + "없음"/"none"/"X"(빈 표기 변형)
        if depends_clean and depends_clean.lower() not in {"—", "-", "–", "없음", "none", "x"}:
            for tok in re.findall(r"\d+", depends_clean):
                depends_on.append(int(tok))
        phases.append(Phase(number=number, name=name, scope=scope, depends_on=depends_on))

    if not phases:
        raise ValueError(f"plan 의 Phase 분해 표에 데이터 행이 없음: {plan_path}")
    return phases


def init_status(plan_path: Path, phases: list[Phase], max_rounds: int) -> RunStatus:
    now = _now_iso()
    task_name = task_dir_for(plan_path).name
    return RunStatus(
        schema_version=SCHEMA_VERSION,
        plan_path=str(plan_path),
        task_name=task_name,
        max_rounds=max_rounds,
        current_phase=0,
        phases=[
            PhaseStatus(number=p.number, name=p.name, state="pending")
            for p in phases
        ],
        started_at=now,
        updated_at=now,
    )


def load_status(task_dir: Path) -> Optional[RunStatus]:
    path = task_dir / STATUS_FILE
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"status.json schema_version 불일치 "
            f"(기대 {SCHEMA_VERSION}, 실제 {data.get('schema_version')!r}): {path}"
        )
    phases = [PhaseStatus(**p) for p in data["phases"]]
    return RunStatus(
        schema_version=data["schema_version"],
        plan_path=data["plan_path"],
        task_name=data["task_name"],
        max_rounds=data["max_rounds"],
        current_phase=data["current_phase"],
        phases=phases,
        started_at=data["started_at"],
        updated_at=data["updated_at"],
    )


def save_status(task_dir: Path, status: RunStatus) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    status.updated_at = _now_iso()
    path = task_dir / STATUS_FILE
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(asdict(status), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_prompt(name: str) -> str:
    return (_repo_root() / PROMPTS_DIR_NAME / name).read_text(encoding="utf-8")


def _compose_system_prompt(role: str, tdd: bool) -> str:
    """role ∈ {"coder", "reviewer"}. 기본 prompt + (tdd 시) prompts/<role>_tdd.md append."""
    base_name = CODER_PROMPT if role == "coder" else REVIEWER_PROMPT
    base = _read_prompt(base_name)
    if not tdd:
        return base
    tdd_name = CODER_PROMPT_TDD if role == "coder" else REVIEWER_PROMPT_TDD
    tdd_extra = _read_prompt(tdd_name)
    return base + "\n\n---\n\n" + tdd_extra


_FENCE_RE = re.compile(r"```(?:yaml|yml)?\s*\n(.*?)\n```", re.DOTALL)
_STATUS_RE = re.compile(
    r"(?m)^[ \t]*status:[ \t]*(ok|needs-fix|escalate)[ \t]*$"
)
_ID_RE = re.compile(r"(?m)^\s*-?\s*id:[ \t]*(\S+)[ \t]*$")


def _parse_reviewer_output(text: str) -> dict:
    """reviewer stdout 에서 status / issue id 추출.

    fence(```yaml ... ```)가 있으면 그 안의 본문만 본다.
    status: 누락 시 ValueError. minor/blocking 등 severity 는 무시 — 본 안전망은 id 만 본다.
    """
    fence = _FENCE_RE.search(text)
    body = fence.group(1) if fence else text

    sm = _STATUS_RE.search(body)
    if not sm:
        raise ValueError(
            "reviewer 출력에서 status: 를 찾지 못함 "
            f"(앞 200자: {text[:200]!r})"
        )
    status = sm.group(1)
    issue_ids = [m.group(1) for m in _ID_RE.finditer(body)]
    return {"status": status, "issue_ids": issue_ids, "raw": text}


def _decide_phase_outcome(
    review: dict,
    round_num: int,
    max_rounds: int,
    prev_issue_ids: set[str],
) -> tuple[PhaseOutcome, Optional[str]]:
    """3중 안전망 판정 (순수 함수).

    우선순위:
      1) status == "ok" → passed
      2) status == "escalate" → escalated (reviewer escalate)
      3) round_num >= max_rounds → escalated (max rounds reached)
      4) prev_issue_ids ∩ issue_ids 비어있지 않음 → escalated (repeated issue: <id>)
      5) needs-fix → continue
    """
    status = review.get("status")
    issue_ids = review.get("issue_ids") or []

    if status == "ok":
        return ("passed", None)
    if status == "escalate":
        if issue_ids and issue_ids[0] == "coder:blocked":
            return ("escalated", "coder blocked")
        return ("escalated", "reviewer escalate")
    if round_num >= max_rounds:
        return ("escalated", "max rounds reached")
    repeated = prev_issue_ids.intersection(issue_ids)
    if repeated:
        rep = sorted(repeated)[0]
        return ("escalated", f"repeated issue: {rep}")
    return ("continue", None)


def _slice_phase_table(plan_text: str, phase_number: int) -> str:
    """plan_text 의 `## Phase 분해` 섹션 표에서 phase_number 와 일치하는 데이터 행만
    남기고 나머지 행을 제거한 plan_text 를 반환한다.

    헤더 2줄 (컬럼명 + 구분선) 은 유지한다. 일치 행이 없으면 ValueError 를 던진다.
    Phase 분해 섹션이 plan 에 없으면 ValueError 를 던진다 (parse_phases 와 동일 정책).
    """
    header_re = re.compile(
        rf"^##\s+(?:\d+\.\s+)?{re.escape(PHASE_TABLE_HEADER)}.*?\n",
        re.MULTILINE,
    )
    m = header_re.search(plan_text)
    if not m:
        raise ValueError(f"plan 에서 '{PHASE_TABLE_HEADER}' 섹션을 찾지 못함")

    after_offset = m.end()
    remaining = plan_text[after_offset:]

    lines_with_pos: list[tuple[int, int, str]] = []  # (start, end, raw_line_with_newline)
    pos = 0
    seen_table = False
    for raw_line in remaining.splitlines(keepends=True):
        end = pos + len(raw_line)
        stripped = raw_line.strip()
        if stripped.startswith("##"):
            break
        if not stripped:
            if seen_table:
                break
            pos = end
            continue
        if stripped.startswith("|"):
            lines_with_pos.append((pos, end, raw_line))
            seen_table = True
        pos = end

    if len(lines_with_pos) < 2:
        raise ValueError("plan 의 Phase 분해 표가 비어 있음")

    header_rows = lines_with_pos[:2]
    data_rows = lines_with_pos[2:]

    matched_row: Optional[tuple[int, int, str]] = None
    for start, end, raw_line in data_rows:
        cells = [c.strip() for c in raw_line.strip().strip("|").split("|")]
        if cells and cells[0] == str(phase_number):
            matched_row = (start, end, raw_line)
            break

    if matched_row is None:
        raise ValueError(f"Phase 분해 표에서 phase {phase_number} 행을 찾지 못함")

    table_start = header_rows[0][0]
    table_end = data_rows[-1][1]
    new_table = "".join(r for _, _, r in header_rows) + matched_row[2]
    new_remaining = remaining[:table_start] + new_table + remaining[table_end:]
    return plan_text[:after_offset] + new_remaining


def _build_coder_prompt(
    plan_path: Path,
    phase: Phase,
    round_num: int,
    prev_review: Optional[dict],
) -> str:
    plan_text = plan_path.read_text(encoding="utf-8")
    parts = [
        f"다음 plan 의 phase {phase.number} ({phase.name}) 를 구현하라. (라운드 {round_num})",
        "",
        "## Phase 범위",
        phase.scope,
        "",
        "## Plan 전체",
        plan_text,
    ]
    if prev_review and prev_review.get("raw"):
        parts.extend(
            [
                "",
                "## 직전 라운드 reviewer 결과",
                prev_review["raw"],
            ]
        )
    return "\n".join(parts)


def _build_reviewer_prompt(plan_path: Path, phase: Phase, round_num: int) -> str:
    plan_text = plan_path.read_text(encoding="utf-8")
    sliced = _slice_phase_table(plan_text, phase.number)
    return "\n".join(
        [
            f"이번 라운드는 phase {phase.number} ({phase.name}) 의 변경사항만 검증한다.",
            "",
            f"다음 plan 의 phase {phase.number} ({phase.name}) 변경사항을 검토하라. (라운드 {round_num})",
            "",
            "## Phase 범위",
            phase.scope,
            "",
            "## Plan 전체",
            sliced,
            "",
            "출력은 docs/spec/reviewer-output.md 의 YAML 스키마 그대로. 추가 산문 금지.",
        ]
    )


def _run_claude(
    model: str,
    allowed_tools: str,
    system_prompt: str,
    user_prompt: str,
) -> tuple[str, str, int]:
    cmd = [
        "claude",
        "-p",
        "--model",
        model,
        "--allowed-tools",
        allowed_tools,
        "--append-system-prompt",
        system_prompt,
        user_prompt,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.stdout, proc.stderr, proc.returncode


def _call_coder(
    plan_path: Path,
    phase: Phase,
    round_num: int,
    prev_review: Optional[dict],
    task_dir: Path,
    tdd: bool = False,
) -> tuple[str, str, int]:
    return _run_claude(
        CODER_MODEL,
        CODER_ALLOWED_TOOLS,
        _compose_system_prompt("coder", tdd),
        _build_coder_prompt(plan_path, phase, round_num, prev_review),
    )


def _call_reviewer(
    plan_path: Path,
    phase: Phase,
    round_num: int,
    task_dir: Path,
    tdd: bool = False,
) -> tuple[str, str, int]:
    return _run_claude(
        REVIEWER_MODEL,
        REVIEWER_ALLOWED_TOOLS,
        _compose_system_prompt("reviewer", tdd),
        _build_reviewer_prompt(plan_path, phase, round_num),
    )


def _is_coder_blocked(coder_stdout: str) -> bool:
    """coder stdout 첫 줄(앞 공백 무시)이 'BLOCKED:' 로 시작하면 True."""
    return coder_stdout.lstrip().startswith("BLOCKED:")


def _write_round_log(
    task_dir: Path,
    phase_num: int,
    round_num: int,
    sections: list[tuple[str, str]],
) -> Path:
    task_dir.mkdir(parents=True, exist_ok=True)
    path = task_dir / f"phase{phase_num}-round{round_num}.log"
    chunks: list[str] = []
    for name, content in sections:
        body = content if content else "(empty)"
        chunks.append(f"### {name}\n{body}")
    path.write_text("\n\n".join(chunks) + "\n", encoding="utf-8")
    return path


def _parse_eval_commands(plan_path: Path) -> list[str]:
    """plan.md 의 '## Evaluate ★' 섹션에서 명령 리스트 파싱. 'none' → []."""
    text = plan_path.read_text(encoding="utf-8")
    m = _EVALUATE_SECTION_RE.search(text)
    if not m:
        return []
    after = text[m.end():]
    commands: list[str] = []
    for line in after.splitlines():
        stripped = line.strip()
        if stripped.startswith("##"):
            break
        if stripped and stripped.lower() != "none":
            commands.append(stripped)
    return commands


def _run_evaluate(commands: list[str], cwd: Path) -> tuple[bool, str]:
    """직렬 실행 + 첫 실패 stop. (success, log_text) 반환."""
    if not commands:
        return (True, "")
    log_parts: list[str] = []
    for cmd in commands:
        proc = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            cwd=cwd,
            shell=False,
            timeout=EVAL_TIMEOUT,
        )
        log_parts.append(
            f"$ {cmd}\nstdout: {proc.stdout}stderr: {proc.stderr}rc: {proc.returncode}"
        )
        if proc.returncode != 0:
            return (False, "\n\n".join(log_parts))
    return (True, "\n\n".join(log_parts))


def _make_eval_review(eval_log: str, round_num: int, max_rounds: int) -> dict:
    """eval 실패를 reviewer 합성 issue dict 로 변환.

    round_num >= max_rounds → status=escalate, 그 외 status=needs-fix.
    """
    status = "escalate" if round_num >= max_rounds else "needs-fix"
    return {
        "status": status,
        "issue_ids": ["eval-fail"],
        "raw": eval_log,
    }


def _append_eval_log(task_dir: Path, phase_num: int, round_num: int, eval_log: str) -> None:
    """eval 결과를 round 로그 파일에 append."""
    task_dir.mkdir(parents=True, exist_ok=True)
    path = task_dir / f"phase{phase_num}-round{round_num}.log"
    body = eval_log if eval_log else "(empty)"
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n\n### Evaluate\n{body}\n")


def run_round(
    phase: Phase,
    round_num: int,
    task_dir: Path,
    plan_path: Path,
    prev_review: Optional[dict] = None,
    tdd: bool = False,
) -> dict:
    """1 라운드(coder + reviewer) 실행. _parse_reviewer_output 결과 dict 반환.

    coder/reviewer 호출이 returncode != 0 이거나 reviewer YAML 파싱 실패 시,
    합성 escalate dict 를 반환해 phase 가 즉시 종료되도록 한다 (사용자 개입 신호).
    """
    coder_out, coder_err, coder_rc = _call_coder(
        plan_path, phase, round_num, prev_review, task_dir, tdd
    )

    if _is_coder_blocked(coder_out):
        _write_round_log(
            task_dir,
            phase.number,
            round_num,
            [
                ("coder stdout", coder_out),
                ("coder stderr", coder_err),
                (f"coder returncode = {coder_rc}", ""),
                ("reviewer", "(skipped: coder BLOCKED)"),
            ],
        )
        return {
            "status": "escalate",
            "issue_ids": ["coder:blocked"],
            "raw": coder_out,
        }

    reviewer_out, reviewer_err, reviewer_rc = _call_reviewer(
        plan_path, phase, round_num, task_dir, tdd
    )
    _write_round_log(
        task_dir,
        phase.number,
        round_num,
        [
            ("coder stdout", coder_out),
            ("coder stderr", coder_err),
            (f"coder returncode = {coder_rc}", ""),
            ("reviewer stdout", reviewer_out),
            ("reviewer stderr", reviewer_err),
            (f"reviewer returncode = {reviewer_rc}", ""),
        ],
    )

    if coder_rc != 0:
        return {
            "status": "escalate",
            "issue_ids": [f"coder:exit-{coder_rc}"],
            "raw": coder_err or coder_out,
        }
    if reviewer_rc != 0:
        return {
            "status": "escalate",
            "issue_ids": [f"reviewer:exit-{reviewer_rc}"],
            "raw": reviewer_err or reviewer_out,
        }
    try:
        return _parse_reviewer_output(reviewer_out)
    except ValueError as e:
        return {
            "status": "escalate",
            "issue_ids": ["reviewer:parse-error"],
            "raw": f"{e}\n\n--- reviewer stdout ---\n{reviewer_out}",
        }


def run_phase(
    phase: Phase,
    task_dir: Path,
    max_rounds: int,
    plan_path: Path,
    tdd: bool = False,
) -> PhaseStatus:
    """phase 1개 실행. round 1..max_rounds 루프 + 3중 안전망 + eval 게이트."""
    prev_issue_ids: set[str] = set()
    prev_review: Optional[dict] = None
    eval_commands = _parse_eval_commands(plan_path)

    for round_num in range(1, max_rounds + 1):
        review = run_round(phase, round_num, task_dir, plan_path, prev_review, tdd)
        outcome, reason = _decide_phase_outcome(
            review, round_num, max_rounds, prev_issue_ids
        )
        if outcome == "passed":
            if eval_commands:
                eval_ok, eval_log = _run_evaluate(eval_commands, cwd=task_dir.parent.parent)
                _append_eval_log(task_dir, phase.number, round_num, eval_log)
                if not eval_ok:
                    review = _make_eval_review(eval_log, round_num, max_rounds)
                    outcome, reason = _decide_phase_outcome(
                        review, round_num, max_rounds, prev_issue_ids
                    )
                    if outcome == "escalated":
                        return PhaseStatus(
                            number=phase.number,
                            name=phase.name,
                            state="escalated",
                            rounds=round_num,
                            last_run_at=_now_iso(),
                            failure_reason=reason,
                        )
                    prev_issue_ids = set(review.get("issue_ids") or [])
                    prev_review = review
                    continue
            return PhaseStatus(
                number=phase.number,
                name=phase.name,
                state="passed",
                rounds=round_num,
                last_run_at=_now_iso(),
            )
        if outcome == "escalated":
            ps = PhaseStatus(
                number=phase.number,
                name=phase.name,
                state="escalated",
                rounds=round_num,
                last_run_at=_now_iso(),
                failure_reason=reason,
            )
            if reason and reason.startswith("repeated issue: "):
                ps.repeated_issue_id = reason[len("repeated issue: ") :]
            return ps
        prev_issue_ids = set(review.get("issue_ids") or [])
        prev_review = review

    return PhaseStatus(
        number=phase.number,
        name=phase.name,
        state="escalated",
        rounds=max_rounds,
        last_run_at=_now_iso(),
        failure_reason="loop exited without decision",
    )


def _check_git_state(cwd: Path) -> tuple[bool, str]:
    """(clean ∧ .git 존재) → (True, ""). 아니면 (False, 차단 메시지)."""
    if not (cwd / ".git").exists():
        return (
            False,
            "git 가드: .git 디렉토리 없음. /nl-setup 으로 git 초기화 후 재실행.",
        )
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if proc.stdout.strip():
        return (
            False,
            (
                "git 가드: working tree 가 dirty. /nl-generate 는 clean tree 에서만 동작.\n"
                "변경 사항 처리 후 재실행:\n"
                "  git status\n"
                '  git add ... && git commit -m "..."  또는  git stash'
            ),
        )
    return (True, "")


def _ensure_feature_branch(task_name: str, cwd: Path) -> str:
    """현재 branch 가 main/master 면 feat/<task_name> 생성·체크아웃. 반환 = 사용 중 branch."""
    proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    current = proc.stdout.strip()
    if current in ("main", "master"):
        branch = f"feat/{task_name}"
        subprocess.run(
            ["git", "checkout", "-b", branch],
            capture_output=True,
            text=True,
            cwd=cwd,
            check=True,
        )
        return branch
    return current


def _commit_phase(task_name: str, phase: Phase, cwd: Path) -> str:
    """git add -A + commit. 메시지 = 'feat(<task>): phase-<N> <name>'. 반환 = commit hash."""
    subprocess.run(
        ["git", "add", "-A"],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=True,
    )
    msg = f"feat({task_name}): phase-{phase.number} {phase.name}"
    subprocess.run(
        ["git", "commit", "-m", msg],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=True,
    )
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return proc.stdout.strip()


def _render_failure_report(phase: Phase, last_good_hash: str, reason: str) -> str:
    """stderr 출력용 실패 리포트. reset 명령 안내 포함, 자동 reset 은 안 함."""
    return (
        f"phase {phase.number} ({phase.name}) 실패: {reason}\n"
        f"last_good_commit: {last_good_hash}\n"
        f"복원 명령 (필요 시): git reset --hard {last_good_hash}"
    )


_CHANGED_FILE_RE = re.compile(r"^\s*-\s*\[(신규|수정|삭제)\]")


def _count_changed_files(plan_path: Path) -> int:
    """plan 의 `## 변경 파일` 섹션에서 `[신규|수정|삭제]` 로 시작하는 항목 수."""
    text = plan_path.read_text(encoding="utf-8")
    section_re = re.compile(r"^##\s+변경\s*파일\s*$", re.MULTILINE)
    m = section_re.search(text)
    if not m:
        return 0
    after = text[m.end():]
    count = 0
    for line in after.splitlines():
        if re.match(r"^##", line):
            break
        if _CHANGED_FILE_RE.match(line):
            count += 1
    return count


def run_inline(plan_path: Path, phases: list[Phase]) -> int:
    """--inline 분기 처리. 0 / EXIT_CODE_INLINE_INVALID 반환.

    - phases 길이 != 1 → stderr 경고 + 5 반환
    - _count_changed_files != 1 → stderr 경고 + 5 반환
    - 통과 시 stdout 에 'INLINE: ...' 한 줄 + plan/phase/파일 요약 출력 후 0 반환
    """
    if len(phases) != 1:
        print(
            f"--inline 조건 불충족: phase 수 {len(phases)} (1이어야 함)",
            file=sys.stderr,
        )
        return EXIT_CODE_INLINE_INVALID

    changed = _count_changed_files(plan_path)
    if changed != 1:
        print(
            f"--inline 조건 불충족: 변경 파일 수 {changed} (1이어야 함)",
            file=sys.stderr,
        )
        return EXIT_CODE_INLINE_INVALID

    phase = phases[0]
    print(f"INLINE: 메인이 직접 작업")
    print(f"plan: {plan_path}")
    print(f"phase: {phase.number} ({phase.name})")
    print(f"scope: {phase.scope}")
    return 0


def _select_next_phase(status: RunStatus) -> Optional[PhaseStatus]:
    for p in status.phases:
        if p.state in ("pending", "in_progress"):
            return p
    return None


def _print_summary(status: RunStatus) -> None:
    print(f"# run_phases 요약 — task: {status.task_name}")
    print(f"plan: {status.plan_path}")
    print(f"max_rounds: {status.max_rounds}, schema_version: {status.schema_version}")
    print(f"updated_at: {status.updated_at}")
    print()
    for p in status.phases:
        print(f"  Phase {p.number} {p.name}: {p.state} (rounds={p.rounds})")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    plan_path: Path = args.plan_path
    if not plan_path.exists():
        print(f"plan 파일 없음: {plan_path}", file=sys.stderr)
        return 2

    task_dir: Path = args.task_dir if args.task_dir is not None else task_dir_for(plan_path)
    phases = parse_phases(plan_path)
    by_number = {p.number: p for p in phases}

    if args.tdd and args.inline:
        print(
            "경고: --tdd 와 --inline 동시 사용 — --inline 만 적용하고 --tdd 는 무시함",
            file=sys.stderr,
        )

    if args.inline:
        return run_inline(plan_path, phases)

    cwd = Path.cwd()
    ok, msg = _check_git_state(cwd)
    if not ok:
        print(msg, file=sys.stderr)
        return EXIT_CODE_GIT_GUARD
    task_name = task_dir.name
    _ensure_feature_branch(task_name, cwd)

    if args.resume:
        status = load_status(task_dir)
        if status is None:
            print(f"--resume 인데 status.json 없음: {task_dir}", file=sys.stderr)
            return 2
    else:
        status = init_status(plan_path, phases, args.max_rounds)
        save_status(task_dir, status)

    last_good_commit = ""
    while True:
        next_status = _select_next_phase(status)
        if next_status is None:
            _print_summary(status)
            return 0

        phase = by_number.get(next_status.number)
        if phase is None:
            print(
                f"plan/status 불일치: phase {next_status.number} 가 plan 에 없음",
                file=sys.stderr,
            )
            return 3

        unmet = [
            d for d in phase.depends_on
            if (s := next((ps for ps in status.phases if ps.number == d), None)) is None
            or s.state != "passed"
        ]
        if unmet:
            print(f"phase {phase.number} 의존 미완료: {unmet}", file=sys.stderr)
            return 4

        next_status.state = "in_progress"
        next_status.last_run_at = _now_iso()
        status.current_phase = next_status.number
        save_status(task_dir, status)

        result = run_phase(phase, task_dir, status.max_rounds, plan_path, tdd=args.tdd)
        for i, ps in enumerate(status.phases):
            if ps.number == result.number:
                status.phases[i] = result
                break
        save_status(task_dir, status)

        if result.state == "passed":
            last_good_commit = _commit_phase(task_name, phase, cwd)

        if result.state == "escalated":
            print(
                _render_failure_report(phase, last_good_commit, result.failure_reason or ""),
                file=sys.stderr,
            )
            _print_summary(status)
            return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
