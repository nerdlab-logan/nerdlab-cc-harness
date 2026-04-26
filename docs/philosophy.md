# 설계 철학

## 1. 모델 분배

사람의 분업 패턴(시니어 설계·시니어 리뷰 vs 미들 구현)을 모델 분배에 매핑한다.

| 단계 | 격리 방식 | 모델 | 근거 |
|------|----------|------|------|
| 기획 | `claude -p` 헤드리스 (`prompts/planner.md`) | Opus | 아키텍처 의사결정·엣지 케이스 발견에 추론력 필수. plan 품질이 전체 파이프라인 천장. |
| 구현 | `claude -p` 헤드리스 (`prompts/coder.md`, `run_phases.py` 가 호출) | Sonnet | 구체화된 plan 을 충실히 따라가는 작업. 비용·속도 효율. |
| 검증 | `claude -p` 헤드리스 (`prompts/reviewer.md`) | Opus | 결함 발견("있어야 할 게 없는 것")은 패턴 매칭이 안 됨. |
| 배포 | 메인 + 기존 skill 재사용 | Sonnet/Haiku | git 워크플로우는 단순 작업. |

핵심:
- "의사결정" 단계(기획·검증)는 Opus, "실행" 단계(구현)는 Sonnet
- 모든 단계를 헤드리스 세션으로 격리 — 메인은 호출자 + 결과 전달자
- 메인 컨텍스트가 깨끗해야 다음 단계의 토큰이 절약됨

## 2. 개발·검증은 한 사이클

`coder` ↔ `reviewer` 는 별도 단계가 아니라 같은 사이클의 두 페이즈다. 한 번 짜고 한 번 검토 받고 끝내는 모델은 시니어 워크플로우 현실과 안 맞는다 — 실제로 개발자는 짜다가 self-test/review 굴리며 고친다.

루프는 `/nl-generate` 가 오케스트레이션하며 종료 조건은 **3중 안전망**:

1. **정상**: reviewer `status: ok` → 즉시 종료
2. **라운드 한도**: 최대 3 라운드 후 강제 종료, 결과 보고
3. **동일 이슈 반복**: 같은 issue id 가 2 라운드 연속 등장 시 escalate (사용자 개입)

`/nl-review` 는 build 외부에서도 reviewer 를 단독 호출할 수 있게 하는 별도 진입점 (PR 검토, ad-hoc sanity 체크 용). 같은 `prompts/reviewer.md` 시스템 프롬프트를 두 진입점이 공유한다.

스키마 상세: [spec/reviewer-output.md](spec/reviewer-output.md).

## 3. 헤드리스 격리

서브에이전트 메커니즘 대신 `claude -p` 헤드리스 세션으로 단계를 분리한다.

이유:
1. 모든 단계가 같은 호출 패턴 (`claude -p --model X --append-system-prompt ...`) → mental model 1개
2. 사람이 동일 명령으로 직접 재현 가능 → 디버그 쉬움
3. 코드 변경 노이즈(긴 diff, 시행착오) 가 메인에 쌓이지 않음 — stdout 압축본만 흐름
4. 결과는 plan/review 파일로 명확히 핸드오프 → 세션 재시작 시에도 재사용
5. `run_phases.py` 같은 파이썬 스크립트가 phase 직렬 + round 루프를 직접 통제 가능 (서브에이전트는 스크립트가 호출 불가)

예외: 한두 줄 수정처럼 작은 변경은 헤드리스 호출 오버헤드(프로세스 시작 ~수백 ms)가 더 크다. `/nl-generate --inline` 으로 메인 직접 작업도 가능.

### Clarify 예외

`/nl-plan` 의 clarify 단계는 **메인 세션이 직접 수행한다**. 헤드리스 통일 원칙의 명시적 예외.

이유:
1. clarify 의 본질이 사용자 인터랙션 (`AskUserQuestion`) — 헤드리스 single-shot 응답 모델과 충돌
2. 시나리오 A (이미 N턴 대화로 요구사항 정리됨) 에서 메인 세션 컨텍스트가 핵심 가치 — 헤드리스로 넘기면 압축 손실
3. 라운드 왕복마다 헤드리스 재호출 = 3자 (메인↔사용자↔헤드리스) 비효율

명세는 [spec/clarify-protocol.md](spec/clarify-protocol.md). planner / coder / reviewer 는 헤드리스 통일 그대로.

