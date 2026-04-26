# Context Gather 프로토콜

`/nl-plan` 단계 2에서 실행하는 Context Gather의 정형 명세. Phase A(결정적 스캔)와 Phase B(헤드리스 익스플로러)로 나뉜다. 결과는 plan.md `## Context` 섹션에 기록된다.

---

## 빈 코드 감지 & 스킵 룰

```bash
N=$(git ls-files 2>/dev/null | wc -l | tr -d ' ')
if [ ! -d .git ] || [ "$N" = "0" ]; then
  CONTEXT="none (empty codebase)"
fi
```

- `.git` 디렉토리가 없거나 추적 파일이 0개이면 Context Gather를 스킵한다.
- `## Context` 섹션 본문은 `none (empty codebase)` 한 줄로 채운다.
- 이 값은 `validate_plan.py` 가 합법(비지 않음)으로 인정한다.

---

## Phase A — 결정적 스캔 (메인 직접)

메인 세션이 Bash 도구로 직접 실행한다. 재현 가능성·디버그성 우선이므로 LLM에 위임하지 않는다.

### 실행 명령 목록

```bash
# 1. 전체 추적 파일 목록
git ls-files

# 2. 디렉토리 분포 (깊이 2)
git ls-files | awk -F/ 'NF>1{print $1"/"$2} NF==1{print $1}' | sort -u

# 3. 핵심 키워드 grep (요구사항에서 추출한 식별자)
git ls-files | xargs grep -l "<keyword>" 2>/dev/null
```

### Phase A 출력 요건

- 전체 결과를 그대로 전달하지 않는다. 5~10줄로 정리해 Phase B user prompt에 합성한다.
- 포함: 관련 디렉토리 경로, 키워드 히트 파일, 파일 총 수.
- 제외: 테스트 fixture, 빌드 아티팩트, 바이너리.

---

## Phase B — 헤드리스 익스플로러

### 호출 형식

```bash
claude -p \
  --allowed-tools "Read,Grep,Glob" \
  --append-system-prompt "$(cat prompts/explorer.md)" \
  "<Phase A 정리 결과 + clarify 요약>"
```

### 도구 권한

| 허용 | 금지 |
|------|------|
| Read | Write |
| Grep | Edit |
| Glob | Bash |

Context 단계는 읽기 전용이 본질이다. Write/Edit/Bash를 허용하면 의도치 않은 변경이 발생할 수 있다.

### 출력 ★ 형식 (plan.md `## Context` 본문에 그대로 삽입)

```markdown
### 영향 파일 ★
- <path> — <한 줄 이유>

### 관련 시그니처 ★
- <path:line> `<함수/타입 시그니처>` — <한 줄>

### 기존 패턴 ★
- <패턴명> — <어디서 따올지 / 1~2줄>
```

- 세 헤더(`영향 파일 ★` / `관련 시그니처 ★` / `기존 패턴 ★`) 모두 필수. 하나라도 빠지면 `validate_plan.py` 가 Context 섹션을 비었다고 판정한다.
- 각 항목은 최소 1개 이상이어야 한다.
- 항목이 없는 경우 `- none` 을 명시한다 (`none (empty codebase)` 와는 달리 헤더는 있어야 함).

---

## 안티패턴

| 안티패턴 | 올바른 대안 |
|----------|------------|
| Phase B가 Bash로 `git log` 직접 조회 | Phase A가 메인에서 추출 후 user prompt에 전달 |
| Context 섹션에 raw grep 출력 수백 줄 복붙 | Phase A에서 5~10줄로 정리 후 Phase B가 요약 |
| 영향 파일 없이 `관련 시그니처 ★` 만 기재 | 세 헤더 모두 채워야 함 |
| `## Context` 섹션 통째로 생략 | 빈 코드 시라도 `none (empty codebase)` 한 줄 필수 |
| `TBD` / `추후 추가` 등 placeholder 기재 | 실제 파일/시그니처/패턴 또는 `- none` 명시 |
| Context를 별도 파일(`context.md`)로 분리 | plan.md `## Context` 섹션에 통합 (단일 파일 원칙) |
