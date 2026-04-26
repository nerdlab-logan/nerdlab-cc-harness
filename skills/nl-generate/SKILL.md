---
name: nl-generate
description: plan 파일을 받아 phase 직렬 실행 + coder/reviewer 루프(개발+검증)를 수행한다. scripts/run_phases.py 에 위임. --tdd / --inline / --resume 옵션.
---

# /nl-generate

`nl-plan` 이 만든 plan 파일을 받아 `scripts/run_phases.py` 에 위임한다. script 가 plan 의 `Phase 분해` 섹션을 파싱하여 phase 직렬로 coder(Sonnet) ↔ reviewer(Opus) 루프를 돌린다.

## 사용

```
/nl-generate <plan-path>
/nl-generate --tdd <plan-path>      # TDD 강제 (plan 의 TDD 필드 무시하고 yes)
/nl-generate --inline <plan-path>   # 메인에서 직접 작업 (script 미사용, phase 1개 작업 전용)
/nl-generate --resume <plan-path>   # 마지막 실패 phase 부터 이어서
```

예: `/nl-generate tasks/add-login-rate-limit/plan.md`

## 동작

`Bash` 도구로 다음을 실행한다 (`<plan-path>` 는 사용자가 지정한 plan 파일 경로, 옵션은 그대로 패스스루):

```bash
python /Users/tiredman/Developer/own/cc-marketplace/nerdlab-harness/scripts/run_phases.py \
  "<plan-path>" [--tdd] [--inline] [--resume]
```

호출이 끝나면 script 의 stdout 요약 블록만 사용자에게 그대로 전달한다. **메인은 stdout 외 추가 분석·요약을 붙이지 않는다.**

## 출력 처리

script stdout 의 요약 블록(phase 별 status + 전체 결과)을 그대로 사용자에게 전달한다.
종료 코드가 0 이 아닐 때는 stderr 내용을 함께 보여 주고, 아래 "종료 코드" 표를 참고해 원인을 한 줄로 안내한다.

## 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 정상 — 모든 phase ok |
| 1 | phase escalated — 사용자 개입 필요 |
| 2 | plan 파일 없음, 또는 `--resume` 시 status.json 없음 |
| 3 | plan 과 status.json 불일치 (plan 이 수정됨) |
| 4 | 선행 의존 phase 미완료 |
| 6 | git 가드 차단 — `.git` 없음 또는 working tree dirty |

## git 가드

`--inline` 이 아닌 일반 실행 시 script 가 진입 직후 두 가지를 검증한다.

1. **`.git` 존재** — 없으면 exit 6 + `/nl-setup` 안내 메시지 출력.
2. **working tree clean** — dirty 이면 exit 6 + `git stash` 또는 commit 안내 출력.

검증 통과 시 현재 branch 가 `main`/`master` 이면 `feat/<task-name>` 을 자동 생성·체크아웃한다. phase passed 시점마다 `feat(<task>): phase-<N> <name>` 메시지로 자동 commit 된다. phase 실패(escalated) 시에는 commit 하지 않고 `git reset --hard <last_good_commit>` 안내만 stderr 에 출력한다.

## 메인 컨텍스트 청결

이 SKILL 의 책임은 "script 위임 + 결과 전달" 둘. coder/reviewer 의 시행착오는 `tasks/<task-name>/phase{N}-round{M}.log` 에 격리되며, 메인 세션은 script stdout 요약만 본다.
