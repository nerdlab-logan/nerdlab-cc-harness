---
name: nl-ship
description: git 워크플로우(commit → push → main PR (squash merge))를 수행한다. 기존 commit-message 스킬을 위임 호출한다.
---

# /nl-ship

흐름: **사전 검사 → push → PR 본문 생성 → gh pr create → URL 출력**.

## 사용

```
/nl-ship                # 현재 feat/<task> → main PR (ready)
/nl-ship --draft        # draft PR
```

## 단계

### 1. 사전 검사

- `gh --version` — 미설치 시 stderr `brew install gh && gh auth login` + exit 1
- `git status --porcelain` 비어 있어야 함 — dirty 면 stderr 안내 + exit 1
- 현재 브랜치 `git branch --show-current` — main/master 면 차단 + exit 1
- (옵션) phase 미완료 `tasks/<task>/status.json` 검사 — escalate 잔여 있으면 stderr 경고만, 진행

### 2. push

`git rev-parse --abbrev-ref --symbolic-full-name @{u}` 로 upstream 존재 확인:
- 없으면 `git push -u origin <branch>`
- 있으면 `git push`

### 3. PR 본문 생성 (commit-message 스킬 위임)

base branch = `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name` (main 강제 X — master 도 허용).

`git log <base>..HEAD` 으로 commit 목록 → `commit-message` 스킬에 위임 (PR 제목 + 본문 squash 형식).

### 4. PR 생성

`gh pr create --base <default> --head <current> --title "<제목>" --body "<본문>"` (옵션 `--draft`)

### 5. 결과 출력

stdout 5줄:
- `PR: <URL>`
- `base: <default> ← head: <current>`
- `squash 메시지 미리보기:`
- `  <제목>`
- `다음: GitHub 웹에서 'Squash and merge' 클릭`

상세는 [`docs/spec/ship-protocol.md`](../../docs/spec/ship-protocol.md) 참조.

## 메인 컨텍스트 청결

이 SKILL 의 책임은 "사전 검사 + gh CLI 호출 + 결과 전달". gh 명령 출력은 stdout 5줄로 압축, raw output 노출 X.
