---
name: nl-setup
description: 신규 프로젝트 첫 진입 시 1회성으로 git init + 표준 메타 문서(CLAUDE.md / ADR template / architecture.md / coding-conventions.md / [옵션] PRD) 를 셋업한다. 하네스 정체성을 입구에서부터 강화.
---

# /nl-setup

흐름: **git 검사 → .git 확인 & init → 5항목 선택 → 파일 복사 → 리포트**.

## 사용

```
/nl-setup
```

## 단계

### 1. git 바이너리 검사

```bash
git --version
```

미설치 시 즉시 종료:

```
git not found.
설치: brew install git (macOS) / apt install git (Debian/Ubuntu)
```

OS 자동 감지·자동 설치 시도 X. 사용자 설치를 기다린다.

### 2. .git 존재 확인 & git init

```bash
ls .git 2>/dev/null
```

- `.git` 없음 → `git init` 자동 실행, 실행 사실을 stdout 으로 알림
- `.git` 있음 → skip (알림 없음)

헤드리스 X — 사용자 인터랙션이 본질. 자세한 룰·안티패턴은 `docs/spec/setup-protocol.md` 참조.

### 3. 항목 선택 (AskUserQuestion 1라운드)

5항목을 **한 번에 묶어** AskUserQuestion 1라운드로 질문한다. 항목 정의·기본값은 `docs/spec/setup-protocol.md` Step 3 참조.

- `claude_md` — CLAUDE.md (default: yes)
- `architecture` — docs/architecture.md (default: yes)
- `coding_conventions` — docs/coding-conventions.md (default: yes)
- `adr_template` — docs/adr/0000-template.md (default: yes)
- `prd` — docs/prd.md (default: no)

라운드 재호출 없음 — 1라운드로 끝낸다.

### 4. 파일 복사

각 yes 항목에 대해:

1. 대상 경로 존재 확인 → 있으면 skip 카운트++
2. 없으면 필요 시 `mkdir -p` 후 `templates/<src>` → `<dst>` 복사, created 카운트++

복사 경로 매핑은 `docs/spec/setup-protocol.md` Step 4 참조.

### 5. 리포트 출력

```
nl-setup 완료
생성: N / skip: M
```

항목별 경로·상태 표를 함께 출력. 포맷은 `docs/spec/setup-protocol.md` Step 5 참조.

## 메인 컨텍스트 청결

사용자 5항목 응답은 메인에 남지만 복사 작업은 단순 파일 조작이므로 추가 오염 없음.
