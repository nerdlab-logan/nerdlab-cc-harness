# nerdlab-harness 작업 기록

매 작업 단위로 갱신한다. 형식: `## YYYY-MM-DD` 헤더 아래 완료 항목과 다음 작업.

---

## 2026-04-25

### Done
- 디렉토리 구조 생성 (`.claude-plugin/`, `skills/`, `agents/`, `hooks/`, `docs/`)
- `.claude-plugin/plugin.json` — 메타데이터
- 4개 skill placeholder — `nl-plan`, `nl-code`, `nl-review`, `nl-ship`
- 3개 agent placeholder — `planner` (opus), `coder` (sonnet), `reviewer` (opus)
- `docs/philosophy.md` — 모델 분배 표 + 새 skill 추가 체크리스트
- `README.md` — 4단계 파이프라인 사용 흐름 + 설치 한 줄
- `.gitignore`

---

## 2026-04-26

### Done

#### 결정 · 철학
- 모델 표기 규칙: 버전 번호 없이 모델 패밀리만 (`Opus 4.7` → `Opus`)
- 노션 글(jha0313 `harness_framework`) 분석 + 비교 — `docs 깊이 = 결과 품질`, MVP 제외 사항·트레이드오프·hooks 패턴이 강점, 모델 분배 부재가 약점
- **흐름 변경**: 4단계 → `plan → generate(phase 직렬 + coder↔reviewer 루프) → ship` + `nl-review` 독립 진입점
- **루프 종료 조건 3중 안전망**: (1) reviewer `status: ok` (2) 최대 3 라운드 (3) 동일 issue id 2회 연속 → escalate
- **TDD 옵션 방식**: `/nl-generate --tdd` 인자 (plan TDD 필드를 yes 로 강제)
- **task/phase 구조 채택**: plan-template 에 `Phase 분해` 섹션, `nl-generate` 가 phase 직렬 실행
- **`scripts/run_phases.py` 도입 결정**: phase 별 헤드리스 Claude 호출, 상태 관리, 실패 재시작 (본구현은 다음 세션)
- **`tasks/` git 정책**: 본 저장소는 `tasks/*` ignore + `.gitkeep` 만 commit, 하네스 사용 프로젝트는 `tasks/` 전체 commit 권장

#### 구조 변경
- skill 디렉토리 rename: `nl-code` → `nl-build` → `nl-generate` (최종)
- `skills/nl-review/` 독립 진입점으로 유지
- 디렉토리 통합: 옛 `docs/plans/` + 옛 `docs/runs/` 제안 → `tasks/<task-name>/{plan.md, status.json, phase*.log}` 한 폴더로
- `docs/plans/` 빈 디렉토리 삭제, `tasks/` + `scripts/` 신설
- `tasks/.gitkeep` 추가, `.gitignore` 에 `tasks/*` + `!tasks/.gitkeep`

#### 명세 신규 (단일 진실의 출처)
- `docs/spec/plan-template.md` — planner 출력 형식 (필수 섹션 10개, ★ 표시 강제 항목, Phase 분해 가이드)
- `docs/spec/reviewer-output.md` — reviewer YAML 출력 스키마 (status / issues / severity / id 규칙)

#### 본구현
- `agents/planner.md` — 시스템 프롬프트, 작업 흐름, "안 할 것"/트레이드오프/Phase 분해 휴리스틱
- `skills/nl-plan/SKILL.md` — 위임 + 다음 단계 안내
- `scripts/run_phases.py` — placeholder (자리 확보)

#### 정합성 갱신
- `skills/nl-generate/SKILL.md` placeholder (설계만 박아둠, 본구현은 다음 세션)
- `README.md` — 디렉토리 트리, 파이프라인, `tasks/` 정책 표
- `docs/philosophy.md` — "개발·검증은 한 사이클" 섹션 추가, `docs/spec/` 단일 진실 출처 명문화
- `TODO.md` 도입 + 매 작업 단위 갱신
- 메모리에 가이드 추가 (모델 표기, TODO 갱신 룰)

#### nl-plan 1차 실호출 테스트 (서브에이전트)
- 후보 D 요구사항(`run_phases.py` 골격)으로 `/nl-plan` 호출 → `tasks/run-phases-skeleton/plan.md` 생성됨
- **plan 본문**: spec 10개 섹션 모두 채워짐 (★ 3개 포함). 길이 128줄. 통과.
- **메인 응답 결함 3건 발견**:
  - ① 명세 외 텍스트 누설 ("plan 파일을 생성했습니다" 헤더, "검토 후 만족하면..." 다음 단계 안내)
  - ② 라벨 변형 (`plan:` → `경로:`, `phases:` → `Phase:`)
  - ③ 핵심 변경 항목 한 줄 합치기 (`+` 로 연결)

#### 헤드리스 전환 결정 + 실행
- **결정 (사용자 명시)**: 서브에이전트 메커니즘 대신 `claude -p` 헤드리스 통일. 이유: 모든 단계 동일 호출 패턴, 사람 직접 재현 가능, `run_phases.py` 가 서브에이전트 호출 불가능 (헤드리스가 유일한 길)
- `agents/` → `prompts/` rename — 명칭 정확성 (서브에이전트 아니라 시스템 프롬프트)
- `prompts/*.md` frontmatter 제거 — 헤드리스에선 의미 없음, 모델/도구는 SKILL 책임
- `prompts/planner.md` 결함 ①②③ 수정 — "stdout 5줄만, 추가 텍스트 금지" + 라벨 정확화 + 핵심 변경 ` | ` 구분 명시
- `skills/nl-plan/SKILL.md` 헤드리스 호출로 교체 (`Bash` + `claude -p --model opus --append-system-prompt "$(cat prompts/planner.md)"`)
- `~/.claude/agents/planner.md` symlink 제거 (헤드리스 전환 후 불필요)
- `README.md`, `docs/philosophy.md` 표현 갱신 (서브에이전트 격리 → 헤드리스 격리)

#### nl-plan 2차 재테스트 (헤드리스) — 통과
- 같은 후보 D 요구사항으로 새 세션 호출 → `tasks/run-phases-skeleton/plan.md` 덮어쓰기
- **결함 ①②③ 모두 해결**: stdout 정확히 5줄, 라벨 정확(`plan:`/`phases:`), 핵심 변경 ` | ` 구분
- plan 본문 품질: 1차 대비 트레이드오프 5→7행, 시그니처에 `task_dir_for()`/`schema_version`/`repeated_issue_id` 추가, 데이터 흐름 5→6단계, atomic write 결정 추가 (149줄)
- "다음 단계" 안내는 메인이 SKILL.md 의 섹션 보고 사용자에게 전달 — 의도한 책임 분리 확인
- 미세 결함 1: `phases: 1 (단일)` 형식 (자동 파싱은 plan.md 의 표를 직접 보므로 무영향, 합격)

#### run_phases.py 골격 본구현 (부트스트랩 — 메인 직접 작성)
- `/nl-generate` 가 `run_phases.py` 에 의존하는 닭-달걀 상황. 이번 한 번만 메인에서 plan 따라 직접 코드 작성.
- plan 5개 핵심 결정 사용자 검토 통과 (범위·`--max-rounds 3`·`schema_version`·TDD no·외부 라이브러리 0개)
- `scripts/run_phases.py` 18줄 placeholder → 약 300줄 골격으로 교체
- 검증 4가지 통과:
  - `--help`: 인자 설명 한국어 출력
  - 정상 호출: status.json 생성(`schema_version: 1`, phases 1, in_progress), `NotImplementedError`, exit 10, traceback stderr / 요약 stdout
  - `--resume`: 기존 status 로드, `started_at` 유지·`updated_at` 갱신, 같은 NotImplementedError
  - `parse_phases()` 직접: Phase 1("스켈레톤") 정확 추출
- `run_phase` / `run_round` 시그니처만, 본문 NotImplementedError → 다음 PR 진입점

#### run_phase / run_round 본구현 (부트스트랩 2회차 — TDD 메인 직접)
- `/nl-generate tasks/run-phases-implement/plan.md` 호출 → 부트스트랩 잔존(`run_phase` 가 NotImplementedError) 으로 스크립트 실행 불가 확인 후 메인 직접 진행 (TODO 가이드 그대로)
- plan TDD: yes → `tests/test_run_phases.py` 9개 테스트 먼저 작성 → 9개 모두 ERROR (red 확인)
- `scripts/run_phases.py` 신규 헬퍼 5개:
  - `_parse_reviewer_output` — fence(```yaml ... ```) 추출 후 `status:` 1개 + `id:` N개 정규식 (외부 의존 0)
  - `_decide_phase_outcome` — 순수 함수, 우선순위: ok → escalate → max-rounds → repeated → continue
  - `_call_coder` / `_call_reviewer` — `subprocess.run([claude, -p, --model, --allowed-tools, --append-system-prompt, ...])` 동기 호출, `(stdout, stderr, rc)` 반환
  - `_write_round_log` — `phase{N}-round{M}.log` 에 `### <name>` 섹션 헤더로 coder/reviewer stdout/stderr/rc 합쳐 기록
- `run_round` / `run_phase` 본문 채움 — coder rc!=0 / reviewer rc!=0 / YAML 파싱 실패 시 합성 escalate dict 반환해 phase 즉시 종료
- `main()` 의 `try/except NotImplementedError` 제거 + `result.state == "escalated"` 시 stderr 요약 + exit 1 분기 추가
- 모듈 docstring / argparse description 의 "(skeleton)" 표현 제거
- 검증:
  - `python3 -m unittest tests.test_run_phases -v` → 9/9 PASS (parse 4개 + decide 5개)
  - `--help` 회귀: 기존 인자 설명 그대로
  - import + `parse_phases()` 스모크 → Phase 1("본구현") 정확 추출, 헬퍼 5개 + 정규식 3개 노출
- 부트스트랩 데모로 생긴 stale `tasks/run-phases-implement/status.json` 삭제 (--resume 혼란 방지, 본 작업은 스크립트가 아니라 메인이 수행)

#### prompts + nl-generate/nl-review SKILL 본구현 (★ 첫 실호출 동시 검증 — 부트스트랩 종료)
- `/nl-plan prompts/coder.md 와 prompts/reviewer.md ...` → `tasks/coder-reviewer-skills/plan.md` 자동 생성 (phases 2 직렬, TDD no, 105줄)
- `/nl-generate tasks/coder-reviewer-skills/plan.md` → `python3 scripts/run_phases.py` background 호출 → exit 0
  - **Phase 1 (prompts 본구현)**: round 1 passed. coder 가 placeholder coder.md 시스템 프롬프트로 호출돼 출력은 자유 산문 형식 (이번 한정 OK), 변경은 plan 시그니처대로 정확. reviewer YAML status: ok, issues: [].
  - **Phase 2 (skills 본구현)**: round 1 passed. coder 가 phase 1 결과 본구현 coder.md 로 호출돼 stdout `변경: ... / 요약: ...` 형식 정확 준수. reviewer status: ok.
- 검증 4가지 통과: 프롬프트 길이(53/75줄), unittest 9 PASS, --help 회귀, fence + status 형식 정확
- **부트스트랩 완전 종료** — `prompts/coder.md` (53줄, 절대 규칙 5 + BLOCKED + 핸드오프), `prompts/reviewer.md` (75줄, plan/ad-hoc 분기 + 안티패턴 표), `skills/nl-generate/SKILL.md` (49줄, script 위임 + 종료 코드 표), `skills/nl-review/SKILL.md` (55줄, plan optional 합성 분기) 모두 placeholder 졸업
- 라운드 로그(`tasks/coder-reviewer-skills/phase{1,2}-round1.log`) 에 coder/reviewer stdout/stderr/rc 정상 기록. status.json 양쪽 phase 모두 passed

