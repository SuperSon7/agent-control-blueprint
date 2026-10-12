# Python 모듈 계약

이 디렉터리는 구현할 모듈의 책임 명세다. 실행 코드가 아니다.

- cli.py: console 명령을 구조화하고 공통 commands에 전달.
- daemon.py: 통신, 스케줄러, outbox, lease heartbeat를 비동기로 구동.
- commands.py: 사용자·창구 권한 확인, 입력 스키마 검증, 중복 방지, 요청 기록.
- scheduler.py: READY 선택, 전체 예산과 프로젝트 writer lease 확인.
- state_machine.py: 허용 상태 전환, revision 검사, 조건과 감사 이벤트 저장.
- context.py: Git hash 기반 관련 자료 수집, 출처 연결, 캐시 무효화.
- supervisor.py: 고정 argv·stdin, 환경 allowlist, 작업 경로, timeout·프로세스 트리 관리.
- adapters/: 설치 버전·구독 인증·권한·출력·복구 계약의 검증된 구현.
- transports/: 명령 입출력만 제공. 모델이나 셸을 직접 호출하지 않음.
- gates/: 모델 주장 대신 실제 diff·검사·승인 문맥으로 통과 여부 판단.
- executors/: 코드 검사, Git 게시, plan과 apply의 권한·프로세스 분리.
- store/: SQLite 트랜잭션, inbox/outbox, 승인 소비, 작업·시도·lease 기록.

통신 토큰은 transports 프로세스만 읽고 게시·적용 자격증명은 해당 executor만 읽는다. 전달 객체에 비밀 값을 넣지 않는다. 운영 관리자 소스와 정책은 작업자 수정 영역에서 제외한다.
