# Setup 프로토콜

`/nl-setup` 의 절차 규칙. **메인 세션** 이 수행한다 (사용자 인터랙션이 본질 — 헤드리스 격리의 명시적 예외. clarify / Phase A / eval 과 동일한 "메인 예외" 카테고리).

이 단계의 목적: 신규 프로젝트에 표준 메타 문서를 1회성으로 배치해 "하네스 정체성" 을 입구에서부터 강화한다.

---

## Step 1 — git 바이너리 검사

```bash
git --version
```

- 성공 → Step 2
- 실패(명령 없음) → 아래 메시지 출력 후 **즉시 종료**:

  ```
  git not found.
  설치: brew install git (macOS) / apt install git (Debian/Ubuntu)
  ```

  OS 자동 감지나 자동 설치 시도 X. 사용자에게 설치를 위임한다.

---

## Step 2 — .git 존재 확인 & git init

```bash
ls .git 2>/dev/null
```

- `.git` 없음 → `git init` 자동 실행, stdout 으로 실행 사실 알림
- `.git` 있음 → skip (알림 없음)

`/nl-setup` 호출 자체가 의도 명확이므로 "init 할까요?" 재확인 질문 없음.

---

## Step 3 — AskUserQuestion (1라운드, 5항목)

5항목을 **한 번에 묶어** AskUserQuestion 1라운드로 질문한다. 항목별 개별 질문 X.

| 키 | 질문 | options | 기본값 |
|----|------|---------|--------|
| `claude_md` | CLAUDE.md 생성 여부 | yes / no | yes |
| `architecture` | docs/architecture.md 생성 여부 | yes / no | yes |
| `coding_conventions` | docs/coding-conventions.md 생성 여부 | yes / no | yes |
| `adr_template` | docs/adr/0000-template.md 생성 여부 | yes / no | yes |
| `prd` | docs/prd.md 생성 여부 (optional) | yes / no | no |

라운드 재호출 없음 — 1라운드로 끝낸다. 재초기화가 필요하면 파일 수동 삭제 후 `/nl-setup` 재실행.

---

## Step 4 — 파일 복사

### 복사 경로 매핑

| 키 | 소스 (`templates/` 기준) | 대상 (프로젝트 루트 기준) |
|----|--------------------------|--------------------------|
| `claude_md` | `CLAUDE.md` | `CLAUDE.md` |
| `architecture` | `docs/architecture.md` | `docs/architecture.md` |
| `coding_conventions` | `docs/coding-conventions.md` | `docs/coding-conventions.md` |
| `adr_template` | `docs/adr/0000-template.md` | `docs/adr/0000-template.md` |
| `prd` | `docs/prd.md` | `docs/prd.md` |

### 충돌 skip 정책

- 대상 경로가 **이미 존재** → skip + skip 카운트++ (덮어쓰지 않음)
- 대상 경로가 **없음** → 필요하면 `mkdir -p` 로 중간 디렉토리 생성 후 복사, created 카운트++

`--force` / 덮어쓰기 옵션 없음. 충돌은 무조건 skip + 리포트로 처리.

### 소스 경로 기준

`templates/` 는 **하네스 저장소 루트** 기준으로 계산한다. SKILL.md 위치(`skills/nl-setup/`) 에서 `../../templates/` 로 접근한다.

---

## Step 5 — 리포트 출력

```
nl-setup 완료
생성: {created} / skip: {skipped}

항목                경로                              상태
──────────────────────────────────────────────────────────────
claude_md           CLAUDE.md                         생성
architecture        docs/architecture.md              생성
coding_conventions  docs/coding-conventions.md        생성
adr_template        docs/adr/0000-template.md         생성
prd                 (선택 안 함)                       -
```

- skip 항목: 경로 뒤 `skip (이미 존재)` 표시
- yes 선택 + skip 항목 vs no 선택 항목 을 리포트에서 명확히 구분

---

## 의사코드 골격

```
step 1: git --version → 실패 시 안내 메시지 + 종료
step 2: ls .git → 없으면 git init 실행
step 3: AskUserQuestion (1라운드, 5항목)
        - claude_md: yes/no (default yes)
        - architecture: yes/no (default yes)
        - coding_conventions: yes/no (default yes)
        - adr_template: yes/no (default yes)
        - prd: yes/no (default no)
step 4: 각 yes 항목에 대해
        - 대상 경로 존재 확인 → 있으면 skip 카운트++
        - 없으면 templates/<src> → <dst> 복사, created 카운트++
step 5: 리포트 출력
        - "생성: N / skip: M / 항목별 경로 표"
```

---

## 안티패턴

| 안티패턴 | 올바른 대안 |
|----------|------------|
| 파일 이미 있는데 덮어쓰기 | 충돌 시 무조건 skip + 리포트 |
| git not found 인데 설치 시도 | 에러 메시지 + 즉시 종료 |
| "git init 할까요?" 재확인 질문 | `/nl-setup` 호출 자체가 의도 명확 — 자동 init |
| 항목별 개별 AskUserQuestion | 5항목 한 라운드 묶음 |
| 헤드리스 `claude -p` 호출 | 메인 직접 (사용자 인터랙션 필수) |
| 복사 후 내용 수정 | 템플릿 원본 그대로 복사 — 수정은 사용자 몫 |
| templates/ 없는 하네스 환경에서 무시하고 진행 | 소스 파일 부재 시 해당 항목 skip + 리포트에 `templates 없음` 표시 |
