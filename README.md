# nerdlab-harness

특정 워크플로우(헤드리스 격리 + 단계 분리 + 강제 입출력)를 따르려는 사람을 위한 미니멀 Claude Code 하네스. **범용성 X** — 자유로운 즉흥 코딩 도우미가 필요하면 다른 SKILL/플러그인 사용.

5단계 모델 `Clarify → Context Gather → Plan → Generate → Evaluate` 를 강제해 매 호출마다 같은 품질이 나오게 한다. 범용 하네스(gstack/superpowers)의 토큰 폭발 없이 핵심만 자동화.

## 설계 철학 (한 줄씩)

1. **헤드리스 격리** — 각 단계는 `claude -p` 헤드리스 세션, 메인은 호출자 + 결과 전달자 (clarify / Phase A / eval 만 명시적 예외)
2. **모델 분리** — 의사결정(기획·검증)은 Opus, 실행(구현)은 Sonnet
3. **개발·검증 루프** — coder ↔ reviewer 한 사이클, 종료 조건 3중 안전망
4. **phase 직렬 실행** — 큰 작업은 phase 로 분해, python script 가 직렬 오케스트레이션 (메인 부담 ↓)
5. **지연 로딩 + 단일 진실 출처** — 두꺼운 명세는 `docs/spec/` 6개 파일에 두고 SKILL/prompt 는 링크만
6. **강제하는 것 7항목** — plan-template ★ 12개 / Clarify ★ 6개 / Context Gather Phase A+B / reviewer YAML / Evaluate 게이트 / git 가드 / 헤드리스 통일 ([philosophy.md §6](docs/philosophy.md))

자세한 내용은 [docs/philosophy.md](docs/philosophy.md).

## 디렉토리 구조

```
nerdlab-harness/
├── .claude-plugin/plugin.json   # 플러그인 메타데이터
├── skills/                      # 슬래시 명령 (5종)
│   ├── nl-setup/                # /nl-setup    — 1회성 프로젝트 부트스트랩 (메인 직접)
│   ├── nl-plan/                 # /nl-plan     — Clarify → Context → planner (Opus)
│   ├── nl-generate/             # /nl-generate — phase 직렬 + coder↔reviewer 루프 + Evaluate + git 가드
│   ├── nl-review/               # /nl-review   — 독립 진입점 (PR/ad-hoc 검토)
│   └── nl-ship/                 # /nl-ship     — 배포 (placeholder, 다음 트랙)
├── prompts/                     # 헤드리스 세션 시스템 프롬프트 (6종)
│   ├── planner.md               # Opus — 기획
│   ├── coder.md / coder_tdd.md  # Sonnet — 구현 (--tdd 변형)
│   ├── reviewer.md / reviewer_tdd.md  # Opus — 검증 (--tdd 변형)
│   └── explorer.md              # Sonnet — Context Gather Phase B
├── scripts/
│   ├── run_phases.py            # phase 직렬 + 루프 + 옵션 + git 가드 + Evaluate (~940줄)
│   └── validate_plan.py         # plan-template ★ 12개 섹션 검증 (~196줄)
├── docs/
│   ├── philosophy.md            # 설계 철학 6 섹션 + 강제하는 것 7항목 표
│   └── spec/                    # 단일 진실 출처 (6종)
│       ├── plan-template.md     # planner 출력 형식 (★ 12)
│       ├── reviewer-output.md   # reviewer YAML 스키마
│       ├── clarify-protocol.md  # 입력 ★ 6개 + 라운드 룰
│       ├── context-protocol.md  # Phase A(결정적) + Phase B(헤드리스)
│       ├── git-guard-protocol.md # /nl-generate 진입 가드
│       └── setup-protocol.md    # /nl-setup 5단계
├── templates/                   # /nl-setup 가 복사하는 표준 메타 문서
│   ├── CLAUDE.md
│   ├── docs/architecture.md
│   ├── docs/coding-conventions.md
│   ├── docs/adr/0000-template.md
│   └── docs/prd.md
├── tasks/                       # plan + 실행 기록 (본 저장소는 비움 — .gitignore)
│   └── <task-name>/
│       ├── plan.md              # planner 출력
│       ├── status.json          # 전체 진척
│       └── phase{N}-round{M}.log
├── tests/                       # unittest (run_phases 90 + validate_plan 36 = 126 PASS)
└── TODO.md                      # 작업 시계열 기록
```

## 파이프라인

```
[1회성]   /nl-setup ──▶ git init + CLAUDE.md / architecture / ADR / coding-conventions / [opt] PRD
                       (메인 직접 + AskUserQuestion)

[매 작업] 요구사항 ──▶ /nl-plan ──▶ tasks/<task>/plan.md ──▶ /nl-generate ──▶ /nl-ship
                       Clarify(메인)                       run_phases.py:        (placeholder)
                       Context Gather                      coder ↔ reviewer
                       planner Opus                        + Evaluate + git 가드
                                                           Sonnet ↔ Opus

[독립]    /nl-review ─ build 외부 진입점 (PR/ad-hoc)
                       reviewer Opus
```

