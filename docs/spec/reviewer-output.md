# Reviewer 출력 스키마

`reviewer` 서브에이전트는 모든 결과를 이 형식으로 메인에 반환한다. `nl-generate` 루프가 이 형식을 파싱하여 종료 조건(3중 안전망)을 판정한다.

## 형식

```yaml
status: ok | needs-fix | escalate
summary: <한 줄, 한국어>
issues:
  - id: <category>:<short-name>
    severity: blocking | minor
    location: <path:line | "general">
    summary: <한 줄>
    suggestion: <선택, 한 줄>
```

## status 값

| 값 | 의미 | 다음 동작 |
|----|------|-----------|
| `ok` | blocking 0개. minor 만 있어도 OK. | 루프 종료 (정상) |
| `needs-fix` | blocking ≥ 1개. 다음 라운드 필요. | coder 재호출 |
| `escalate` | reviewer 가 판단 불가 (plan 부실, 본질적 막힘). | 루프 강제 종료, 사용자 개입 |

## issue id 규칙

- 형식: `<category>:<short-name>` (영어 kebab-case)
- 예: `missing-test:login-validator`, `null-check:user-loader`, `race:cache-write`, `signature-mismatch:auth-handler`
- **같은 결함은 라운드 간 같은 id 를 유지**한다. `nl-generate` 는 동일 id 가 2 라운드 연속 등장하면 자동 escalate.

## severity

| 값 | 다음 라운드 트리거 | 예시 |
|----|---|---|
| `blocking` | yes | plan 누락, 보안 결함, 회귀, 시그니처 불일치, TDD 모드에서 테스트 누락 |
| `minor` | no (보고만) | 스타일, 명명, 사소한 중복 |

## plan 컨텍스트 분기

reviewer 호출 시 plan 파일이 함께 주어지면 **plan 대비 누락 검증**을 우선한다 — `핵심 변경` / `변경 파일` / `시그니처` 항목을 대조해 누락을 `blocking` 으로 잡는다.

plan 이 없으면 (`/nl-review` 독립 호출 시) **일반 결함 검출** 모드 — 정합성·보안·회귀를 자체 판단으로 검출.

## 안티패턴 (출력 금지)

- 자유 형식 산문으로 "코드를 살펴봤더니..." 같은 도입부 — 메인이 파싱 못 함
- `status` 누락 — 루프가 종료 판정 못 함
- 같은 결함을 매 라운드마다 다른 id 로 출력 — 반복 차단 안전망이 무력화됨
- minor 만 있는데 `status: needs-fix` — 무한 루프 유발
