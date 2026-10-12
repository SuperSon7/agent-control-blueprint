# 설계와 스킬 저장소 작업 지침

이 저장소는 설계 계약과 재사용 스킬 패키지다. 전체 daemon이나 연결된 봇·배포 실행기는 아직 구현되지 않았다.

이슈의 mode를 먼저 확인한다. delivery는 .agents/skills/deliver-task/SKILL.md, portfolio는 .agents/skills/learn-and-build/SKILL.md를 사용한다. 모드와 권한을 스킬 선택만으로 바꾸지 않는다.

portfolio의 소유자 판단·실험 해석·핵심 설명은 실제 소유자의 응답에서만 가져온다. 현재 없는 실험·성능·학습 결과를 만들지 않는다.

계약 변경은 관련 schema·예시·상태·문서를 함께 수정하고 python scripts/validate_blueprint.py로 확인한다. 실제 CLI·통신·권한·인프라의 동작 검증과 계약 검증을 구분한다.

비밀 값, 세션 원문, 개인 토큰 통계, 운영 plan·state는 커밋하지 않는다.
