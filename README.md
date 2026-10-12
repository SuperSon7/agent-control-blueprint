# 구독과 로컬 모델 기반 개발 에이전트 시스템

여러 프로젝트를 하나의 Python 작업 관리자에 등록하고, 기존 구독 CLI와 Ollama로 개발 작업을 수행하는 설계 패키지다. 원격 창구는 Telegram 장기 폴링을 기본으로 하고 Discord Gateway를 같은 명령 계약으로 추가한다.

이 패키지에는 설계서, 설정 예시, 프로젝트 부착 템플릿, 역할 지침, 데이터 계약, SQLite DDL, 구현 순서가 포함된다. 실제 실행 프로그램이나 연결된 봇은 포함되지 않는다.

- [전체 설계](design.md)
- [이슈별 두 모드](modes.md)
- [포트폴리오 학습 순서](portfolio-roadmap.md)
- [구현 순서와 완료 조건](implementation-plan.md)
- [원격 명령과 승인](remote-protocol.md)
- [Windows 운영 방법](windows-operations.md)
- 공통 설정: config/runner.example.yaml
- 프로젝트 등록: config/projects.example.yaml
- 프로젝트 부착: templates/project/
- 데이터 계약: schemas/
- DB 설계: reference/schema.sql

예시의 저장소 경로, 사용자 ID, CLI 버전은 실제 환경에서 등록해야 한다. 비어 있는 허용 사용자 목록이나 검증되지 않은 CLI가 있으면 실행을 허용하지 않는다. 설정 키는 이 시스템의 설계 계약이며 제품 CLI의 설정 키가 아니다.

추가 AI API 사용은 기본 차단한다. 기존 구독료, 전기·인터넷, 선택한 클라우드 인프라의 사용료는 별도다. 구독 제공 범위와 CLI 동작은 설치 버전을 검증한 뒤 활성화한다.


## 스킬 사용

- $deliver-task: 현재 delivery 이슈의 확정 결과를 구현하고 검증한다.
- $learn-and-build: portfolio 이슈에서 내가 설계 결정·실험 해석·설명을 직접 하며 구현한다.

원본은 .agents/skills/에 있어 저장소 작업에서 발견할 수 있다. 다른 프로젝트에서도 사용하려면 두 폴더를 사용자 스킬 경로에 설치한다. 두 스킬은 독립 작업에서도 사용할 수 있지만 미래 실행기의 상태·비용·승인 제어를 대신하지 않는다.

빠른 구현에서도 공통 게이트는 동일하다. 포폴 모드의 사용자 단계가 비어 있으면 학습 완료로 표시하지 않는다. 현재 세 포폴 대상은 계획 상태이며 실제 성능·학습 성과를 주장하지 않는다.

## 계약 검증

Python 3.11 이상에서 python -m pip install -r requirements-dev.txt 후 python scripts/validate_blueprint.py를 실행한다. 검증은 YAML·JSON·조건부 Schema·SQLite 제약·문서 연결·모드 라우팅의 정합성을 확인한다. 실제 작업 복구·동시 실행·원격 인증·승인 소비·배포의 실행 검증은 구현 후 별도로 수행한다.

GitHub Actions에도 같은 검사를 등록한다. 워크플로는 읽기 권한만 사용하고 CLI·모델·비밀 값 없이 실행한다. Actions 설정은 [checkout 공식 문서](https://github.com/actions/checkout/blob/main/README.md)와 [setup-python 공식 문서](https://github.com/actions/setup-python/blob/main/README.md)를 기준으로 작성했다.

포폴 대상은 [작업 복구](backlog/portfolio-recovery.md), [중복 실행 방지](backlog/portfolio-deduplication.md), [승인 게이트](backlog/portfolio-approval-gates.md) 세 이슈로 나눈다. 이 저장소의 초기 업로드는 설계 결과이며 해당 기능의 구현 완료가 아니다.
