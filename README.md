# 구독과 로컬 모델 기반 개발 에이전트 시스템

여러 프로젝트를 하나의 Python 작업 관리자에 등록하고, 기존 구독 CLI와 Ollama로 개발 작업을 수행하는 설계 패키지다. 원격 창구는 Telegram 장기 폴링을 기본으로 하고 Discord Gateway를 같은 명령 계약으로 추가한다.

이 패키지에는 설계서, 설정 예시, 프로젝트 부착 템플릿, 역할 지침, 데이터 계약, SQLite DDL, 구현 순서가 포함된다. 실제 실행 프로그램이나 연결된 봇은 포함되지 않는다.

- [전체 설계](design.md)
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
