# ship-protocol

`/nl-ship` 의 단계별 의사코드 + 안티패턴 표. SKILL.md 의 5단계와 1:1 매핑.

## 의사코드

### Step 1 — 사전 검사

```
if ! gh --version >/dev/null 2>&1:
    stderr "gh CLI 미설치: brew install gh && gh auth login"
    exit 1

dirty=$(git status --porcelain)
if dirty != "":
    stderr "uncommitted 변경 있음. git add && /nl-generate 로 commit 후 재실행."
    exit 1

branch=$(git branch --show-current)
if branch in ["main", "master"]:
    stderr "main/master 브랜치에서 직접 push 금지. feat/<task> 브랜치로 전환 후 재실행."
    exit 1

if tasks/<task>/status.json exists:
    escalate_remaining=$(parse escalate 잔여 수)
    if escalate_remaining > 0:
        stderr "경고: phase 미완료 escalate ${escalate_remaining}건 잔여. 계속 진행."
```

### Step 2 — push

```
upstream=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null)
if upstream == "":
    git push -u origin <branch>
else:
    git push
```

### Step 3 — PR 본문 생성

```
default_branch=$(gh repo view --json defaultBranchRef --jq .defaultBranchRef.name)
commits=$(git log ${default_branch}..HEAD --oneline)

# commit-message 스킬에 위임
# 입력: commits 목록
# 출력: PR 제목(첫 줄) + 본문(squash merge 형식)
invoke commit-message skill with commits → (title, body)
```

### Step 4 — PR 생성

```
flags="--base ${default_branch} --head ${branch} --title '${title}' --body '${body}'"
if --draft 옵션:
    flags += " --draft"

pr_url=$(gh pr create ${flags})
```

### Step 5 — 결과 출력

```
stdout:
  "PR: ${pr_url}"
  "base: ${default_branch} ← head: ${branch}"
  "squash 메시지 미리보기:"
  "  ${title}"
  "다음: GitHub 웹에서 'Squash and merge' 클릭"
```

## 안티패턴 표

| 안티패턴 | 이유 | 대안 |
|----------|------|------|
| 자동 squash merge | 되돌릴 수 없음. 사용자 의도 확인 필요. | GitHub 웹에서 수동 'Squash and merge' |
| force push (`git push --force`) | 공유 브랜치 히스토리 훼손. 협업 사고 유발. | rebase 후 일반 push. force가 필요하면 사용자 명시 요청. |
| draft → ready 자동 전환 | draft 는 WIP 의도적 표시. 자동 ready 는 의미 훼손. | 사용자가 GitHub 웹에서 직접 전환. |
| main 직접 push | 브랜치 보호 규칙 우회. PR 리뷰 흐름 무력화. | feat/<task> 브랜치 → PR 경유. |
| 충돌 자동 해결 | 충돌 해결은 의미적 판단 — 자동화 불가. 잘못된 머지로 데이터 손실 위험. | 사용자에게 충돌 파일 목록 + `git mergetool` 안내. |

## 관련 파일

- `skills/nl-ship/SKILL.md` — 호출 인터페이스 + 단계 요약
- `~/.claude/skills/commit-message/SKILL.md` — PR 제목 / 본문 / squash 메시지 생성
- `~/.claude/docs/git/pr-convention.md` — PR 본문 템플릿
- `~/.claude/docs/git/squash-merge-convention.md` — squash 머지 메시지 형식
- `docs/spec/git-guard-protocol.md:66` — push/PR 은 nl-ship 책임 명문화