#### `--tdd` / `--inline` 옵션 본구현 (★ /nl-plan → /nl-generate 두 번째 실호출, TDD 모드)
- `/nl-plan run_phases.py 에 --tdd 와 --inline 옵션 본구현 ...` → `tasks/run-phases-tdd-inline-options/plan.md` 자동 생성 (phases 2 직렬, TDD yes, 156줄)
- 호출 시 `--tdd` 플래그를 script 에 직접 넘기면 exit 2 (옵션 미존재) — plan TDD 필드가 yes 이므로 플래그 없이 호출하면 됨을 확인. plan 자체가 자기 자신의 옵션 신설을 명세함
- `/nl-generate tasks/run-phases-tdd-inline-options/plan.md` → `python3 scripts/run_phases.py` background → exit 0
  - **Phase 1 (--tdd)**: round 1 passed. `parse_args` 에 `--tdd`, `_compose_system_prompt(role, tdd)` 신규, `prompts/coder_tdd.md` (20줄) + `prompts/reviewer_tdd.md` (22줄) 신규, `_call_coder` / `_call_reviewer` / `run_round` / `run_phase` / `main` 흐름에 tdd 전파, `TestComposeSystemPrompt` 3개 추가
  - **Phase 2 (--inline)**: round 1 passed. `parse_args` 에 `--inline`, `run_inline(plan_path, phases) -> int` + `_count_changed_files` 신규, `EXIT_CODE_INLINE_INVALID = 5`, `main()` 에 inline 분기 + `--tdd` + `--inline` 동시 사용 시 stderr 경고 + `--inline` 만 적용, `TestRunInline` 3개 추가
