# [프로젝트 이름]

## 프로젝트 개요

TBD — 이 프로젝트가 무엇을 하는지 한 문단으로 작성.

## 기술 스택

TBD — 언어, 프레임워크, 주요 라이브러리.

## Git Workflow (GitHub flow, 1인 개발자)

- main = 항상 배포 가능 상태
- 모든 변경은 feature 브랜치에서 작업
- feature → PR → 셀프 리뷰 → squash merge
- develop 브랜치 X (1인이라 불필요)
- commit 메시지: Conventional Commits (feat / fix / docs / refactor / test / chore)

## 작업 방식 (Claude 에게)

- 코드: 주석 최소화, 함수명으로 의도 표현
- 언어: 한국어 응답 선호

## 경계 (하지 말 것)

- 요청 없는 리팩터링·추상화 추가
- 환경변수·시크릿 하드코딩

## 검증 방법

TBD — 테스트 실행 명령, 로컬 서버 구동 방법 등.
