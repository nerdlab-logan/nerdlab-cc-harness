# git 가드 프로토콜

`/nl-generate` 실행 시 git 상태를 검증하고, 올바른 branch 위에서 phase 단위 commit 을 자동으로 생성하며, 실패 시 안내만 출력하고 자동 reset 은 하지 않는 5 책임 가드.

## 책임

| 번호 | 책임 | 함수 | 동작 |
|------|------|------|------|
| 1 | git repo 검증 | `_check_git_state` | `.git` 미존재 → 차단, dirty tree → 차단 |
| 2 | feature branch 보장 | `_ensure_feature_branch` | main/master 위면 `feat/<task>` 자동 생성·체크아웃 |
| 3 | phase commit | `_commit_phase` | phase passed 직후 `git add -A` + commit |
| 4 | 실패 리포트 | `_render_failure_report` | failed 시 stderr 안내 출력. 자동 reset 없음 |
| 5 | exit code | `EXIT_CODE_GIT_GUARD = 6` | 가드 차단 시 6 반환 |

## exit code

| 코드 | 의미 |
|------|------|
| 6 | git 가드 차단 (`.git` 없음 또는 dirty tree) |

기존 exit code 와 충돌 없음: `EXIT_CODE_INLINE_INVALID = 5`.

## 차단 메시지 형식

### `.git` 미존재 (stderr)

```
git 가드: .git 디렉토리 없음. /nl-setup 으로 git 초기화 후 재실행.
```

### dirty tree (stderr)

```
git 가드: working tree 가 dirty. /nl-generate 는 clean tree 에서만 동작.
변경 사항 처리 후 재실행:
  git status
  git add ... && git commit -m "..."  또는  git stash
```

## phase commit 메시지 형식

```
feat(<task>): phase-<N> <name>
```

예시:
- `feat(add-evaluate-gate): phase-1 스펙·검증`
- `feat(nl-setup-skill): phase-1 단일`

`<task>` = `tasks/<task>/` 디렉토리 이름, `<N>` = phase 번호, `<name>` = Phase 분해 표 이름 칸.

## phase 실패 리포트 형식 (stderr)

```
phase {N} ({name}) 실패: {reason}
last_good_commit: {hash}
복원 명령 (필요 시): git reset --hard {hash}
```

자동 reset 은 실행하지 않는다. 사용자가 직접 판단·실행한다.

## 안 하는 것

- auto stash / auto reset / branch 자동 삭제
- worktree 도입 (cwd 그대로 사용)
- push / rebase / merge / PR (`nl-ship` 책임)
- signing / GPG / pre-commit hook 강제
- `--force-no-git` 가드 우회 옵션
- 다중 task 병렬 race condition 처리
- 자동 issue 생성 / 알림

## 데이터 흐름

```
main()
  ↓ parse_args
  ↓ plan_path 검증
  ↓ _check_git_state(cwd)   → False → stderr + sys.exit(6)
  ↓ _ensure_feature_branch(task_name, cwd)
  ↓ phase 실행 루프
      phase passed → _commit_phase(task_name, phase, cwd) → last_good_commit 갱신
      phase failed → _render_failure_report(phase, last_good_commit, reason) → stderr
```