- 검증 4가지 통과:
  - `--help`: `--tdd` / `--inline` 두 옵션 한국어 설명 노출
  - unittest: 15/15 PASS (기존 9 + 신규 6)
  - 본 plan 자체로 `--inline` 호출 → stderr `--inline 조건 불충족: phase 수 2 (1이어야 함)` + exit 5
  - prompts/*_tdd.md 본문 — TDD 사이클·금지 사항·blocking 격상 규약 모두 자연어로 명시
- 트레이드오프 인상: TDD 룰을 별도 파일로 분리한 결정 덕에 `--tdd` 안 켜진 통상 모드에서 system prompt 누설 0. `_compose_system_prompt` 헬퍼 한 곳 → 단위 테스트 가능
- 미세 결함: 본 plan 의 `--tdd` + `--inline` 동시 사용은 stderr 경고만 찍고 통과시키는 결정 (실패 차단 X). 향후 사용성 관찰 후 재검토 필요

#### `BLOCKED:` 토큰 자동 escalate 분기 본구현 (★ /nl-plan → /nl-generate 세 번째 실호출, TDD 모드)
- `/nl-plan _call_coder 결과 stdout 첫 줄이 BLOCKED: ...` → `tasks/coder-blocked-escalate/plan.md` 자동 생성 (phases 1, TDD yes, 83줄)
- `/nl-generate tasks/coder-blocked-escalate/plan.md` → `python3 scripts/run_phases.py` background → exit 0
  - **Phase 1 (BLOCKED 분기 본구현)**: round 1 passed. `_is_coder_blocked(stdout)` 헬퍼 신규(`stdout.lstrip().startswith("BLOCKED:")` 단순 매칭), `run_round` 에 coder 호출 직후 BLOCKED 분기 추가(reviewer 미호출 + 합성 escalate dict `{"status":"escalate","issue_ids":["coder:blocked"],"raw":coder_out}` 반환), round 로그에 reviewer "(skipped: coder BLOCKED)" 명시, `_decide_phase_outcome` 에 `issue_ids[0]=="coder:blocked"` 인지 + reason `"coder blocked"` 분기 추가
  - reviewer status: ok ("plan 의 핵심 변경·변경 파일·시그니처 모두 일치하고 22 테스트 PASS")
- 검증 4가지 통과:
  - unittest: 22/22 PASS (기존 15 + 신규 `TestIsCoderBlocked` 5 + `TestDecidePhaseOutcome` reason 분기 2)
  - `--help` 회귀 없음 (옵션 추가 없음)
  - 코드 리뷰: `scripts/run_phases.py:406-408` 헬퍼, `:444-458` BLOCKED 분기, `:298-299` reason 분기 — 모두 plan 시그니처 그대로
  - 신규 테스트: `BLOCKED: ...` 첫 줄 / 앞 공백 / 빈 문자열 / 정상 출력 / 두 번째 줄 BLOCKED 5가지 양음성 커버
- 트레이드오프 인상: `_is_coder_blocked` 헬퍼 분리 덕에 `run_round` 본문은 외부 프로세스 의존 그대로 두고 분기만 단위 테스트 가능. issue_ids 첫 항목으로 reason 분기하는 방식 → review dict 시그니처 불변 (별도 reason 키 도입 회피)
- 잠재 결함 1: `_decide_phase_outcome` 의 escalate 분기에서 `issue_ids[0]=="coder:blocked"` 체크가 첫 항목만 보므로 향후 합성 escalate 가 다중 issue id 를 가지면 부정확. 현재는 합성 dict 가 단일 id 만 채워서 안전

#### reviewer phase 범위 한정 본구현 (★ /nl-plan → /nl-generate 네 번째 실호출, TDD 모드)
- `/nl-plan run_round 의 reviewer 호출 시 plan 전체 대신 현재 phase 만 슬라이스 ...` → `tasks/reviewer-phase-slice/plan.md` 자동 생성 (phases 1, TDD yes, 71줄)
- `/nl-generate tasks/reviewer-phase-slice/plan.md` 1차 호출 → `parse_phases` 가 `ValueError: Phase 분해 표가 비어 있음` 으로 즉시 실패 (exit 1)
- **부트스트랩 발견 — `parse_phases` 정규식 버그**: `scripts/run_phases.py:130` 의 `##\s+Phase 분해.*?\n` 이 행 시작 앵커(`^`) 없어, plan 의 시그니처 docstring 안에 백틱으로 인용된 `\`## Phase 분해\`` 를 먼저 매치 → 진짜 `## Phase 분해` 섹션을 못 찾고 docstring 본문을 표 영역으로 오인. 사용자에게 A(plan 우회)/B(근본 수정)/C(plan 재작성) 3안 제시 → **B 선택**
- 메인 직접 부트스트랩 수정: 정규식에 `^` 앵커 추가(`re.MULTILINE` 와 함께) + `tests/test_run_phases.py` 에 `TestParsePhasesHeaderAnchor` 회귀 테스트 1개(`test_inline_backtick_phase_header_in_signature_is_ignored`) 추가 → unittest 22 → 23 PASS
- `/nl-generate` 재호출 → exit 0
  - **Phase 1 (단일)**: round 1 passed. `_slice_phase_table(plan_text, phase_number) -> str` 헬퍼 신규(310-363) — 표 헤더 2줄 유지 + 일치 phase 행 1개만 남기고 나머지 데이터 행 제거, 일치 행 없으면 `ValueError`. `_build_reviewer_prompt` 가 슬라이스 적용 + "이번 라운드는 phase {N} ({이름}) 의 변경사항만 검증한다" 가이드 prepend. `_build_coder_prompt` 미변경(plan "안 할 것" 준수). `tests/test_run_phases.py` 신규 10개 추가 → unittest 23 → 34 PASS. reviewer status: ok, issues: []
- 트레이드오프 인상: 슬라이스 대상을 `Phase 분해` 표 1개 섹션으로만 한정한 결정 덕에 plan-template 변경 없이 reviewer 격리 달성. 변경 파일·시그니처는 phase 라벨 없으므로 자동 분리 보류 (plan 명시)
- 잠재 결함 1: `_slice_phase_table` 의 정규식이 `parse_phases` 와 동일한 패턴을 두 곳에 중복. 향후 PHASE_TABLE_HEADER 형식 바뀌면 두 곳 동기화 필요. 헬퍼화는 본 작업 범위 밖

#### 슬래시 등록 메커니즘 조사 + 등록 방식 전환 결정
- 조사 결과 (claude-code-guide 두 차례 호출):
  - SKILL 자동 발견 = `~/.claude/skills/` 또는 cwd 의 `.claude/skills/` 스캔. 자연어 트리거만 작동, 슬래시 노출 X
  - 슬래시 노출 = plugin **install** 상태에서 `/<plugin-name>:<skill-name>` 형식. 단순 `/nl-plan` 은 처음부터 잘못된 형식
  - 단일 plugin 직접 install 경로 없음. 공식은 (1) 개발 모드 `claude --plugin-dir <path>` (2) release 검증 시점 로컬 마켓플레이스(`marketplace.json` 1개) 등록 → `/plugin install` (3) 공개 시 GitHub push / 공식 PR
- 현재 동작 발견: `~/.claude/skills/{nl-plan,nl-generate}` 가 `Developer/tools/nerdlab-harness/skills/...` 로 symlink 되어 있어 사용자 전역 skill 로 인식되던 것. plugin 메커니즘 미경유 → 슬래시 X. nl-review / nl-ship 은 symlink 없어 자연어 트리거조차 미보장
- 결정: symlink 임시변통 → plugin 정공법(`--plugin-dir`) 으로 전환. 마켓플레이스/공개는 release 검증 시점으로 분리

#### 프로젝트 위치 이동
- `~/Developer/tools/nerdlab-harness` → `~/Developer/own/cc-marketplace/nerdlab-harness` (mv 완료)
- 이유: `cc-marketplace/` 디렉토리 신설, 향후 `nerdlab-*` 시리즈(웹툰·카드뉴스 등) 형제 위치 준비. 폴더명 자체는 `nerdlab-harness` 유지 (suffix 미부여 — 시리즈 분기 시 재고)
- 절대경로 참조 5곳 갱신: `README.md` / `skills/{nl-plan,nl-generate,nl-review}/SKILL.md` / `tasks/coder-reviewer-skills/plan.md`
- `~/.claude/skills/{nl-plan,nl-generate}` symlink 2개는 mv 로 broken — 사용자 직접 제거 예정 (이 세션 cwd 사라져 Bash 차단)
- `README.md` 의 "설치" 섹션(76-85 라인) 본격 교체는 다음 세션에서 정공법 셋업과 함께

#### 방향 재정의 — nl-ship 보류, plan 전후 프로세스 다듬기 우선
- 사용자 인식: 80% 완성. 단 plan 전후의 두 구멍 채워야 ship 진입 가능. 이 하네스는 범용성 X — 사용자 철학대로 흐름이 강제되는 도구라는 정체성을 명문화해야 함
- (A) plan 이전 — 요구사항 정리 단계: 입력 품질이 plan 품질을 결정. 모호한 요구사항 → 모호한 plan. `nl-spec` 신규 단계 또는 plan 자체 검증 강화 (옵션 미정)
- (B) plan 이후 — git 강제 + worktree: `nl-generate` 시작 시 git clean 가드, phase 또는 task 단위 worktree, phase 완료 시 commit, 모든 phase 완료 후 merge. 실패 시 rollback 정책
- (C) `docs/philosophy.md` 강제성 섹션: "이 하네스가 강제하는 것" 명문화. plan-template / reviewer YAML / Phase 분해 / git clean / worktree / 요구사항 ★ 섹션 강제. 범용성 X 라는 정체성 박아둠
- (D) 위 셋 정착 후 nl-ship 본구현 진입. ship 책임 = "이미 만들어진 commit/PR 정리·push" 이지 generate 의 잔여 책임 떠안기 X (책임 경계 명확화)

#### plugin 정공법 셋업 검증 + 마무리 작업
- `claude --plugin-dir .` 로 새 세션 진입 → `/nerdlab-harness:nl-plan` 등 슬래시 4개 정상 노출 확인 (사용자 보고 "plugin 잘나온다")
- broken symlink 2개 제거: `~/.claude/skills/nl-plan`, `~/.claude/skills/nl-generate` (이전 세션 mv 로 깨진 상태)
- `README.md` "설치" 섹션 교체: symlink 안내 → `--plugin-dir` 정공법 + alias 가이드. 슬래시 형식 `/nerdlab-harness:<skill>` 명시
- `README.md` "로드맵" 4개 [x] 갱신 (reviewer/run_phases/옵션 4종/plugin 셋업) + (A)(B)(C) 신규 [ ] 추가

#### 5단계 모델 도입 결정 — Clarify → Context Gather → Plan → Generate → Evaluate
- 사용자 제시 표준 흐름: `Clarify → Context Gather → Plan → Generate → Evaluate`
- 현 하네스 매핑 점검 결과 **구멍 3개**:
  - **(1) Clarify 부재** — 사용자가 요구사항 던지면 `/nl-plan` 이 그대로 plan 생성. 인터랙션 왕복 없음. 모호 입력 → 모호 plan
  - **(2) Context Gather 명세 모호** — `prompts/planner.md` / `prompts/coder.md` 둘 다 누가 언제 모으는지 명시 X. 부트스트랩 단계는 빈 코드베이스라 무영향이었으나, 하네스 사용자 프로젝트는 기존 코드베이스가 본질
  - **(5) Evaluate 자동 게이트 부재** — reviewer 는 LLM 의미 검증만. typecheck/lint/test/build 자동 실행 X → 빌드 깨진 채 phase passed 가능. `--tdd` 도 coder 자율 실행이라 강제력 X
- 기존 (A)(B)(C) 재배치: (A) ↔ (1), (5) 신규, (2) 신규, (B) git 강제는 직교 트랙으로 유지, (C) philosophy 는 위 다 정리되고 마지막
- **작업 순서 결정 (사용자 명시)**: **(1) Clarify → (2) Context Gather → (5) Evaluate** → 그 다음 (B) git → (C) philosophy → nl-ship

#### (1) Clarify 명세 + SKILL 인계 본구현 (1a — 헬퍼/실호출은 1b 로 분리)
- 결정 합의 (사용자 답변):
  - 1-1 = (다) 하이브리드 — clarify 게이트 + 질문 반환
  - 1-2 = (b)+(c) 결합 — 정규식 검증 + reviewer 항목별 status
  - 1-3 = (iii) 부족분만 되묻기
  - 추가: 한 세션 = 한 작업, 메인 세션 대화 맥락 그대로 활용 (시나리오 A/B/C 자연 분기)
- 책임 분할: clarify 는 **메인 세션 직접** (헤드리스 통일 예외) — 사용자 인터랙션 + 세션 맥락 활용이 본질, 헤드리스 single-shot 모델과 충돌. sub agent 도 동일 이유로 부적합 (단일 응답 + 세션 맥락 미보유) — 검토 후 기각
- 입력 ★ 6개 정의: 목적 / 입력 / 출력 / 제약 / 완료조건 / 안 할 것. plan-template 의 출력 ★ (3·4·10) 와는 **다른 차원** — 둘 다 명문화
- 항목별 상태 분류: `filled` / `empty` / `ambiguous` (판정 기준 표 + 예시)
- 질문 절차: `AskUserQuestion` 우선(객관식+자유 묶음), 자유 서술은 산문. 한 라운드에 빈/모호 항목 모두 묶음. 최대 2 라운드 → 초과 시 abort 옵션 (가정 박고 진행 / 작업 취소)
- 추출 결과 투명화 룰: 시나리오 A/B/C 무관 모든 ★ 확정 후 사용자에게 요약 보여주고 진행 확인 (스킵 불가)
- 산출물: 확정 ★ 요약 텍스트 한 덩어리 → planner 헤드리스 user prompt 로 전달. 별도 `clarify.md` 파일 X (plan.md 의 섹션으로 흡수)
- 신규/갱신 파일:
  - `docs/spec/clarify-protocol.md` 신규 (95줄) — 책임/★6/추출 절차/판정/질문/라운드/투명화/산출물/안티패턴
  - `docs/spec/plan-template.md` 갱신 — 입력 ★ vs 출력 ★ 차원 구분 명문화 + ★ 섹션 빈/placeholder 식별 패턴 표 추가 (76줄)
  - `skills/nl-plan/SKILL.md` 갱신 — 1) clarify 2) context gather (TBD) 3) planner 헤드리스 4) ★ 정규식 검증 5) 결과 안내 5단계 흐름 (66줄, 50줄 가이드 살짝 초과 — (2)(5) 추가 시 위임 강화로 함께 정리 메모)
  - `docs/philosophy.md` — "Clarify 예외" 섹션 추가 (헤드리스 통일 원칙 명시적 예외, 이유 3개)
- 검증: unittest 34/34 PASS (코드 미변경 회귀), 링크 정합성 3곳 모두 유효, 파일 길이 합리(95/76/66/70)
- **잔여 (1b 로 분리)**: ★ 섹션 정규식 검증 헬퍼 본구현 (`scripts/validate_plan.py` 또는 `run_phases.py` 안 헬퍼) + 의도적 모호/정리됨 두 케이스로 실호출 검증 + reviewer 항목별 status 강제 (`prompts/reviewer.md` 갱신) — 다음 세션

#### (1b) Clarify 헬퍼 본구현 + reviewer ★ status + SKILL 4단계 연결 (★ /nl-plan → /nl-generate 다섯 번째 실호출, TDD 모드 X)
- 결정 합의 (사용자 답변): 헬퍼 위치 = `scripts/validate_plan.py` 신규 (run_phases.py 안 X) / 검증 실패 정책 = 사용자 통지만 + 진행 차단 X
- 시나리오 A 그 자체 — 메인이 TODO.md 의 작업 단위에서 입력 ★ 6개 추출 → 사용자에게 표로 요약 + 추가 결정 2개 묶음 질문 (헬퍼 위치 / 실패 정책) → 응답 후 라운드 0 통과 (요약 확인 1회는 라운드 카운트 X). 정리된 입력 케이스 실호출 검증 ✓
- `/nl-plan` 헤드리스 호출 → `tasks/clarify-helper-impl/plan.md` 자동 생성 (phases 2 직렬, TDD no, 110줄)
- **부트스트랩 발견 — `parse_phases` / `_slice_phase_table` 정규식이 번호 prefix 헤더 미지원**: planner 가 이번 plan 헤더에 `## 10. Phase 분해 ★` 형식으로 번호를 prefix 했는데(이전 plan 들은 우연히 모두 prefix 없었음) 정규식이 매치 못 해 `ValueError: 'Phase 분해' 섹션을 찾지 못함` 으로 즉시 실패 (exit 1). 사용자에게 A(plan 우회)/B(근본 수정)/C(plan 재작성) 3안 제시 → **B 선택**
- 메인 직접 부트스트랩 수정: `scripts/run_phases.py:130, 317` 두 정규식에 `(?:\d+\.\s+)?` 선택적 번호 prefix 추가 + `tests/test_run_phases.py` 의 `TestParsePhasesHeaderAnchor` 에 `test_numbered_section_prefix_is_accepted` 회귀 테스트 1개 추가 (parse_phases + _slice_phase_table 동시 검증) → unittest 34 → 35 PASS
- `/nl-generate tasks/clarify-helper-impl/plan.md` 재호출 → exit 0
  - **Phase 1 (helper-and-tests)**: round 1 passed. `scripts/validate_plan.py` (147줄) 신규 — `validate_plan_stars(plan_path) -> list[str]` + `_slice_section`(`(?:\d+\.\s+)?` prefix 허용) + `_is_section_3/4/10_empty` 3개 + `_split_table_data_rows` + `_row_all_placeholder` + `main(argv)` CLI. 외부 의존 0(re/sys/pathlib). `tests/test_validate_plan.py` (309줄, 36 테스트) 신규 — 정상/빈/placeholder/표 헤더만/데이터 행 모두 `-` 등 양음성 커버
  - **Phase 2 (docs-and-skill-wiring)**: round 1 passed. `prompts/reviewer.md` plan 모드에 항목 6 추가 + `star_sections` 출력 필드 (present/missing/ambiguous) 신설. `skills/nl-plan/SKILL.md` 단계 4 본문 갱신 — `python scripts/validate_plan.py` 호출 + 통지만 (자동 차단 X)
- 검증 4가지 통과:
  - unittest: 71/71 PASS (기존 35 + 신규 36 + 부트스트랩 회귀 1)
  - `run_phases.py --help` 회귀 없음
  - `validate_plan.py` CLI 4 케이스: 정상 plan / 빈 ★ plan(`이번에 안 할 것, 트레이드오프, Phase 분해` 3개 정확 보고) / 파일 없음(stderr + exit 2) / 인자 누락(stderr + exit 2)
  - 실호출 정리된 입력 케이스 — 이번 세션 자체가 시나리오 A. 의도적 모호 입력 케이스는 다음 세션 별도 시뮬레이션
- 트레이드오프 인상: 헬퍼를 `scripts/validate_plan.py` 별도 모듈로 분리한 결정 → run_phases.py 의 phase 오케스트레이션 책임과 plan 검증 책임 명확 분리. 단 `(?:\d+\.\s+)?` 정규식 패턴이 두 파일에 중복 (`run_phases.py:130, 317` + `validate_plan.py:18`). 향후 헤더 형식 바뀌면 3곳 동기화 필요 — 헬퍼화는 본 작업 범위 밖
- 잠재 결함 1: `_slice_section` 의 정규식이 헤더 라인 끝까지 `[^\n]*` 로 흡수해 `★` / 부가 텍스트 모두 통과. plan-template 변경 없으면 안전
- 잠재 결함 2: 의도적 모호 입력 실호출 케이스는 미검증 — 다음 세션 진입 시 시뮬레이션 권장 (예: `/nl-plan "X 만들어줘"` → clarify 라운드 1 AskUserQuestion 질문 묶음 반환)

#### (2) Context Gather 본구현 (★ /nl-plan → /nl-generate 여섯 번째 실호출, TDD no)
- 결정 합의 (사용자 답변): 2-1 = 하이브리드 (planner 직전 / Phase A 메인 직접 + Phase B 헤드리스 익스플로러) / 2-2 = ★ 3개 (영향 파일 / 관련 시그니처 / 기존 패턴) / 2-3 = plan.md `## Context` 섹션 통합 (별도 파일 X) / 2-4 = 자동 감지 (`.git` 존재 + `git ls-files | wc -l`)
- `/nl-plan` 헤드리스 호출 → `tasks/context-gather-impl/plan.md` 자동 생성 (phases 2 직렬, TDD no, 145줄). 본 plan 자체는 빈 코드 가정 아님 — `## 11. Context ★` 섹션을 `none (empty codebase)` 한 줄로 보강해 자기 검증 일관성 확보 (phase 2 reviewer 가 minor 지적 후 보강)
- `/nl-generate tasks/context-gather-impl/plan.md` → `python3 scripts/run_phases.py` background → exit 0
  - **Phase 1 (static-assets)**: round 1 passed. `docs/spec/context-protocol.md` (96줄) 신규 — Phase A 결정적 명령 / Phase B 출력 ★ 3개 / 빈 코드 스킵 룰 / 안티패턴. `docs/spec/plan-template.md` 갱신 — `## Context` ★ 섹션 (11번째 필수) + 빈 판정 표 행 추가. `prompts/explorer.md` (49줄) 신규 — Phase B 시스템 프롬프트, 도구 권한 Read/Grep/Glob (Write/Edit/Bash X), 출력 ★ 3개 강제. reviewer status: ok
  - **Phase 2 (helper-and-skill-wiring)**: round 1 passed. `scripts/validate_plan.py` 147→177줄 (`SECTION_CONTEXT` 상수 + `_EMPTY_CODEBASE_LITERAL = "none (empty codebase)"` + `_is_section_context_empty(body)` + `validate_plan_stars` 검증 대상 3→4 확장). `tests/test_validate_plan.py` +12 케이스. `prompts/reviewer.md` plan 모드 `star_sections` 출력 키 3→4 (Context 추가). `skills/nl-plan/SKILL.md` 66→113줄 (단계 2 본구현 — 자동 감지 + Phase A + Phase B + plan 통합). reviewer status: ok, minor issue 1건 (본 plan 자기 자신 Context 섹션 누락 — 보강으로 해결)
- 검증 4가지 통과:
  - unittest: **88/88 PASS** (기존 71 + Context 신규 17)
  - `validate_plan.py` CLI: 본 plan(`tasks/context-gather-impl/plan.md`) — `★ 섹션 검증 통과` (Context = `none (empty codebase)` 한 줄 합법 인정)
  - `run_phases.py --help` 회귀 없음
  - 사람 눈 확인 4건 모두 통과 (context-protocol.md / explorer.md / SKILL.md 단계 2 / reviewer.md star_sections)
- 트레이드오프 인상: **Phase A 메인 직접 / Phase B 만 헤드리스** 결정으로 결정적 추출(git ls-files / grep)은 재현·디버그 가능, 비결정 LLM 추론은 격리. clarify 와 동일한 "헤드리스 통일 원칙의 명시적 예외" 패턴 정착 — 익스플로러 도구 권한 Read/Grep/Glob 만으로 읽기 전용 강제. Context 결과를 별도 파일이 아닌 plan.md `## Context` 섹션에 통합 → reviewer/coder 가 plan 한 파일만 읽으면 됨
- 잠재 결함 1: `skills/nl-plan/SKILL.md` 113줄 — 50줄 가이드 한참 초과. 단계 2 추가로 인한 자연스러운 증가지만 위임 강화 필요. **다음 단계 작업(5/B/C) 진입 시 SKILL.md 위임 정리 함께 처리**
- 잠재 결함 2: 빈 코드 스킵 실호출 검증은 미수행 — 외부 테스트 프로젝트 트랙으로 분리 (사용자 명시: 플러그인 배포 후)

#### (5) Evaluate 본구현 (★ /nl-plan → /nl-generate 일곱 번째 실호출, TDD yes, phase 3 직렬)
- 결정 합의 (사용자 추천 일괄 채택): 5-1=(b) phase 종료 게이트 / 5-2=(a) plan-template `Evaluate ★` 신규 필드 / 5-3=(b) eval 결과 → reviewer 합성 issue dict → coder 재호출 / 5-4=typecheck/lint/test/build 다중 직렬 + 첫 실패 stop / 5-5=(b) 빈 명령 `none` 명시 강제 (Context `none (empty codebase)` 패턴 일관)
- Context Gather: 자동 감지가 `.git` 부재로 빈 코드 잘못 판정 → 사용자 결정으로 강제 실행 (find 로 파일 스캔 → Phase A 메인 직접 + Phase B 헤드리스 익스플로러). plan 품질 보존 — explorer 가 영향 파일 7개 + 시그니처 6개(`run_phase`/`_decide_phase_outcome`/`_run_claude`/`_write_round_log`/`validate_plan_stars`/`_is_section_context_empty`) + 기존 패턴 5개(합성 review dict / 섹션 슬라이스 / subprocess.run / star_sections / round 로그 chunk) 정확 추출
- `/nl-plan` 헤드리스 호출 → `tasks/add-evaluate-gate/plan.md` 자동 생성 (phases 3 직렬, TDD yes, 127줄). planner 가 Phase B Context 결과를 plan `## Context` 섹션에 자동 통합
- `/nl-generate tasks/add-evaluate-gate/plan.md` 1차 호출 → exit 1 즉시 실패 (`ValueError: invalid literal for int() with base 10: '없음'`)
- **부트스트랩 발견 — `parse_phases` depends 컬럼 파서 결함**: planner 가 만든 의존 컬럼이 "없음" 한국어 + "1 (plan-template 형식·validate_plan 통과 필요)" 괄호 부가설명 형식인데, 기존 정규식이 빈 키워드 셋 `{"—","-","–"}` 만 처리 + 순수 정수 토큰만 가정. 사용자에게 A(plan 우회)/B(근본 수정)/C(plan 재작성) 3안 제시 → **B 선택** (이전 두 부트스트랩 — 1b 번호 prefix / reviewer-phase-slice 행 앵커 — 와 동일 패턴)
- 메인 직접 부트스트랩 수정: `scripts/run_phases.py:170-177` — 괄호 이후 부가설명 제거(`re.sub(r"\s*\(.*$", "", depends_raw)`) + 빈 키워드 셋 확장(`{"—","-","–","없음","none","x"}`, 대소문자 무시) + 정수 토큰만 추출(`re.findall(r"\d+", depends_clean)`). `tests/test_run_phases.py:294` 신규 `TestParsePhasesDependsColumn` 5개 — 한국어 키워드 / 괄호 부가설명 / em-dash / 다중 정수 / 괄호 안 숫자 무시. unittest 88 → 93 PASS
- `/nl-generate` 재호출 → exit 0 (총 22분: 08:32→08:54)
  - **Phase 1 (스펙·검증, 12분)**: round 1 passed. `docs/spec/plan-template.md` 12번째 ★ 섹션 `## Evaluate ★` 신설 + 빈 판정 표 행 (76→80줄). `scripts/validate_plan.py` `SECTION_EVALUATE` + `_is_section_evaluate_empty` + `validate_plan_stars` 5-섹션 확장 (177→196줄). `tests/test_validate_plan.py` Evaluate 빈/none/명령 케이스 (≥4 신규). 보너스: phase 1 coder 가 본 plan 자체 `## Evaluate ★ = none` 섹션도 자동 보강해 자기 검증 통과 (trade-off 5번 그대로)
  - **Phase 2 (실행 게이트, 8분)**: round 1 passed. `scripts/run_phases.py` (~700→842줄) `_run_evaluate(commands, cwd) -> tuple[bool, str]` 헬퍼 + `_make_eval_review(eval_log, round_num, max_rounds) -> dict` 헬퍼 + `run_phase` reviewer ok 직후 분기 + `_write_round_log` eval 섹션 + `EVAL_TIMEOUT=300` + `_EVALUATE_SECTION_RE`. `tests/test_run_phases.py` `_run_evaluate` 다중 직렬·첫 실패 stop·exit code 전파·round 재진입 시나리오
  - **Phase 3 (프롬프트·SKILL 정합, 2분)**: round 1 passed. `prompts/reviewer.md` (75→106줄) `star_sections` 키 4→5 (Evaluate 추가) + eval 실패 입력 가이드. `skills/nl-plan/SKILL.md` (113→145줄) 단계 4 검증 결과에 Evaluate 추가 + planner 위임 시 Evaluate 채우기 가이드
- 검증 4가지 통과:
  - **unittest: 116/116 PASS** (기존 88 + 부트스트랩 5(depends) + Evaluate 신규 23)
  - `validate_plan.py tasks/add-evaluate-gate/plan.md` → `★ 섹션 검증 통과` (Evaluate=none 합법 인정)
  - `run_phases.py --help` 회귀 없음
  - 모든 phase round 1 통과 — coder/reviewer 재진입 0회 (plan 품질 + Context Gather 효과)
- 트레이드오프 인상: **eval 실패를 reviewer 합성 issue dict 로 변환** 결정 → 기존 BLOCKED/exit/parse-error 합성 패턴 그대로 재사용해 phase status 머신 복잡도 증가 회피. **헤드리스 통일 명시적 예외**(eval 명령은 `subprocess.run` 직접) → clarify / Phase A 와 동일 패턴 정착. 본 작업 plan 자체 `Evaluate=none` → 하네스 자체 진화는 외부 빌드 도구 없음 (validate_plan / unittest 가 검증), self-eval round 재진입은 단위 테스트로 대체
- 잠재 결함 1: `skills/nl-plan/SKILL.md` 113→**145줄**. 50줄 가이드 초과 폭 더 커짐. (B)/(C) 진입 시 위임 강화 필수
- 잠재 결함 2: 의도적 typecheck 깨지는 외부 코드 실호출 통합 검증 미수행 — 외부 트랙으로 분리 (1b 모호 입력 / 2 빈 코드 스킵 과 같이 묶어서 외부 프로젝트 셋업 후)
- 잠재 결함 3: `_run_evaluate` 의 `cwd` 가 `task_dir.parent.parent` 가정 — 본 작업 plan 의 데이터 흐름 #2 명시. 향후 외부 프로젝트에서 다른 위치에서 호출되면 재검토 필요

#### `skills/nl-plan/SKILL.md` 위임 강화 (단독 작업, 본구현·검증 메인 직접)
- 목적: 145줄 → 50줄 가이드에 가깝게 압축. (B) git 강제 진입 전 비용 낮추기. 단계 추가 시 200줄 돌파 위험 차단
- 위임 전략 3가지:
  - **(1) Evaluate 작성 가이드 30줄** → SKILL.md 단계 4에서 빼고 `docs/spec/plan-template.md` 의 "Evaluate 작성 가이드" 섹션으로 이동 (단일 진실 출처 원칙: plan 형식은 plan-template.md 가 책임)
  - **(2) Context Gather 본문 25줄** → `docs/spec/context-protocol.md` 위임 강화. SKILL.md 에는 빈 코드 자동 감지 / Phase A / Phase B 호출 명령 (cat explorer.md) / plan.md `## Context` 통합 4단계만 핵심 한 줄씩
  - **(3) Clarify 단계** → 이미 spec 위임 잘 됨, 핵심만 압축 (헤드리스 X 이유 한 줄)
- 신규 갱신 파일:
  - `docs/spec/plan-template.md` 80→**112줄** — "Evaluate 작성 가이드" 섹션 추가 (작성 룰 / 채운 예시 / `none` 예시 / `validate_plan.py` 판정 표)
  - `skills/nl-plan/SKILL.md` 145→**84줄** — 단계 1·2·4 위임 강화. 단계 3·5 호출 명령은 그대로 유지
- 검증 4가지 통과:
  - **unittest: 116/116 PASS** (코드 미변경 회귀 없음)
  - `validate_plan.py tasks/add-evaluate-gate/plan.md` → `★ 섹션 검증 통과` (기존 plan 검증 회귀 없음)
  - `validate_plan.py tasks/context-gather-impl/plan.md` → `빈 ★ 섹션: ## Evaluate ★` (Evaluate 추가 전 plan 이라 정상)
  - `run_phases.py --help` 회귀 없음 (기존 인자 6개 그대로)
- 트레이드오프 인상: Evaluate 가이드 plan-template 이동 결정 → SKILL 은 흐름 / spec 은 형식 책임 분리 명확. 단일 진실 출처 원칙 준수. 단 plan-template.md 80→112줄 (40% 증가)는 "단일 진실 출처는 풍부해도 OK" 룰 적용
- 잠재 결함: SKILL.md 84줄도 50줄 가이드 살짝 초과(+34). 단계 5개 + frontmatter + 부가 2 섹션 합쳐 합리적 한도. 추가 단계 도입 시 spec 신규 분리 필요

#### (B0) `/nl-setup` SKILL 본구현 (★ /nl-plan → /nl-generate 여덟 번째 실호출, TDD no, phase 1)
- 결정 합의 (사용자 답변): (B0) `/nl-setup` 1회성 셋업 + (B1) `/nl-generate` git 가드 트랙 분리 / 디폴트 4 항목(CLAUDE.md, ADR template, architecture.md, coding-conventions.md) + PRD 옵션 / AskUserQuestion 인터랙티브 1라운드 묶음 / 충돌 skip + 리포트 (--force X) / git 미설치 안내만 / `.git` 미존재 시 자동 init / 메인 직접 (헤드리스 X) / nl-* 통합 룰은 (B1) 후
- 부트스트랩 1: 하네스 자체 비-git 상태 → 메인이 `git init` 직접. Context Gather Phase A 가 git ls-files 0 개 케이스라 `find` fallback 사용 (context-protocol.md 미갱신, 본 작업 한정)
- 부트스트랩 2: Phase B 헤드리스 explorer 호출 대신 메인 직접 작성 (git 추적 0 상태에선 explorer 의 grep 도 빈 결과). plan.md `## Context` 섹션 메인이 직접 박음
- `/nl-plan` 헤드리스 호출 → `tasks/nl-setup-skill/plan.md` 자동 생성 (phases 1, TDD no, 126줄). 12 섹션 모두 채워짐
- **부트스트랩 발견 — `validate_plan.py` numbered list 미인식**: `_is_section_3_empty` 정규식 `^\s*-\s*` 가 bullet `-` 만 인식. plan-template 은 numbered/bullet 둘 다 명시 안 함이고 planner 가 numbered list 선택해도 합법. 사용자에게 A/B/C 3안 제시 → **B 선택** (이전 부트스트랩 4회와 동일 패턴)
- 메인 직접 부트스트랩 수정: `scripts/validate_plan.py:66` — `^\s*-\s*` → `^\s*(?:[-*]|\d+\.)\s+` (numbered + asterisk + dash 모두 인식). `tests/test_validate_plan.py` `TestIsSection3Empty` +3 (numbered valid / numbered placeholder / asterisk valid). unittest 116 → **119 PASS**
- `/nl-generate tasks/nl-setup-skill/plan.md` background → exit 0 (6분 6초: 09:25:40 → 09:31:46)
  - **Phase 1 (단일)**: round 1 passed. coder 가 신규 9 파일 한 번에 생성:
    - `skills/nl-setup/SKILL.md` (77줄) — frontmatter + 5단계(git 검사 / .git init / AskUserQuestion / 파일 복사 / 리포트) + spec 위임. nl-plan 패턴 그대로
    - `docs/spec/setup-protocol.md` (132줄) — Step 1~5 본문 + 의사코드 + 안티패턴 7행
    - `templates/CLAUDE.md` (27줄) — **1차안 위배 발견 후 메인 수정**
    - `templates/docs/architecture.md` (18줄) — 4섹션 placeholder
    - `templates/docs/coding-conventions.md` (33줄) — 4섹션 + Conventional Commits 표
    - `templates/docs/adr/0000-template.md` (18줄) — ADR 표준 4섹션
    - `templates/docs/prd.md` (18줄) — 4섹션 placeholder
    - `README.md` 수정 — SKILL 디렉토리 트리·표·슬래시 명령·로드맵 4곳 갱신
  - reviewer status: ok. Evaluate 게이트 자동 실행 → unittest 119/119 PASS
- **부트스트랩 발견 2 — planner→coder 본문 전달 누락**: `templates/CLAUDE.md` 의 GitHub flow 1차안 본문이 planner user prompt 에는 박혔지만 plan.md 의 "변경 파일" 줄에는 `본문은 1차안 그대로` 만 적힘 → coder 가 1차안 못 받고 자율 작성 → "feature → develop → main (GitHub flow)" 박음. **합의 위배** (합의: develop 브랜치 X). 메인이 직접 수정해 합의안 본문 박음
- 검증 4가지 통과:
  - **unittest: 119/119 PASS** (기존 116 + 신규 3)
  - `validate_plan.py tasks/nl-setup-skill/plan.md` → `★ 섹션 검증 통과`
  - 기존 plan 회귀: `add-evaluate-gate/plan.md` 통과
  - 사람 눈: SKILL/spec/templates 모두 패턴 따름. CLAUDE.md 1건만 수정 필요 → 처리됨
- 트레이드오프 인상: (B0)(B1) 트랙 분리 결정 → 1회성 셋업과 매 호출 가드 책임 명확 분리. 충돌 skip 정책 + 항목별 인터랙티브 패턴이 신규 — 후속 SKILL 이 참조할 1차 사례. Phase A/B 메인 직접 부트스트랩은 git ls-files 0 케이스에 대한 임시 처리 — context-protocol.md 갱신은 후속
- 잠재 결함 1: planner 가 plan.md 에 "변경 파일 본문 1차안" 인라인 인용 안 하면 coder 가 합의 본문 못 받음. 본 plan 처럼 사용자 합의 본문이 있는 케이스에서는 plan 의 "변경 파일" 항목 본문 전체를 plan.md 에 박는 가이드 필요. **planner 프롬프트 갱신 후속 작업** 후보
- 잠재 결함 2: context-protocol.md 가 git ls-files 0 (init 직후, 추적 0 상태) 케이스를 명시 안 함. 빈 코드(`.git` 없음 또는 추적 0)와 다른 케이스 — 명세 갱신 필요
- 잠재 결함 3: 하네스 self-apply 실호출(이미 .git 존재 → init 건너뛰고 항목 묻기) 미수행. 외부 트랙 묶음(1b 모호 / 2 빈 코드 / 5 typecheck)에 추가

#### planner 프롬프트 갱신 (단발 작업, 메인 직접)
- 직전 (B0) 부트스트랩 발견 2 (1차안 본문 전달 누락 → coder 합의 위배) 재발 방지
- `prompts/planner.md` 70→72줄
  - **절대 규칙 6 추가** (라인 14): user prompt 에 1차안 본문 있으면 plan.md `## 6. 변경 파일` 항목 바로 아래에 `**본문 1차안:**` 헤더 + 코드 블록 인라인 인용. 위반 사례 (GitHub flow → git flow) 명시
  - **핸드오프 한 줄 보강** (라인 69): coder 가 따라가는 항목에 `변경 파일 본문 1차안 인용` 추가
- 검증: unittest 119/119 PASS 그대로 / 기존 plan 2개 회귀 통과 / planner.md 사람 눈
- 트레이드오프 인상: 절대 규칙 6 추가는 시스템 프롬프트 길이 +2 줄. 단위 테스트 X (LLM 행동 변경) — 다음 SKILL 호출 시 자연스러운 회귀 검증
- 잠재 결함: planner 가 **본문 없는 user prompt** 에서도 빈 코드 블록을 박을 위험. 룰에 "본문 박았으면" 조건 명시했지만 LLM 해석 변형 가능. 다음 SKILL 본구현 시 행동 관찰

#### (B1) `/nl-generate` git 가드 본구현 (★ /nl-plan → /nl-generate 아홉 번째 실호출, TDD yes, phase 2 직렬)
- 결정 합의 (사용자 추천 일괄 채택): 1=dirty 차단 / 2=main 자동 feat 분기 / 3=phase passed 자동 commit / 4=실패 시 그대로+리포트(reset X) / 5=worktree 안 씀 / 6=push·rebase·merge=nl-ship 책임 (범위 X) / A=`.git` 미존재 차단+/nl-setup 안내 / B=main 자동 분기 / C=`feat(<task>): phase-<N> <name>` / D=phase passed 1회 commit (round 중간 X)
- **planner 갱신 첫 적용 효과**: clarify ★ 6개에 1차안 본문 3종(commit 메시지 / dirty 차단 / .git 미존재 / phase failed 리포트) 코드 블록으로 user prompt 에 박음 → planner 가 plan.md 49 라인에 `### 변경 파일 본문 1차안` 헤더 + 3종 코드 블록 정확 인용. **(B0) 의 CLAUDE.md 합의 위배 같은 사고 재발 X**
- `/nl-plan` 헤드리스 호출 → `tasks/git-guard-impl/plan.md` 자동 생성 (phases 2 직렬, TDD yes, 160줄)
- `/nl-generate tasks/git-guard-impl/plan.md` background → exit 0 (7분 42초: 09:50:09 → 09:57:51)
  - **Phase 1 (스펙·헬퍼·테스트, ~3분 13초)**: round 1 passed. coder 가 헬퍼 4개 신설:
    - `_check_git_state(cwd) -> tuple[bool, str]` (702) — `.git` 존재 ∧ clean tree 검증
    - `_ensure_feature_branch(task_name, cwd) -> str` (728) — main/master 면 자동 `feat/<task>` 분기
    - `_commit_phase(task_name, phase, cwd) -> str` (750) — `git add -A` + commit, 메시지 1차안 그대로
    - `_render_failure_report(phase, last_good_hash, reason) -> str` (776) — stderr 안내
    - `EXIT_CODE_GIT_GUARD = 6` (48)
    - `docs/spec/git-guard-protocol.md` 신규 (83줄) — 절차 명세
    - `tests/test_run_phases.py` `TestGitGuard` 5 시나리오 (dirty/.git 미존재/main 분기/passed commit/failed 리포트)
  - **Phase 2 (main 통합·문서, ~4분 29초)**: round 1 passed. coder 가 본 헬퍼들을 main() 흐름에 연결:
    - `main()` 873-878 가드 분기 (plan_path 검증 직후)
    - `main()` 878 `_ensure_feature_branch` 호출
    - `run_phase` passed 직후 `_commit_phase` 926 호출
    - `run_phase` failed/escalated 직후 `_render_failure_report` 930 stderr
    - `skills/nl-generate/SKILL.md` 49→59줄 (가드 룰 명시)
    - `README.md` 가드 동작 한 단락 갱신
- 검증 5가지 통과:
  - **unittest: 119 → 126/126 PASS** (TDD 신규 7개: TestGitGuard 5 + 보조 2)
  - `validate_plan.py tasks/git-guard-impl/plan.md` → `★ 섹션 검증 통과`
  - `--help` 회귀 없음 (기존 인자 6개 그대로)
  - **자기 검증 ✓**: 본 작업 직후 `python3 scripts/run_phases.py tasks/git-guard-impl/plan.md --resume` → `git 가드: working tree 가 dirty...` + exit 6. 1차안 메시지 정확 + EXIT_CODE 정확
  - 사람 눈: 헬퍼 4개 모두 plan 시그니처 그대로 / main 분기 위치 정확 / stdout 5줄 5단계 모두 정합
- 트레이드오프 인상: **헬퍼 4개 분리 + main 진입 분기** 결정 → 단위 테스트 5 시나리오 모두 mock 으로 격리 가능. EXIT_CODE_GIT_GUARD = 6 신설 → 기존 EXIT_CODE_INLINE_INVALID = 5 패턴 그대로 재사용. `_commit_phase` 의 `git add -A` 정책 → 본 phase 외의 변경도 같이 commit 될 위험 있지만 가드 1=dirty 차단 덕에 phase 시작 시 clean → phase 작업분만 add -A 됨. 최소 복잡도
- **자기 정합성 닭-달걀 한계**: 본 작업 시점엔 가드 미구현 → 본 작업 자체는 main 브랜치 + commit 0개로 끝남 (가드 적용 X). **다음 작업부터 가드 작동** — 이미 자기 검증으로 dirty 차단 확인. 본 작업의 변경분 commit 은 사용자 결정 (수동 / 다음 세션)
- 잠재 결함 1: clean tree 에서 정상 호출 → 자동 feat 분기 + phase passed commit 실호출 검증은 미수행 (하네스 dirty 라 차단됨). **외부 검증 트랙**(1b 모호 / 2 빈 코드 / 5 typecheck / B0 self-apply / B1 clean-tree happy-path)에 추가
- 잠재 결함 2: `_commit_phase` 가 `git add -A` 사용 → 사용자가 작업 중인 untracked 파일도 휘말림. 가드 1 dirty 차단 덕에 phase 시작 시 clean 보장이지만, phase 도중 사용자가 다른 터미널에서 파일 추가하면 race. 다중 task race condition 처리 안 함 명시(plan 안 할 것) — 범위 외
- 잠재 결함 3: phase 도중 git 명령이 실패하면(예: 사용자 user.email 미설정) `_commit_phase` subprocess 가 raise. 본 plan 의 안 할 것 "GPG / 사용자 user.name 검사" 명시 — 사용자 git 설정 책임. 향후 (B0) `/nl-setup` 에서 git config 검사 추가 검토 후속

#### (C) philosophy 강제성 섹션 명문화 (단발 작업, 메인 직접)
- 사용자 추천 일괄 채택: 7개 항목 단일 표 / 신규 섹션 6 으로 추가 / "범용성 X" 한 단락 섹션 6 맨 위 / `nl-review` SKILL frontmatter 같이 정리
- `docs/philosophy.md` 71→**93줄** — 섹션 6 "이 하네스가 강제하는 것" 신설:
  - "범용성 X — 헤드리스 격리 + 단계 분리 + 강제 입출력 따르려는 사람 위한 도구" 한 단락 + "강제는 자유를 줄이는 게 아니라 흐름이 깨질 가능성을 차단해 매 호출마다 같은 품질" 정체성 박음
  - 강제 항목 7개 표 (강제 항목 / 강제 위치 / 위반 시):
    1. plan-template 12개 ★ 섹션 — `validate_plan.py` — 단계 4 통지
    2. Clarify 입력 ★ 6개 — 메인 직접(헤드리스 예외) — planner 호출 차단
    3. Context Gather Phase A+B — `/nl-plan` 단계 2 — `## Context` 누락 → reviewer 지적
    4. reviewer YAML 스키마 — `prompts/reviewer.md` — parse 실패 → 합성 escalate
    5. Evaluate 게이트 — `_run_evaluate` — 합성 issue → coder 재호출
    6. git 가드 — `_check_git_state` 등 — exit 6 + 진입 차단
    7. 헤드리스 통일 — 모든 prompts/SKILL — 자동 가드 X (철학)
  - 단일 진실 출처 매핑 (1·2·3·4·5·6 → spec/{plan-template, clarify-protocol, context-protocol, reviewer-output, git-guard-protocol}.md / 7 → §3)
  - "강제 항목 추가/완화/제거 시 본 표 + spec 함께 갱신, SKILL/prompt 본문에 강제 룰 중복 X" (단일 진실 출처 §4 재인용)
- `skills/nl-review/SKILL.md` frontmatter description "reviewer 서브에이전트(Opus)로" → "헤드리스 reviewer(Opus)로" 정정 (헤드리스 전환 후 부정확했던 표현)
- 검증 4가지 통과:
  - **unittest: 126/126 PASS** (코드 미변경 회귀 없음)
  - `validate_plan.py` 회귀 없음 (별도 호출 — 마지막 출력 `★ 섹션 검증 통과`)
  - spec 5개 모두 존재 (philosophy.md 표 매핑한 plan-template/clarify-protocol/context-protocol/reviewer-output/git-guard-protocol — setup-protocol 포함 6개) → 링크 정합성 ✓
  - 사람 눈: philosophy.md 93줄 (5섹션 + 신규 6 = 6섹션 일관) / nl-review SKILL.md 55줄 (frontmatter 1줄만 변경)
- 트레이드오프 인상: 강제 항목을 한 표로 묶는 결정 → 추가/제거 시 한 곳만 갱신 + 사용자가 "이 도구가 뭘 강제하는지" 한 눈에 파악 가능. 단일 진실 출처 매핑 한 줄로 spec 책임 분리 재확인. nl-review frontmatter 정리는 끼워넣기 (별도 작업 분리 X) — 한 트랙 묶음 효율
- 자기 정합성: 본 작업도 git 가드 안 탐 (메인 직접, /nl-generate 미경유). 가드 작동은 다음 /nl-generate 호출부터

#### nl-ship 워크플로우 GitHub flow 정렬 (단발 작업, 메인 직접)
- 사용자 지적: ~/.claude/CLAUDE.md 글로벌 룰의 옛 워크플로우(develop 머지)가 컨텍스트에 자동 주입되어 하네스 내부 표현에 잔존. 사용자 현재 워크플로우는 GitHub flow (develop 브랜치 X — (B0) templates/CLAUDE.md 합의 일치)
- grep 발견 4곳 → 활성 모순 3곳 수정 + 1곳 보존:
  - `skills/nl-ship/SKILL.md:3` frontmatter "commit → develop merge → push → main rebase → PR" → "commit → push → main PR (squash merge)"
  - `skills/nl-ship/SKILL.md:10` "feature → develop → main 자동화" → "feat/<task> → main PR (GitHub flow, squash merge) 자동화" + squash-merge-convention.md 자산 추가
  - `TODO.md:439` 다음 세션 가이드: "develop 머지 / main rebase" → "main PR (squash merge) + commit-message 위임"
  - `TODO.md:301` Done 기록 보존 (옛 사고 시계열 역사)
- commit `52ac283` push 완료. nl-ship 본구현 진입 전 전제 정렬

#### nl-ship 본구현 (★ /nl-plan → /nl-generate 열 번째 실호출, TDD no, phase 2 직렬)
- 결정 합의 (사용자 추천 일괄 채택): A=phase 미완료 stderr 경고만 / B=메인 직접(헤드리스 X) / C=/nl-plan→/nl-generate 사이클 / D=PR base branch 자동 감지(`gh repo view --json defaultBranchRef`) / E=`--draft` 옵션 / F=첫 push -u 자동
- `/nl-plan` 헤드리스 호출 → `tasks/nl-ship-impl/plan.md` 자동 생성 (phases 2 직렬, TDD no, 164줄). planner 가 사용자 입력 ★ 6 + 추가 결정 + 본문 1차안 + Context Gather 결과를 plan 통합. validate_plan 통과
- `/nl-generate tasks/nl-ship-impl/plan.md` background → exit 0 (~5분)
  - **자동 git 가드 작동 ✓**: main 브랜치 + clean tree → `feat/nl-ship-impl` 자동 분기
  - **Phase 1 (spec-and-skill)**: round 1 passed. coder 가 `skills/nl-ship/SKILL.md` placeholder 16줄 → 본구현 55줄 교체 + `docs/spec/ship-protocol.md` 89줄 신규 (Step 1~5 본문 + 의사코드 + 안티패턴). reviewer status: ok. 자동 commit `6af9d3f`
  - **Phase 2 (docs-integration)**: round 1 passed. coder 가 `README.md` 154→157줄 갱신 (디렉토리 트리 nl-ship 주석 / 파이프라인 다이어그램 / 명령 표 / 사용 흐름). reviewer status: ok. 자동 commit `779086c`
- 검증 4가지 통과:
  - **unittest: 126/126 PASS** (코드 미변경 회귀 없음)
  - `validate_plan.py tasks/nl-ship-impl/plan.md` → `★ 섹션 검증 통과`
  - 사람 눈: SKILL 5단계(사전 검사 / push / PR 본문 / gh pr create / URL 출력) + ship-protocol.md 단일 진실 출처 + README 4곳 모두 정합
  - 자동 commit 2개 정확 (feat 메시지 형식 + phase 단위)
- **★ self-test 메타 검증 통과 ✓**: 본 SKILL 본구현 직후 본 SKILL 호출(`/nerdlab-harness:nl-ship`)로 본 SKILL 의 PR 생성 → 머지
  - 사전 검사: `gh --version` 2.89.0 / `git status --porcelain` clean / `git branch --show-current` feat/nl-ship-impl (main 아님) → 통과
  - push: `git push -u origin feat/nl-ship-impl` 신규 브랜치 생성 + upstream 추적
  - base branch: `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name` → `main`
  - PR 생성: `gh pr create` → https://github.com/nerdlab-logan/nerdlab-cc-harness/pull/1
  - PR 머지: `gh pr merge 1 --squash --delete-branch` → squash commit `4e01ac1` (메시지 형식: `feat(nl-ship): SKILL 본구현으로 main PR(squash merge) 자동 생성 (#1)` + 변경 요약 4 bullet, ~/.claude/docs/git/squash-merge-convention.md 형식 정확)
  - 로컬 동기화: `git checkout main && git pull` (Already up to date — gh merge 가 main 자동 동기화) + `git fetch --prune` 으로 stale `origin/feat/nl-ship-impl` 정리
- 트레이드오프 인상: **메인 직접(헤드리스 X) + commit-message 스킬 위임** 결정 → gh CLI 인터랙션 + 메인 컨텍스트 청결 (stdout 5줄 압축) 둘 다 달성. SKILL 5단계 = 다른 SKILL 본구현(nl-plan/nl-generate/nl-review/nl-setup) 패턴 그대로. self-test 가능한 구조 — 본 SKILL 이 본 PR 을 만든 첫 사례, 강제 흐름의 자기 검증 패턴 정착
- 잠재 결함 1: PR 본문 생성 단계 commit-message 스킬 위임은 명세만, self-test 에선 메인이 직접 PR 본문 작성. commit-message SKILL 실호출 위임은 다음 사용 시 검증 (외부 트랙)
- 잠재 결함 2: phase 미완료(escalate 잔여) 시 stderr 경고만 정책은 명세만, 실호출 검증 미수행. 외부 트랙 묶음 추가

---

## 2026-04-28

### Done

#### 외부 검증 묶음 1차 — 5/6 통과 + 본 하네스 회귀 결함 2건 발견·수정 (★ 외부 검증의 진짜 가치 = 결함 발견)
- 외부 검증 환경 셋업: `~/Developer/playground/nl-validation/` 신설. `empty-codebase/` (빈 디렉토리, .git 없음) + `clean-python/` (Python 미니 프로젝트 — `pyproject.toml` mypy strict + ruff + pytest, `src/greeter/{__init__,core}.py` + `tests/test_core.py`, `.venv/` mypy 1.19 / ruff 0.15 / pytest 8.4, `git init -b main` + initial commit)
- 진행 방식: 처음 (2)(B0)(1b) 세 시나리오는 사용자가 새 터미널에서 `cd <case>/ && claude --plugin-dir ~/.../nerdlab-harness` 띄워 SKILL 실호출. (B1)(5) 는 메인이 cwd 변경 + run_phases 직접 호출로 처리(결정적 동작 위주). (1b) 만 컨텍스트 0 진실성 위해 새 세션 강제

##### (2) 빈 코드 스킵 — 통과
- `/nerdlab-harness:nl-plan 간단한 hello 출력하는 Python 스크립트 추가` → clarify ★ 6 통과 → **Context Gather Phase A 가 `.git` 부재 자동 감지 → CONTEXT="none (empty codebase)" 스킵** → planner stdout 5줄 정확
- 산출물: `tasks/add-hello-script/plan.md` (12 섹션 모두 채움, validate_plan 통과). `## 11. Context = none (empty codebase)` 한 줄 정확. `**본문 1차안:**` 코드 블록(planner 절대 규칙 6) 정확

##### (B0) `.git` 존재 시 self-apply — 통과
- clean-python (이미 git init) 에서 `/nerdlab-harness:nl-setup` → git 2.50.1 검출 + `.git` 존재 → init skip + AskUserQuestion 5종 묶음 + 답한 항목 templates/ 복사 + 리포트
- 5개 파일 모두 `~/.../templates/` 와 **diff 0** (정확 복사 — 안티패턴 "복사 후 내용 수정" 준수)
- ⚠️ **명세 결함 발견**: setup-protocol.md "5항목 1라운드" 명시 vs `AskUserQuestion` 도구 자체 `maxItems: 4` 제한 → 실제 흐름은 4 묶음 + PRD 별도 = 2 라운드. 사용자 인터랙션 1회 추가됨. spec 갱신 필요 ("4 묶음 + 별도 PRD 1개" 또는 "도구 제한으로 1~2 라운드 허용")
- 미검증 보너스: 충돌 skip 정책 — 첫 호출이라 모두 신설. 두 번째 호출/충돌 케이스는 외부 트랙 별도

##### (1b) 모호 입력 clarify — 통과
- empty-codebase 에서 새 세션 `/nerdlab-harness:nl-plan 메모 앱 만들어줘` → 메인이 정확히 모호함 감지 ("요구사항이 매우 추상적이라 clarify 게이트에서 ★ 6개를 보충해야 합니다") → AskUserQuestion 묶음(앱형태/저장/완료범위/스택 4 묶음 → 저장구현+안할것 추가) → 2 라운드 + 사용자 요약 확인(스킵 불가)
- 산출물: `tasks/add-markdown-memo-app/plan.md` 170줄 — Next.js + react-markdown 마크다운 메모 앱(CRUD + 파일 영속), 12 섹션 모두 채움 + validate_plan 통과
- **보너스 (B1) #1 검증**: 후속 `/nerdlab-harness:nl-generate` 호출 시 git 가드가 `.git` 미존재 자동 차단 → exit 6 + 정확 메시지 ("/nl-setup 으로 git 초기화 후 재실행")

##### (B1) git 가드 happy-path — 4/5 통과
- ✅ #1 .git 미존재 차단: (1b) 보너스에서 검증
- ✅ #2 dirty 차단: clean-python 이 (B0) untracked 5종 상태 → /nl-generate → exit 6 + "git 가드: working tree 가 dirty" 정확
- ✅ #3 main → feat 자동 분기: clean tree 후 /nl-generate → `feat/add-farewell-fn` 자동 생성
- ✅ #4 phase passed 자동 commit: round 1 통과 → `feat(add-farewell-fn): phase-1 단일` (메시지 형식 1차안 정확) + working tree clean
- 🔲 #5 failed 리포트: 본 검증에선 모든 phase 가 round 1 또는 round 2 에서 통과 → 미검증 (max-rounds 모두 fail 케이스 별도 외부 트랙)
- 산출물: `tasks/add-farewell-fn/` (작성: 본 메인이 직접 작성한 plan, planner 헤드리스 호출은 (B1) 본질 아님). coder 가 `src/greeter/farewell.py` + `__init__.py` 갱신 + `tests/test_farewell.py` 정확히 작성 + Evaluate 통과(이 시점에선 결함 가려져 있어 사실 통과 아니라 스킵)

##### (5) Evaluate typecheck 깨지는 코드 — **본 하네스 회귀 결함 2건 발견 → 수정 → 재검증 통과**
- 1차 시도 (`tasks/add-reverse-fn/plan.md` — untyped reverse 함수 의도): /nl-generate → **rounds=1 passed** 라는 잘못된 결과
  - 진단: `phase1-round1.log` 에 **`### Evaluate` 섹션이 아예 없음** → `_run_evaluate` 호출 안 됨 → 로그도 안 남음
  - 직접 mypy 호출하면 3 errors (`Function is missing a type annotation` 등) 정확 fail → run_phases 만 게이트 무효
- **결함 1**: `scripts/run_phases.py:51` `_EVALUATE_SECTION_RE = r"^##\s+Evaluate\s+★"` 가 **numbered prefix 미지원** → planner 가 만드는 `## 12. Evaluate ★` 헤더 못 매치 → `_parse_eval_commands` 빈 리스트 → eval_commands 가 빈 리스트면 `_run_evaluate` 호출 분기 자체 스킵. (5) 본구현 직후 부트스트랩 4회차 때 `parse_phases`/`_slice_phase_table`/`validate_plan._slice_section` 세 곳에는 `(?:\d+\.\s+)?` 추가됐는데 본 정규식만 누락된 회귀
- **결함 2**: 결함 1 수정 후 회귀 테스트 작성 시 추가 발견 — `_parse_eval_commands` 가 코드 펜스(```) 자체를 명령으로 취급 → `subprocess.run(["```"])` → command not found → 모든 plan 의 첫 명령이 무조건 fail. 결함 1 이 가려서 안 보였던 두 번째 결함
- 수정:
  - `scripts/run_phases.py:51` 정규식에 `(?:\d+\.\s+)?` 추가
  - `scripts/run_phases.py:_parse_eval_commands` 에 ` ```\` 시작 라인 continue 분기 추가
  - `tests/test_run_phases.py` 에 `TestParseEvalCommands` 신규 5개 케이스 (plain / numbered prefix 회귀 / fenced 회귀 / none 빈 리스트 / 섹션 없음)
- 검증: unittest **126 → 131/131 PASS**
- 재검증: clean-python add-reverse-fn 의 round 1 결과 reset (commit + branch 삭제 + status/log 삭제) → /nl-generate 재실행 → **rounds=2 정확**
  - **round 1**: coder 가 plan 1차안 그대로 untyped reverse 작성 → reviewer status: ok ("plan 본문 1차안과 정확히 일치 — 타입 힌트 누락은 plan 이 명시한 의도된 mypy strict 위반") → **`### Evaluate` 섹션에 mypy fail 정확 기록** (no-untyped-def + no-untyped-call, exit 1) → run_phases 가 `_make_eval_review` 로 `{status: needs-fix, issue_ids: [eval-fail], raw: ...}` 합성
  - **round 2**: coder 가 합성 needs-fix 받아 `def reverse(s: str) -> str:` 로 타입 힌트 추가 → reviewer status: ok ("round 2 에서 타입 힌트 보완 확인") → Evaluate 모두 통과 (mypy 5 files / ruff All passed / pytest 2 passed) → phase passed → 자동 commit `037cf90 feat(add-reverse-fn): phase-1 단일`

##### 트레이드오프 인상
- **외부 검증의 진짜 가치 = 결함 2건 동시 발견**. 본 하네스 self-eval 은 plan 의 `Evaluate=none` 이 흔해서(하네스 자체는 외부 빌드 도구 없음) 우연히 회귀 누락이 가려져 있었음. 외부 mypy strict 환경에서야 비로소 진짜 게이트 작동 검증
- planner 절대 규칙 6 (1차안 본문 인라인 인용) 효과 (2)(1b)(5) 세 케이스 모두 **본문 1차안 코드 블록 정확** — coder 가 자율 판단으로 합의 위배할 위험 차단됨
- (B0)(B1) 자동 commit 메시지 형식 1차안 정확 (`feat(<task>): phase-<N> <name>`) — planner 절대 규칙 6 + (B1) plan 내 본문 1차안 인용 효과
- 부트스트랩 5회차 (1b 번호 prefix / reviewer-phase-slice 행 앵커 / Evaluate depends 컬럼 / nl-setup numbered list / Evaluate 정규식+펜스) 모두 동일 패턴 — planner 가 만드는 plan 의 표현 변형이 정규식 가정과 어긋남. 향후 spec 신설 시 정규식 회귀 테스트 동시 추가 룰화 필요

##### 잠재 결함
- 잠재 결함 1: setup-protocol.md "5항목 1라운드" 명세 vs AskUserQuestion `maxItems:4` — spec 갱신 필요. 다음 세션 단발 작업
- 잠재 결함 2: (B1) #5 failed 리포트 미검증 — round 재시도가 max-rounds 까지 다 fail 하는 케이스 미시뮬레이션. 외부 트랙 별도
- 잠재 결함 3: nl-ship commit-message 위임 + phase 미완료 stderr 경고도 외부 트랙 별도
- 잠재 결함 4: clean-python 의 `_parse_eval_commands` 회귀 테스트는 단위 테스트만. 정규식 + 펜스 + numbered prefix 가 동시에 깨졌을 때 진짜 plan 실호출 통합 테스트는 없음. 본 외부 검증이 그 역할을 했지만 자동화 X — 향후 외부 검증 묶음 자동화 검토

---

## Next (우선순위 순 — 5단계 모델 기준)

작업 순서: **(1) Clarify → (2) Context Gather → (5) Evaluate → (B) git 강제 → (C) philosophy 강제성 → nl-ship**

각 항목은 다음 세션에서 *결정 → 설계 → 본구현 → 검증* 한 사이클로 진입한다.

---

### [x] (1a) Clarify 명세 + SKILL 인계 — 완료 (2026-04-26)

산출물: `docs/spec/clarify-protocol.md` 신규 + `plan-template.md` / `nl-plan/SKILL.md` / `philosophy.md` 갱신. 상세는 위 Done 섹션.

### [x] (1b) Clarify 정규식 검증 헬퍼 + 실호출 검증 — 완료 (2026-04-26)

산출물: `scripts/validate_plan.py` 신규(147줄, 36 테스트) + `prompts/reviewer.md` plan 모드 ★ status 출력 룰 + `skills/nl-plan/SKILL.md` 단계 4 헬퍼 호출 연결 + `parse_phases` / `_slice_phase_table` 번호 prefix 부트스트랩 수정. 상세는 위 Done 섹션. **잔여 1**: 의도적 모호 입력 실호출 케이스(다음 세션에서 시뮬레이션).

---

### [x] (2) Context Gather — 완료 (2026-04-26)

산출물: `docs/spec/context-protocol.md` 신규(96줄) + `prompts/explorer.md` 신규(49줄) + `docs/spec/plan-template.md` Context ★ 섹션 추가 + `scripts/validate_plan.py` 4-섹션 확장(177줄) + `prompts/reviewer.md` plan 모드 Context 키 + `skills/nl-plan/SKILL.md` 단계 2 본구현(113줄). unittest 88/88 PASS. **잔여 1**: 빈 코드 스킵 실호출 검증(외부 테스트 프로젝트 트랙).

---

### [x] (5) Evaluate — 완료 (2026-04-26)

산출물: `docs/spec/plan-template.md` 12번째 ★ 섹션 `## Evaluate ★`(80줄) + `scripts/validate_plan.py` 5-섹션 확장(196줄) + `scripts/run_phases.py` `_run_evaluate`/`_make_eval_review`/`run_phase` 분기/eval 로그(842줄) + `prompts/reviewer.md` star_sections 5키 + eval 가이드(106줄) + `skills/nl-plan/SKILL.md` 단계 4 Evaluate(145줄). 부트스트랩 수정: `parse_phases` depends 컬럼 "없음"/괄호 부가설명 처리 + 회귀 테스트 5개. unittest 116/116 PASS. **잔여 1**: 의도적 typecheck 깨지는 외부 코드 실호출 통합 검증(외부 프로젝트 트랙).

---

### 이후 트랙 (위 셋 정착 후)

- [x] **(B0) `/nl-setup` 1회성 셋업** — git init + 표준 메타 문서 5종 (CLAUDE.md / ADR template / architecture.md / coding-conventions.md / [opt] PRD) (2026-04-26)
- [x] **(B1) `/nl-generate` git 가드** — dirty 차단 / `.git` 미존재 차단 / main 자동 feat 분기 / phase passed 자동 commit / failed 리포트. 헬퍼 4 + EXIT_CODE_GIT_GUARD=6 + 자기 검증 통과 (2026-04-26)
- [x] **(C) `docs/philosophy.md` 강제성 섹션** — 섹션 6 "이 하네스가 강제하는 것" 신설 (범용성 X 한 단락 + 강제 항목 7개 표 + 단일 진실 출처 매핑). philosophy.md 71→93줄. unittest 126/126 PASS 회귀 없음 (2026-04-26)
- [ ] **nl-ship 본구현** — (1)(2)(5)(B)(C) 정착 후. ship 책임 = git push·release 정리, 코드 작업 책임 X
- [ ] **hooks 도입** — `dangerous-cmd-guard` 우선. (B) git 강제와 함께 검토
- [ ] **marketplace 공개** — 모든 트랙 정착 후

### 검토 필요 (작업 시 같이 처리)

- [x] `skills/nl-review/SKILL.md` frontmatter description "reviewer 서브에이전트" → "헤드리스 reviewer" 정정 (2026-04-26, (C) 와 함께)
- [x] **`skills/nl-plan/SKILL.md` 위임 강화** — 145→84줄. Evaluate 가이드 30줄 → plan-template.md 이동. Context Gather/Clarify 본문 spec 위임 강화. unittest 116/116 PASS (2026-04-26)
- [x] 외부 프로젝트 실호출 검증 묶음 1차 — 5/6 통과 + 본 하네스 회귀 결함 2건 (`_EVALUATE_SECTION_RE` numbered prefix / `_parse_eval_commands` 코드 펜스) 발견·수정. unittest 126 → 131/131 PASS. (B1 #5 failed 리포트 / nl-ship 위임 / setup-protocol "1라운드" spec 갱신은 외부 트랙 잔여) (2026-04-28)
- [x] **planner 프롬프트 갱신** — `prompts/planner.md` 절대 규칙 6번 추가 + 핸드오프 한 줄 보강 (70→72줄). user prompt 에 1차안 본문 있으면 plan.md `## 6. 변경 파일` 에 `**본문 1차안:**` 헤더 + 코드 블록으로 인라인 인용 강제. unittest 119/119 PASS 회귀 없음 (2026-04-26)
- [ ] **context-protocol.md 갱신** — git ls-files 0 (init 직후 추적 0) 케이스 명시. 빈 코드와 다른 분기로 처리

---

## 다음 세션 진입 한 줄 가이드

**외부 검증 1차 완료 + 회귀 결함 2건 수정** — `~/Developer/playground/nl-validation/{empty-codebase, clean-python}` 셋업. (2)(B0)(1b)(B1 4/5)(5) 5개 통과. 진행 중 `scripts/run_phases.py:51` `_EVALUATE_SECTION_RE` 정규식 numbered prefix 미지원 + `_parse_eval_commands` 코드 펜스 명령 취급 두 결함 발견 → 수정 + `TestParseEvalCommands` 5 케이스 신규 → unittest **126→131/131 PASS**. (5) 재검증 시 round 1 mypy fail → round 2 typed 수정 → Evaluate 통과 → commit `037cf90` 진짜 흐름 확인.

**다음 세션 진입 즉시:**

```bash
cd ~/Developer/own/cc-marketplace/nerdlab-harness
claude --plugin-dir .
```

→ 갈래:
1. **setup-protocol.md spec 갱신** — "5항목 1라운드" → "AskUserQuestion maxItems:4 제한 고려 4 묶음 + 별도 PRD 1개" (또는 1~2 라운드 허용). 작은 단발 작업
2. **(B1) #5 failed 리포트 검증** — 의도적으로 max-rounds(3) 까지 다 fail 시키는 plan + /nl-generate → escalate → stderr 리포트 형식 확인. 외부 트랙
3. **`context-protocol.md` 보강** — git ls-files 0 (init 직후 추적 0) 케이스 명시. 작은 단발 작업
4. **nl-ship 잔여 외부 검증** — commit-message 스킬 실호출 위임 + phase 미완료 stderr 경고 케이스. 외부 트랙
5. **hooks 도입** — `dangerous-cmd-guard` 우선. (B1) git 가드와 직교 트랙
6. **marketplace 공개 검토** — 위 정착 후

추천 순서: **1 (setup-protocol 갱신) → 3 (context-protocol 보강) → 2+4 (외부 검증 잔여) → 5 (hooks) → 6 (marketplace)**.

---

## Roadmap (전체 단계)

- [x] 4단계 → 3+1단계 흐름 결정 + spec 명세 분리
- [x] `nl-plan` SKILL.md + `planner.md` 본구현
- [x] `docs/spec/plan-template.md` + `docs/spec/reviewer-output.md`
- [x] `tasks/<task-name>/` 통합 디렉토리 + `.gitignore` 정책
- [x] plan-template `Phase 분해` 섹션 + planner 휴리스틱
- [x] 호출 메커니즘 헤드리스 통일 (`nl-plan` 서브에이전트 → `claude -p`) (2026-04-26)
- [x] `agents/` → `prompts/` rename + frontmatter 제거 (2026-04-26)
- [x] `scripts/run_phases.py` 골격 본구현 (CLI + dataclass 스키마 + Phase 파서 + status read/write) (2026-04-26)
- [x] `run_phase` / `run_round` 본구현 + 헬퍼 5개 + 3중 안전망 + unit test 9개 (2026-04-26)
- [x] `prompts/coder.md` + `prompts/reviewer.md` 본구현 + `nl-generate` / `nl-review` SKILL.md (2026-04-26)
- [x] `--tdd` / `--inline` 옵션 본구현 + `prompts/{coder,reviewer}_tdd.md` + 단위 테스트 6 개 (2026-04-26)
- [x] `BLOCKED:` 자동 escalate 분기 + `_is_coder_blocked` 헬퍼 + `_decide_phase_outcome` reason 분기 + 단위 테스트 7 개 (2026-04-26)
- [x] reviewer phase 범위 한정 (`_slice_phase_table` + `_build_reviewer_prompt` 슬라이스/가이드) + `parse_phases` 행 시작 앵커 버그 부트스트랩 수정 + 단위 테스트 11 개 (2026-04-26)
- [x] 프로젝트 위치 이동 (`Developer/tools/` → `Developer/own/cc-marketplace/`) + 절대경로 5곳 갱신 + plugin 정공법(`--plugin-dir`) 셋업 결정 (2026-04-26)
- [x] plugin 정공법 셋업 검증 + symlink 잔재 제거 + README 설치 섹션 교체 (2026-04-26)
- [x] 5단계 모델(`Clarify → Context Gather → Plan → Generate → Evaluate`) 도입 결정 + 작업 순서 (1)(2)(5) 확정 (2026-04-26)
- [x] **(1a) Clarify 명세 + SKILL 인계** — `clarify-protocol.md` 신규 + plan-template/SKILL/philosophy 갱신 + 메인 세션 직접 수행 결정(헤드리스 예외) + 입력 ★ 6개 정의 + 단위 테스트 회귀 34/34 (2026-04-26)
- [x] **(1b) Clarify 헬퍼 본구현** — `scripts/validate_plan.py`(147줄) + `prompts/reviewer.md` plan 모드 `star_sections` + `skills/nl-plan/SKILL.md` 단계 4 헬퍼 호출 + `parse_phases` 번호 prefix 부트스트랩 수정 + unittest 71/71 (2026-04-26). 잔여: 모호 입력 실호출 시뮬레이션
- [x] **(2) Context Gather 본구현** — `docs/spec/context-protocol.md`(96줄) + `prompts/explorer.md`(49줄) + `plan-template.md` Context ★ + `scripts/validate_plan.py` 4-섹션 확장(177줄) + `reviewer.md` star_sections Context 키 + `nl-plan/SKILL.md` 단계 2 본구현(113줄) + unittest 88/88 (2026-04-26). Phase A 메인 / Phase B 헤드리스 익스플로러. 잔여: 빈 코드 스킵 실호출 검증
- [x] **(5) Evaluate 본구현** — `plan-template.md` 12번째 ★ `Evaluate`(80줄) + `validate_plan.py` 5-섹션(196줄) + `run_phases.py` `_run_evaluate`/`_make_eval_review`/`run_phase` 분기(842줄) + `reviewer.md` star_sections 5키 + eval 가이드(106줄) + `nl-plan/SKILL.md` 단계 4 Evaluate(145줄) + 부트스트랩 `parse_phases` depends 컬럼 "없음"/괄호 처리 + 회귀 테스트 5 + unittest 116/116 (2026-04-26). 5단계 모델 모두 본구현 완료. 잔여: 외부 typecheck 깨지는 코드 실호출 검증
- [x] **`nl-plan/SKILL.md` 위임 강화** — 145→84줄(-61). Evaluate 작성 가이드 30줄 → plan-template.md(80→112줄) 이동. Context Gather/Clarify 본문 spec 위임 강화. unittest 116/116 PASS 회귀 없음 (2026-04-26)
- [x] **(B0) `/nl-setup` SKILL 본구현** — 5번째 SKILL nl-setup(77줄) + setup-protocol.md(132줄) + templates/ 5종 + README 갱신 + 부트스트랩 `validate_plan.py` numbered list 인식 + 회귀 테스트 3 + unittest 119/119 PASS (2026-04-26). 잔여: context-protocol.md ls-files 0 케이스 / self-apply 실호출
- [x] **planner 프롬프트 갱신** — `prompts/planner.md` 절대 규칙 6 추가 + 핸드오프 한 줄 보강(70→72줄). 1차안 본문 인라인 인용 강제 → coder 자율 판단 합의 위배 재발 방지 (2026-04-26)
- [x] **(B1) `/nl-generate` git 가드 본구현** — 헬퍼 4 + EXIT_CODE_GIT_GUARD=6 + main() 분기 + phase passed commit + failed 리포트(`run_phases.py` 842→938줄). `docs/spec/git-guard-protocol.md` 신규(83줄). `nl-generate/SKILL.md` 49→59줄. TestGitGuard 5 시나리오 + 보조 2 = unittest 119→**126/126 PASS**. **자기 검증 ✓** (dirty 차단 메시지 + exit 6 정확) (2026-04-26). 잔여: clean tree happy-path 실호출 검증(외부 트랙)
- [x] **(C) `docs/philosophy.md` 강제성 섹션 명문화** — 섹션 6 신설(71→93줄). 범용성 X 한 단락 + 강제 항목 7개 표(plan-template/Clarify/Context/reviewer YAML/Evaluate/git 가드/헤드리스 통일) + 단일 진실 출처 매핑. nl-review SKILL frontmatter 정정 동시 처리. unittest 126/126 PASS 회귀 없음 (2026-04-26)
- [x] **nl-ship 본구현 + self-test ✓** — `skills/nl-ship/SKILL.md` 16→55줄 본구현 + `docs/spec/ship-protocol.md` 89줄 신규 + `README.md` 갱신. /nl-generate phase 1+2 round 1 passed + 자동 commit 2개. **★ self-test**: 본 SKILL 호출로 본 SKILL 의 PR(#1) 생성 → squash merge(`4e01ac1`) → 로컬 main 동기화. unittest 126/126 PASS (2026-04-26). 잔여: commit-message 스킬 실호출 위임 / phase 미완료 stderr 경고 케이스 외부 트랙
- [x] **외부 검증 1차 + Evaluate 게이트 회귀 결함 2건 수정** — `~/Developer/playground/nl-validation/{empty-codebase,clean-python}` 셋업. (2)(B0)(1b)(B1 4/5)(5) 5/6 통과. (5) 재검증 중 결함 발견: `_EVALUATE_SECTION_RE` numbered prefix 미지원 + `_parse_eval_commands` 코드 펜스 명령 취급. 수정: `run_phases.py:51` 정규식 `(?:\d+\.\s+)?` 추가 + `_parse_eval_commands` 펜스 continue + `TestParseEvalCommands` 5 케이스. unittest 126→**131/131 PASS**. 재검증: round 1 mypy fail → round 2 typed 수정 → Evaluate 통과 → commit `037cf90` (clean-python). 잔여: setup-protocol "1라운드" spec 갱신 / (B1)#5 failed 리포트 / nl-ship 외부 트랙 (2026-04-28)
- [ ] hooks 추가
- [ ] marketplace 공개 검토
