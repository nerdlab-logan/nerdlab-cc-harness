---
name: nl-plan
description: 사용자 요구사항을 clarify 게이트(메인) → planner 헤드리스(Opus) 로 보내 plan 파일 하나를 생성한다. plan 은 tasks/<task-name>/plan.md 에 저장되며 nl-generate / nl-review 가 이를 그대로 소비한다.
---

# /nl-plan

흐름: **clarify → context gather → plan 생성 → ★ 섹션 검증**.

## 사용

```
/nl-plan <요구사항>
/nl-plan --tdd <요구사항>     # TDD 강제
/nl-plan                      # 인자 없이 — 이번 세션 대화에서 요구사항 추출
```

## 단계

### 1. Clarify (메인 직접)

`docs/spec/clarify-protocol.md` 절차 그대로 수행. 핵심: 입력 ★ 6개(목적·입력·출력·제약·완료조건·안 할 것) 추출, 빈/모호 시 `AskUserQuestion` 한 라운드 묶음(최대 2 라운드), 확정 후 사용자 요약 확인(스킵 불가). 확정 ★ 요약 텍스트를 다음 단계 user prompt 로 전달.

헤드리스 X — 세션 맥락 활용이 본질. 자세한 룰·안티패턴은 spec 참조.

### 2. Context Gather (메인 직접 + 헤드리스)

`docs/spec/context-protocol.md` 절차 그대로 수행. 흐름:

1. **빈 코드 자동 감지** — `.git` 부재 또는 `git ls-files | wc -l` 가 0이면 `CONTEXT="none (empty codebase)"` 로 스킵, 단계 3으로.
2. **Phase A (메인 직접 결정적 스캔)** — `git ls-files`, 디렉토리 분포, 키워드 grep. 5~10줄로 정리해 `PHASE_A_SUMMARY` 에 보관.
3. **Phase B (헤드리스 익스플로러)**:
   ```bash
   CONTEXT=$(claude -p \
     --allowed-tools "Read,Grep,Glob" \
     --append-system-prompt "$(cat /Users/tiredman/Developer/own/cc-marketplace/nerdlab-harness/prompts/explorer.md)" \
     "<clarify ★ 요약>

   ## Phase A 결과
   ${PHASE_A_SUMMARY}")
   ```
   stdout 으로 `### 영향 파일 ★` / `### 관련 시그니처 ★` / `### 기존 패턴 ★` 세 섹션 수신.

단계 3 완료 후 메인이 plan.md 의 `## 11. Context ★` 섹션에 `$CONTEXT` 를 기록 (없으면 append, 재호출 시 덮어쓰기).

### 3. Planner 헤드리스 호출

확정 ★ 요약 + (있으면) `--tdd` 플래그를 user prompt 로 합성:

```bash
claude -p \
  --model opus \
  --allowed-tools "Read,Write,Glob,Grep,WebFetch" \
  --append-system-prompt "$(cat /Users/tiredman/Developer/own/cc-marketplace/nerdlab-harness/prompts/planner.md)" \
  "<★ 요약 + 원본 요구사항 + TDD 강제 플래그>"
```

stdout 5줄 (`plan: ...` ~ `TDD: ...`) 만 받는다.

### 4. ★ 섹션 검증 (메인)

```bash
python scripts/validate_plan.py tasks/<task-name>/plan.md
```

결과를 사용자에게 그대로 전달:
- `★ 섹션 검증 통과` → 5단계로
- `빈 ★ 섹션: ...` → 어느 섹션이 비었는지 통지하고 planner 재호출 / plan 직접 편집 / 무시 중 선택 안내 (자동 차단 X)

★ 섹션 작성 가이드(특히 `## 12. Evaluate ★` 채우는 법)는 `docs/spec/plan-template.md` 참조.

### 5. 결과 안내

stdout 5줄 그대로 보여주고 다음 단계 한 줄 안내:
- 만족 → `/nl-generate tasks/<task-name>/plan.md`
- 수정 → plan 파일 편집 또는 `/nl-plan` 재호출

## 출력 형식의 단일 진실 출처

`prompts/planner.md` 의 "출력 형식" + `docs/spec/plan-template.md`. 형식 변경 시 그 두 파일만 수정.

## 메인 컨텍스트 청결

clarify 사용자 왕복은 메인에 남지만 planner 헤드리스 시행착오는 stdout 5줄로 압축돼 흐른다. ★ 섹션 검증 결과는 통과/실패 한 줄만 보고.