## 4. 지연 로딩 + 단일 진실의 출처

- SKILL.md 는 짧게 유지 (50줄 이내 목표)
- git 컨벤션 등 두꺼운 외부 문서는 SKILL.md 에 **링크만** 두고 `Read` 도구로 필요할 때만 가져온다
- `~/.claude/docs/git/*` 의 기존 문서를 참조 (중복 작성 금지)
- plan 출력 형식 / reviewer 스키마 같은 **하네스 내부 명세는 `docs/spec/` 에 단일 진실의 출처**로 둔다. SKILL/agent 는 링크와 짧은 요약만 가지며, 형식 변경 시 `docs/spec/` 만 수정하면 모든 단계가 자동 반영된다.

## 5. 새 skill/prompt 추가 시 체크리스트

- [ ] 어느 단계에 속하는가? (기획 / 구현·검증 / 배포)
- [ ] 모델 분배 표에 맞게 SKILL 의 `claude -p --model ...` 인자를 지정했는가?
- [ ] SKILL.md 가 50줄 이내인가? 두꺼운 문서는 `docs/spec/` 또는 외부 링크로 두었는가?
- [ ] 시스템 프롬프트(`prompts/*.md`) 에 "stdout 출력은 정확히 X줄, 추가 텍스트 금지" 가 명시되어 있는가? (메인 컨텍스트 청결)
- [ ] 기존 자산(`commit-message`, `daily-report`, `~/.claude/docs/git/*`) 과 중복되지 않는가?

## 6. 이 하네스가 강제하는 것

이 하네스는 **범용성 X** — 특정 워크플로우(헤드리스 격리 + 단계 분리 + 강제 입출력)를 따르려는 사람을 위한 도구다. 자유로운 즉흥 코딩 도우미가 필요하면 다른 SKILL/플러그인을 쓰는 편이 빠르다. 강제는 사람의 자유를 줄이는 게 아니라 흐름이 깨질 가능성을 차단해 매 호출마다 같은 품질이 나오게 한다.

아래 7개 항목을 강제하며, 위반은 진입 차단 / 합성 escalate / exit 분기 / 사용자 통지로 즉시 가시화된다.

| # | 강제 항목 | 강제 위치 | 위반 시 |
|---|----------|-----------|---------|
| 1 | plan-template 12개 ★ 섹션 채우기 (목적/배경/핵심 변경/수용 기준/시그니처/변경 파일/데이터 흐름/안 할 것/트레이드오프/Phase 분해/Context/Evaluate) | `scripts/validate_plan.py` | `/nl-plan` 단계 4 사용자 통지 (진행은 차단 X) |
| 2 | Clarify 입력 ★ 6개 (목적/입력/출력/제약/완료조건/안 할 것) | 메인 세션 직접 (헤드리스 예외) | `/nl-plan` planner 호출 차단 |
| 3 | Context Gather Phase A(결정적 git 명령) + Phase B(헤드리스 익스플로러) | `/nl-plan` 단계 2 | plan `## Context` 섹션 누락 → reviewer 지적 |
| 4 | reviewer YAML 스키마 (status / issues / severity / id) | `prompts/reviewer.md` | parse 실패 → 합성 escalate dict |
| 5 | Evaluate 게이트 (typecheck / lint / test / build 직렬, 첫 실패 stop) | `scripts/run_phases.py:_run_evaluate` | reviewer 합성 issue → coder 재호출 |
| 6 | git 가드 (clean tree / `.git` 존재 / main 자동 `feat/<task>` 분기 / phase passed 자동 commit) | `scripts/run_phases.py:_check_git_state` 등 | exit 6 + `/nl-generate` 진입 차단 |
| 7 | 헤드리스 통일 (`claude -p`) — clarify / Phase A / eval 만 명시적 예외 | 모든 `prompts/*.md` + SKILL `Bash` 호출 패턴 | — (설계 철학, 자동 가드 X) |

각 항목의 단일 진실 출처:

- 1·2·3·4·5·6 — `docs/spec/{plan-template, clarify-protocol, context-protocol, reviewer-output, git-guard-protocol}.md`
- 7 — 본 문서 §3 헤드리스 격리

강제 항목을 추가/완화/제거할 때는 본 표 + 해당 spec 파일을 함께 갱신한다. SKILL/prompt 본문에 강제 룰을 중복 박지 않는다 (단일 진실 출처 원칙, §4).
