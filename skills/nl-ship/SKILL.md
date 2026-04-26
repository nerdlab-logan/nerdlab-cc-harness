---
name: nl-ship
description: git 워크플로우(commit → push → main PR (squash merge))를 수행한다. 기존 commit-message 스킬을 위임 호출한다.
---

TODO: 구현 예정

## 의도

- GitHub flow 기준 흐름 자동화 — `feat/<task>` 브랜치 → main PR (squash merge)
- 기존 자산 재활용:
  - `~/.claude/skills/commit-message/SKILL.md` — 커밋 메시지 생성
  - `~/.claude/docs/git/branch-strategy.md` — 브랜치 규칙
  - `~/.claude/docs/git/pr-convention.md` — PR 템플릿
  - `~/.claude/docs/git/squash-merge-convention.md` — squash 머지 메시지 형식
- 단순 git 작업이라 Sonnet/Haiku 충분