| 명령 | 역할 | 모델 | 출력 |
|------|------|------|------|
| `/nl-setup` | 1회성 프로젝트 부트스트랩 (git init + 표준 메타 문서 5종) | — (메인 직접) | `CLAUDE.md` / `docs/architecture.md` / `docs/coding-conventions.md` / `docs/adr/0000-template.md` / `[docs/prd.md]` |
| `/nl-plan` | 요구사항 → Clarify ★6 + Context Gather → plan ★12 | Opus (planner) | `tasks/<task-name>/plan.md` |
| `/nl-generate` | plan → phase 직렬 + 구현+검증 루프 + Evaluate + git 가드 (`--tdd` / `--inline` / `--resume`) | Sonnet ↔ Opus | 변경 파일 + `tasks/<task-name>/status.json` + 자동 phase commit |
| `/nl-review` | 독립 코드 리뷰 (build 외부, plan optional) | Opus (reviewer) | YAML 결함 리스트 |
| `/nl-ship` | git 배포 워크플로우 (commit / push / PR) | — | (placeholder, 다음 트랙) |

## /nl-generate 루프 종료 조건 (3중 안전망)

phase 단위:
1. **정상**: phase reviewer `status: ok` → 다음 phase
2. **라운드 한도**: 한 phase 내 최대 3 라운드 후 phase escalate
3. **동일 이슈 반복**: 같은 issue id 가 2 라운드 연속 → phase escalate

전체 단위: 어떤 phase 가 escalate → script 즉시 종료, 후속 phase 미실행.

상세 스키마: [docs/spec/reviewer-output.md](docs/spec/reviewer-output.md).

## git 가드 (`/nl-generate`)

`/nl-generate` 는 `--inline` 이 아닌 한 진입 직후 git 상태를 두 단계로 검증한다.

1. `.git` 미존재 → exit 6 + `/nl-setup` 안내.
2. working tree dirty → exit 6 + `git stash` 또는 commit 안내.

통과하면 현재 branch 가 `main`/`master` 일 때 `feat/<task-name>` 을 자동 생성·체크아웃한다. 각 phase 가 통과(`passed`)할 때마다 `feat(<task>): phase-<N> <name>` 형식으로 자동 commit 된다. phase 가 escalate 되면 commit 없이 `git reset --hard <last_good_commit>` 안내만 stderr 에 출력하고 사용자 판단에 맡긴다 (자동 reset 없음).

## 설치

이 저장소를 clone 한 디렉토리에서 `--plugin-dir` 로 Claude Code 를 띄운다.

```bash
git clone git@github.com:nerdlab-logan/nerdlab-cc-harness.git ~/Developer/own/cc-marketplace/nerdlab-harness
cd ~/Developer/own/cc-marketplace/nerdlab-harness
claude --plugin-dir .
```

세션 안에서 슬래시 명령이 `/nerdlab-harness:nl-setup`, `/nerdlab-harness:nl-plan`, `/nerdlab-harness:nl-generate`, `/nerdlab-harness:nl-review`, `/nerdlab-harness:nl-ship` 형식으로 노출된다.

자주 쓰면 shell alias 권장:

```bash
alias clh='claude --plugin-dir ~/Developer/own/cc-marketplace/nerdlab-harness'
```

> 헤드리스 통일 구조라 `~/.claude/agents/` 또는 `~/.claude/skills/` 에 별도 등록할 파일은 없다.

## 사용 흐름 — 처음부터 끝까지

신규 프로젝트:

```bash
mkdir my-project && cd my-project
clh                                # nerdlab-harness 플러그인 로드
> /nerdlab-harness:nl-setup        # git init + CLAUDE.md / architecture / ADR / coding-conventions / [PRD]
> /nerdlab-harness:nl-plan "X 기능 추가"
                                   # 메인이 Clarify ★6 묶음 질문 (모호하면 최대 2 라운드)
                                   # → Context Gather Phase A(git ls-files / grep) + Phase B(헤드리스 익스플로러)
                                   # → planner 헤드리스 호출 → tasks/x-feature/plan.md
> /nerdlab-harness:nl-generate tasks/x-feature/plan.md
                                   # git 가드 (clean tree + .git 존재 확인)
                                   # → main 이면 feat/x-feature 자동 분기
                                   # → phase 1 coder ↔ reviewer 루프 → Evaluate(typecheck/test) → 자동 commit
                                   # → phase 2... → 모든 phase passed
> /nerdlab-harness:nl-review       # 필요 시 독립 검토
```

옵션:

- `/nerdlab-harness:nl-generate <plan> --tdd` — coder/reviewer 가 TDD 사이클 강제
- `/nerdlab-harness:nl-generate <plan> --inline` — phase 1 짜리 작은 작업은 메인 직접 (헤드리스 오버헤드 회피)
- `/nerdlab-harness:nl-generate <plan> --resume` — 중단된 phase 부터 재개

## tasks/ 디렉토리 정책

| 위치 | 정책 | 이유 |
|------|------|------|
| **본 저장소 (nerdlab-harness)** | `tasks/*` 를 `.gitignore`, `tasks/.gitkeep` 만 commit | 하네스 본체만 관리. 작업 부산물은 보존 불필요. |
| **하네스를 사용하는 프로젝트** | `tasks/` 전체 commit 권장 | plan(의사결정)과 실행 이력(phase 로그)을 PR/리뷰에서 추적 |
