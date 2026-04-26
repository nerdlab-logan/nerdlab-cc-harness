---
name: nl-review
description: 현재 변경 사항을 헤드리스 reviewer(Opus)로 검토한다. plan 대비 누락/회귀/보안 이슈를 찾아 요약 리포트를 반환한다.
---

# /nl-review

현재 변경 사항을 헤드리스 `claude -p` 세션(Opus) 에 위임해 검토한다. plan 파일 인자가 있으면 plan 대비 누락을 우선 검증하고, 없으면 ad-hoc 모드(정합성·보안·회귀 자체 판단)로 동작한다.

## 사용

```
/nl-review                          # ad-hoc — 현재 변경 사항만 검토
/nl-review <plan-path>              # plan 대비 검토 (누락·시그니처 불일치 우선)
```

예: `/nl-review tasks/add-login-rate-limit/plan.md`

## 동작

`Bash` 도구로 다음을 실행한다.

**plan 인자 없을 때 (ad-hoc 모드):**

```bash
claude -p \
  --model opus \
  --allowed-tools "Read,Glob,Grep,Bash" \
  --append-system-prompt "$(cat /Users/tiredman/Developer/own/cc-marketplace/nerdlab-harness/prompts/reviewer.md)" \
  "<요구사항>"
```

**plan 인자 있을 때 (plan 모드):**

```bash
plan_text=$(cat "<plan-path>")
claude -p \
  --model opus \
  --allowed-tools "Read,Glob,Grep,Bash" \
  --append-system-prompt "$(cat /Users/tiredman/Developer/own/cc-marketplace/nerdlab-harness/prompts/reviewer.md)" \
  "<요구사항>

## Plan 전체
${plan_text}"
```

`<요구사항>` 은 사용자가 `/nl-review` 에 함께 전달한 자유 텍스트(없으면 "현재 변경 사항을 검토하라"). plan 인자는 경로이므로 `cat` 으로 텍스트를 읽어 user prompt 에 합친다.

## 출력 처리

헤드리스 stdout(YAML fence) 을 사용자에게 그대로 전달한다. **메인은 YAML 을 재해석·요약하지 않는다.**

## 메인 컨텍스트 청결

이 SKILL 의 책임은 "헤드리스 1회 호출 + 결과 전달" 둘. reviewer 의 코드베이스 탐색 과정은 헤드리스 세션 안에 격리된다.
