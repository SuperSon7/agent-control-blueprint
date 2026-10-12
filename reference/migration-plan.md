# 모드 계약 변경 시 DB 마이그레이션

현재 schema.sql은 새 DB에 적용하는 DDL이다. 기존 운영 DB를 변경하는 마이그레이션은 아직 구현하지 않았다. CREATE TABLE IF NOT EXISTS만 다시 실행해서 기존 테이블을 갱신할 수 없다.

이 실행기를 처음 구현할 때 schema 버전과 PRAGMA user_version을 함께 관리한다. 기존 DB 업그레이드는 writer 종료 확인, 백업과 복원 검증, 명시적인 버전 확인 후 시작한다. jobs의 mode·mode_revision·learning_json뿐 아니라 학습 상태를 허용하는 CHECK 제약도 함께 변경해야 하므로 테이블 재생성과 데이터 복사가 필요하다.

새 테이블에는 기존 작업을 delivery·mode_revision=1·learning_json=NULL로 옮긴다. 기존 작업을 학습 완료로 변환하지 않는다. 인덱스와 외래 키를 복원하고 foreign_key_check 및 integrity_check를 검사한다. 기존 job_attempts·artifacts·approvals·lease 참조를 보존하고 승인 문맥 변경에 따라 이전 승인은 무효화한다.

SQLite의 foreign_keys 변경 시점과 테이블 이름 변경이 참조에 미치는 영향을 검증한 뒤 트랜잭션과 복원 전략을 확정한다. 실제 마이그레이션 완료 조건은 이전 버전 DB fixture, 중간 실패, 재실행 거절, 복구 후 데이터·인덱스·외래 키 보존이다. 이 문서는 실행할 SQL을 대신하지 않는다.
