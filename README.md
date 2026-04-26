# nerdlab-harness

사용자 워크플로우에 맞춘 미니멀 Claude Code 하네스. `기획 → (phase 직렬 + 개발+검증 루프) → 배포` 흐름만 추려서, 범용 하네스(gstack/superpowers)의 토큰 폭발 없이 핵심만 자동화한다.

## 설계 철학 (한 줄씩)

1. **헤드리스 격리** — 각 단계는 `claude -p` 헤드리스 세션, 메인은 호출자 + 결과 전달자
2. **모델 분리** — 의사결정(기획·검증)은 Opus, 실행(구현)은 Sonnet
3. **개발·검증 루프** — coder ↔ reviewer 한 사이클, 종료 조건 3중 안전망
4. **phase 직렬 실행** — 큰 작업은 phase 로 분해, python script 가 직렬 오케스트레이션 (메인 부담 ↓)
5. **지연 로딩** — 두꺼운 명세는 `docs/spec/` 단일 진실 출처에 두고 SKILL/prompt 는 링크만

자세한 내용은 [docs/philosophy.md](docs/philosophy.md).

## 디렉토리 구조

```
nerdlab-harness/
├── .claude-plugin/plugin.json   # 플러그인 메타데이터
├── skills/                      # 슬래시 명령
│   ├── nl-setup/                # /nl-setup    — 1회성 프로젝트 부트스트랩
│   ├── nl-plan/                 # /nl-plan     — 기획 (planner Opus)
│   ├── nl-generate/             # /nl-generate — phase 직렬 + 개발+검증 루프
│   ├── nl-review/               # /nl-review   — 독립 진입점 (PR/ad-hoc 검토)
│   └── nl-ship/                 # /nl-ship     — 배포 (git)
├── prompts/                     # 헤드리스 세션 시스템 프롬프트
│   ├── planner.md               # Opus
│   ├── coder.md                 # Sonnet
│   └── reviewer.md              # Opus
├── scripts/
│   └── run_phases.py            # phase 직렬 실행 + 상태 관리 (다음 세션 본구현)
├── hooks/                       # (placeholder)
├── docs/
│   ├── philosophy.md            # 설계 결정 기록
│   └── spec/
│       ├── plan-template.md     # planner 출력 형식
│       └── reviewer-output.md   # reviewer 출력 스키마
├── tasks/                       # plan + 실행 기록 저장 (본 저장소는 비움 — .gitignore)
│   └── <task-name>/
│       ├── plan.md              # planner 출력
│       ├── status.json          # 전체 진척
│       ├── phase{N}.status.json # phase 별 상태
│       └── phase{N}-round{M}.log
└── README.md
```

## 파이프라인

```
요구사항 ──▶ /nl-plan ──▶ tasks/<task-name>/plan.md ──▶ /nl-generate ──▶ /nl-ship
            (planner)                                  (run_phases.py        (git)
            Opus                                        + coder ↔ reviewer)  Sonnet/Haiku
                                                        Sonnet ↔ Opus

                              /nl-review ─ 독립 진입점 (build 외부, PR/ad-hoc)
                              (reviewer Opus)
```

| 명령 | 역할 | 모델 | 출력 |
|------|------|------|------|
| `/nl-setup` | 1회성 프로젝트 부트스트랩 (git init + 표준 메타 문서) | — (메인 직접) | CLAUDE.md / architecture / ADR / prd |
| `/nl-plan` | 요구사항 → 구체적 plan 생성 | Opus (planner) | `tasks/<task-name>/plan.md` |
| `/nl-generate` | plan → phase 직렬 + 구현+검증 루프 (`--tdd` / `--inline` / `--resume`) | Sonnet ↔ Opus | 변경 파일 + `tasks/<task-name>/status.json` |
| `/nl-review` | 독립 코드 리뷰 (build 외부) | Opus (reviewer) | 결함 리스트 |
| `/nl-ship` | git 워크플로우 (commit → develop → main) | Sonnet/Haiku | 커밋·PR |

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
git clone https://github.com/nerdlab/nerdlab-harness.git ~/Developer/own/cc-marketplace/nerdlab-harness
cd ~/Developer/own/cc-marketplace/nerdlab-harness
claude --plugin-dir .
```

세션 안에서 슬래시 명령이 `/nerdlab-harness:nl-setup`, `/nerdlab-harness:nl-plan`, `/nerdlab-harness:nl-generate`, `/nerdlab-harness:nl-review`, `/nerdlab-harness:nl-ship` 형식으로 노출된다.

자주 쓰면 shell alias 권장:

```bash
alias clh='claude --plugin-dir ~/Developer/own/cc-marketplace/nerdlab-harness'
```

> 헤드리스 통일 구조라 `~/.claude/agents/` 또는 `~/.claude/skills/` 에 별도 등록할 파일은 없다. 이전 버전에서 사용하던 `~/.claude/skills/nl-*` symlink 가 남아 있다면 제거.

## tasks/ 디렉토리 정책

| 위치 | 정책 | 이유 |
|------|------|------|
| **본 저장소 (nerdlab-harness)** | `tasks/*` 를 `.gitignore`, `tasks/.gitkeep` 만 commit | 하네스 본체만 관리. 작업 부산물은 보존 불필요. |
| **하네스를 사용하는 프로젝트** | `tasks/` 전체 commit 권장 | plan(의사결정)과 실행 이력(phase 로그)을 PR/리뷰에서 추적 |

## 로드맵

- [x] 4단계 → 3+1단계 흐름 결정 + spec 명세 분리 (2026-04-26)
- [x] `nl-plan` SKILL.md + `planner.md` 본구현 (2026-04-26)
- [x] `docs/spec/plan-template.md` + `docs/spec/reviewer-output.md` (2026-04-26)
- [x] `tasks/<task-name>/` 통합 디렉토리 + `.gitignore` 정책 (2026-04-26)
- [x] plan-template `Phase 분해` 섹션 추가 + planner 휴리스틱 (2026-04-26)
- [x] `reviewer.md` 본구현 + `nl-review` SKILL.md (plan 컨텍스트 optional) (2026-04-26)
- [x] `scripts/run_phases.py` + `coder.md` + `nl-generate` SKILL.md 본구현 (2026-04-26)
- [x] `--tdd` / `--inline` / `BLOCKED:` escalate / reviewer phase 슬라이스 옵션 (2026-04-26)
- [x] plugin 정공법(`--plugin-dir`) 셋업 (2026-04-26)
- [x] `nl-setup` SKILL.md + `setup-protocol.md` + `templates/` 5종 (2026-04-26)
- [ ] (A) plan 이전 요구사항 정리 단계 (`nl-spec` vs plan self-review)
- [ ] (B) `nl-generate` 의 git 강제 + worktree
- [ ] (C) `docs/philosophy.md` 강제성 섹션 명문화
- [ ] `nl-ship` 본구현 ((A)(B)(C) 정착 후)
- [ ] hooks 추가 (`dangerous-cmd-guard` 우선)
- [ ] marketplace 공개 검토
