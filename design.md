# 구독과 로컬 모델 기반 공통 개발 에이전트 시스템 설계

하나의 운영 PC에서 여러 Git 프로젝트를 등록하고, 선택한 작업을 구현·검증·PR 초안까지 처리한다. 외부에서는 Telegram으로 기획 대화, 작업 제출, 상태 조회, 중단, 승인 요청에 응답한다. 작업 관리와 게이트는 Python 프로그램이 맡고, AI는 기획·구현·리뷰·정보 정리에 호출한다.

기본 구성은 Python 3.11 이상, SQLite, 기존 구독의 Codex CLI·Claude Code·Gemini CLI, Ollama다. RAM 32GB와 VRAM 16GB 환경에서는 로컬 추론 하나와 구현 작업 하나를 순차 운영한다. 전체 기획은 발전시켜도 현재 작업의 범위와 인수 조건은 고정한다.

## 구성과 책임

~~~mermaid
flowchart TB
    Phone["외부의 Telegram 또는 Discord"] --> Transport["통신 어댑터와 사용자 확인"]
    Console["PC의 터미널"] --> Commands["공통 명령 처리기"]
    Transport --> Commands
    Commands --> DB["SQLite 작업·승인·수신·발신 기록"]
    DB --> Scheduler["Python 스케줄러와 상태 전환"]
    Scheduler --> Context["관련 코드·규칙·예제 수집"]
    Context --> Models["구독 CLI 또는 로컬 모델"]
    Models --> Worktree["작업별 Git worktree"]
    Worktree --> Gates["검증·변경 범위·리뷰 게이트"]
    Gates --> Publish["별도 Git 작업과 PR 초안 생성"]
    Gates --> Plan["인프라 실행 계획과 정책 검사"]
    Plan --> Approve["커밋·계획·환경에 묶인 승인"]
    Approve --> Apply["별도 권한의 적용 실행기"]
    Scheduler --> Outbox["변경·완료·필요 행동 알림"]
    Outbox --> Transport
~~~

통신 어댑터는 메시지를 명령 객체로 변환할 뿐 셸을 실행하지 않는다. 작업 관리자가 역할과 실행기를 선택한다. 모델은 변경안과 의견을 내고, 실제 검사 결과·상태 전환·승인 소비는 관리자가 기록한다.

운영 권한은 통신 서비스, 모델 실행기, 코드 검사 실행기, Git 게시 실행기, 인프라 적용 실행기로 나눈다. 모델과 테스트 프로세스에는 Telegram 봇 토큰, Git 게시 토큰, 운영 클라우드 자격증명을 전달하지 않는다. 구독 CLI의 자체 인증은 검증된 로그인과 해당 도구의 실행 보호 기능을 사용한다.

이 분리는 프로세스 이름이나 환경 변수만으로 달성되지 않는다. 통신·게시·적용 비밀은 작업자 OS 계정이 읽을 수 없는 자격증명 저장소와 ACL에 둔다. native CLI의 파일·명령·MCP 권한을 검사하고, 비밀 파일 접근 거절을 실제로 시험한 실행 환경만 활성화한다. 같은 Windows 사용자 권한으로 분리한 프로세스는 강한 비밀 격리로 취급하지 않는다.

## 공통 폴더와 프로젝트 폴더

운영 프로그램은 대상 프로젝트의 Git 저장소 밖에 둔다. 다음은 구현할 프로그램의 목표 구조다. 패키지의 src/README.md에 모듈별 책임을 정의했다.

~~~text
agent-control/
  pyproject.toml
  src/agent_control/
    cli.py
    daemon.py
    commands.py
    scheduler.py
    state_machine.py
    context.py
    supervisor.py
    adapters/                 # codex, claude, gemini, ollama
    transports/               # console, telegram, discord
    gates/                    # billing, scope, checks, review, deployment
    executors/                # checks, git_publish, infra_plan, infra_apply
    store/                    # migrations, inbox, jobs, approvals, outbox
  config/
    runner.yaml
    projects.yaml
    languages/
  shared/
    rules/                    # 공통 규칙의 유일한 원본
    roles/
    templates/
  policies/
    default.policy.yaml
    approved-projects/        # 프로젝트별 검증된 설정 스냅샷
  var/                        # Git 제외·작업자가 쓸 수 없는 영역
    control.sqlite3
    runs/<job-id>/<attempt-id>/
    worktrees/<project-id>/<job-id>/
    context-cache/
    protected-artifacts/      # 인프라 계획 등 권한 제한
  tests/
~~~

~~~text
existing-project/
  PROJECT_RULES.md
  AGENTS.md
  CLAUDE.md
  GEMINI.md
  .agent/
    project.yaml              # 실행·검증·배포 작업 선언
    rules.generated.md        # 공통 규칙 버전으로 생성
    product.md                # 목표·현재 상태·다음 데모
    architecture.md           # 모듈 책임과 의존성
    examples/                 # 저장소의 기준 코드 위치
    decisions/                # 설계 변경 근거
    tasks/                    # 사람에게 보이는 이슈 명세
  ... 기존 소스 ...
~~~

새 프로젝트는 언어별 템플릿으로 시작한다. 기존 프로젝트는 소스 전체를 재배치하지 않고 .agent/부터 붙인다. 기존 지침 파일이 있으면 먼저 내용을 읽고 조정안을 만들며 자동 덮어쓰지 않는다. 프로젝트 등록은 알려진 Git root와 승인된 설정 스냅샷을 연결한다.

현재 작업의 모든 경로는 Windows 대소문자, 심볼릭 링크·junction, 상대 경로를 정규화해 등록된 worktree 내부인지 확인한다. worktree는 변경 충돌을 줄이는 장치다. 프로세스 권한과 네트워크 격리는 sandbox·OS 권한으로 별도로 적용한다.

## 기획이 미완성인 프로젝트 운영

product.md에는 대상 사용자, 해결할 문제, 핵심 사용 흐름, 현재 동작, 다음 데모, 이번 제외 범위를 적는다. 알 수 없는 내용은 가정으로 표시하고 조사 작업으로 만든다.

제품 루프는 실제 사용·피드백 → 최대 세 개의 후보 → 소유자의 다음 목표 선택 → 범위와 인수 조건 확정 → 구현 → 직접 사용 순서다. 기획 에이전트는 후보를 PROPOSED 상태로 기록한다. 사용자가 명세의 특정 버전을 선택해야 READY가 된다.

기획 대화와 구현 세션은 분리한다. 구현 중 새 기능이나 구조 개선이 필요하면 범위 변경 요청이나 다음 후보를 남긴다. 현재 작업 명세가 바뀌면 명세 해시를 갱신하고 기존 READY 승인과 구현 검증을 무효화한다.

프로젝트 상태는 active, parked, archived로 관리한다. 첫 설정에서는 active 하나만 허용하고 프로젝트마다 writer 하나만 둔다. parked 프로젝트는 자발적으로 전체 분석하거나 구현하지 않는다. Git 변화가 있거나 사용자 요청이 있을 때 상태를 갱신한다.

## 에이전트 역할

| 역할 | 기본 실행기 | 권한과 산출물 |
|---|---|---|
| product_planner | Codex 또는 요청한 구독 CLI | 코드 읽기, 후보·가정·명세 초안. 실행 승인 불가 |
| implementer | Codex | 해당 worktree의 허용 소스 수정. 범위 밖 변경은 요청 |
| reviewer | Claude Code | 명세·diff·관련 코드 읽기, 근거 있는 지적. 코드 수정·최종 승인 불가 |
| local_assistant | Ollama | 좁은 자료에서 정보 추출·분류·PR 설명 초안. 원문 위치 반환 |
| infra_designer | Codex의 별도 역할 지침 | 허용된 IaC 변경안 작성. apply 자격증명 없음 |

스케줄러·검사기·게시기·적용기는 AI 역할이 아닌 프로그램이다. 역할마다 모델을 항상 실행하지 않는다. implementer 하나가 코드와 필요한 테스트를 작성한다. 자동 검사 후 변경 위험에 따라 reviewer를 호출한다.

Gemini CLI는 요청한 문서 비교·조사에 선택해서 사용한다. 다른 구독을 사용하도록 정한 정책이 있어도 변경 전환은 최대 한 번이며 전체 작업 예산을 이어서 쓴다. 기본 한도 초과 동작은 대기다.

로컬 모델의 첫 후보는 Qwen3.5 9B다. Qwen2.5-Coder 14B는 작은 코드 작업의 비교 후보로 둔다. 분류·추출 작업의 초기 컨텍스트는 4k에서 시작해 필요하면 8k로 조정하고 실제 메모리를 측정한다. 전체 저장소 코딩과 긴 자율 루프에는 이 작은 컨텍스트를 그대로 적용하지 않는다. 컨텍스트가 커지면 필요한 메모리도 증가한다. [Ollama 컨텍스트 문서](https://docs.ollama.com/context-length)

로컬 결과에는 출처 파일과 기준 해시를 포함한다. JSON Schema로 형식을 확인한 다음 값의 근거를 확인한다. 로컬 모델이 위험을 낮추거나 인프라 적용을 승인할 수는 없다. [Ollama 구조화 출력](https://docs.ollama.com/capabilities/structured-outputs)

## 구독 인증과 추가 API 비용 차단

Codex는 ChatGPT 로그인, Claude Code는 Claude 구독 로그인, Gemini CLI는 Google 계정의 구독 경로를 사용한다. 구독은 API 키 사용과 별개다. [OpenAI 인증](https://learn.chatgpt.com/docs/auth) · [Claude 구독](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan) · [Gemini 구독](https://geminicli.com/docs/resources/quota-and-pricing/)

billing_mode는 subscription_only 또는 local_only만 허용한다. 직접 과금형 AI API SDK, API 키 제공자, 유료 대체 게이트웨이는 이 설계의 실행 경로에 없다. 자식 프로세스에는 검증된 환경 변수만 전달하고 API 키·클라우드 모델 제공자 설정·봇·게시·적용 토큰은 제외한다. CLI가 읽는 파일과 설정, 사용자 정의 게이트웨이, hooks·MCP·plugins도 등록 시 검사하고 검증된 조합만 허용한다.

doctor는 실제 설치 버전, 실행 파일 위치, 구독 인증 방식, 기본 제공자, 과금형 대체 경로 비활성 상태, 격리 기능을 확인한다. 버전이나 인증 방식이 불명확하면 AUTH_REQUIRED로 멈춘다. 재로그인은 설치된 도구의 공식 로그인 절차로 처리한다. 도구 업데이트 뒤에는 어댑터 계약을 다시 검증한다.

Claude Code의 ANTHROPIC_API_KEY는 구독 대신 API를 사용할 수 있다. --bare 모드도 구독 OAuth를 읽지 않으므로 이 구성에서 사용하지 않는다. extra usage 또는 구매한 추가 크레딧 소비도 초기 설정에서는 허용하지 않는다. [구독 안내](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan) · [비대화형 모드](https://code.claude.com/docs/en/headless)

설치 버전에서 extra usage 비활성이나 인증 경로를 프로그램으로 확실히 확인할 수 없으면 등록 시 사용자가 공식 설정에서 확인하고 doctor가 기록한 검증 버전과 설정을 고정한다. 이후 상태가 불명확해지면 실행을 중단한다. 환경 변수 제거만으로 비용 차단이 보장된다고 취급하지 않는다.

구독 한도에 도달하면 BLOCKED_QUOTA에 저장하고 알린다. 과금형 API로 전환하지 않는다. 한도 초기화는 공식 상태를 확인하거나 사용자가 재개할 때 판단하고 잦은 모델 호출로 확인하지 않는다.

## 이슈별 모드와 학습 게이트

이슈의 mode는 delivery 또는 portfolio다. 두 모드는 같은 실행기와 기술 게이트를 공유하고, portfolio에는 소유자의 설계 결정·실험 해석·핵심 설명과 실제 근거 기록을 추가한다. [모드 계약](modes.md)과 [세 포트폴리오 목표](portfolio-roadmap.md)에 단계와 인수 조건을 정의했다.

스킬은 .agents/skills/deliver-task와 .agents/skills/learn-and-build에 있다. 작업 관리자는 이슈 모드에 맞는 스킬을 명시적으로 전달하고, 스킬이 상태·권한·승인을 임의로 바꾸지 못하게 한다. 독립 Codex 작업에서도 사용할 수 있는 절차다.

복구·중복 방지·승인 게이트는 각각 portfolio 이슈로 진행한다. CLI 연결·통신 UI·정리는 delivery다. 사용자 대기 중에는 모델을 호출하지 않고 전체 활동 예산을 보존한다. 모드 변경은 소유자의 명시 요청으로 기록하고 이전 완료·승인을 재평가한다.

## 입력과 데이터 계약

Job은 job_id, project_id, kind, mode, mode_revision, learning, spec_version, 목표, 인수 조건, 제외 범위, 허용 변경 경로, 위험도 하한, 기준 커밋, 예산을 갖는다. 자유로운 사용자 메시지는 원문 자료로 저장하고 셸이나 CLI 옵션으로 연결하지 않는다.

프로젝트 명세가 없거나 인수 조건이 비어 있으면 NEEDS_INPUT으로 이동한다. 계획·조사 작업도 답할 질문과 완료 시 제출할 근거를 명시한다. 원격 자연어 입력은 먼저 PROPOSED다. 준비·실행은 공통 명령 처리기의 구조화된 요청으로만 수행한다.

모델 출력은 AgentResult 계약을 따른다. 결과의 상태는 implemented, needs_input, blocked, failed다. 모델의 implemented는 완료 판정이 아니라 주장이다. 관리자가 actual diff, 직접 실행한 검사, 리뷰 근거를 확인해야 다음 상태로 이동한다.

CLI 어댑터 계약은 preflight, run, stop, resume, normalize_result, report_usage다. resume에는 특정 세션 ID와 같은 worktree를 사용한다. 가장 최근 세션을 찾는 --last 방식은 사용하지 않는다. 명령은 고정된 argv와 표준 입력으로 전달한다. Windows .cmd 래퍼가 필요한 도구는 사용자 텍스트를 래퍼 명령문에 삽입하지 않고 버전별 실행 시험을 거친다.

Codex exec, Claude Code -p, Gemini CLI headless는 프로그램 실행과 구조화 출력 경로를 제공한다. [Codex](https://learn.chatgpt.com/docs/non-interactive-mode) · [Claude Code](https://code.claude.com/docs/en/headless) · [Gemini CLI](https://geminicli.com/docs/cli/headless/)

## 구현 상태와 실행 루프

~~~text
PROPOSED → PLANNING → NEEDS_INPUT 또는 PROPOSED
PROPOSED → READY                   소유자가 명세 버전 선택
READY → PREFLIGHT → CONTEXT → IMPLEMENTING → CHECKING
CHECKING 실패 → REVISING → CHECKING  전체 수정 시도 최대 2회
CHECKING 통과 → REVIEWING 또는 READY_FOR_PR
REVIEWING 지적 → REVISING → CHECKING → 필요 리뷰 재실행
high 변경 → WAITING_APPROVAL(action=accept_change) → READY_FOR_PR
READY_FOR_PR → PUBLISHING → PR_OPENED → COMPLETED
게시 승인이 필요하면 READY_FOR_PR → WAITING_APPROVAL → PUBLISHING
~~~

매 작업의 시작에는 구독 인증·프로젝트 등록·명세 해시·기준 커밋·프로젝트 잠금을 확인한다. 기준 커밋에 사용자 미커밋 변경이 포함되지 않는 경우를 숨기지 않는다. 초기 설정은 깨끗한 기준 상태를 요구한다.

관련 규칙, 기준 코드, 필요한 파일과 심볼, 인수 조건을 수집한다. 구현 후에는 모델이 명령을 실행했다고 말한 기록을 신뢰하지 않고 별도 검사기가 등록된 검증 명령을 실행한다. 관련된 변경은 반드시 최종 전체 필수 검사로 확인한다. 필수 검사가 없거나 건너뛰어졌으면 통과하지 않는다.

전체 job의 활동 실행 상한은 90분, 구독 CLI 단계 하나의 상한은 30분, 총 구독 실행 단계는 6회, 수정 시도는 2회다. 이 값들은 첫 운영을 위한 설정값이다. 내부 모델 호출 제한 기능이 있으면 추가 적용한다. 그렇지 않으면 관측 가능한 도구 실행 수와 프로세스 실행시간을 강제한다. 관측 불가능한 내부 턴이나 토큰에 엄격한 상한을 설정했다고 표시하지 않는다.

소유자 입력·구독 차단·승인 대기는 활동 예산에 포함하지 않는다. 각 단계 전에 남은 시간을 확인하고 짧은 단계 예산만 할당한다. 예산은 프로세스 재시작·모델 전환·수동 재개로 초기화하지 않는다. 재개 전에 소유자가 예산 증액을 명시하면 별도 변경 기록을 남긴다.

작업은 PAUSED, BLOCKED_QUOTA, AUTH_REQUIRED, BUDGET_EXHAUSTED, FAILED, CANCELLED로 중단될 수 있다. PID·생성 시각·세션 ID·worktree·커밋·단계·검사 결과·사용량은 SQLite에 저장한다.

실제 상태 전환 목록은 reference/state-machine.json에 정의한다. 대기 상태를 재개하면 PREFLIGHT 또는 RECOVERING부터 필요한 확인을 다시 수행한다. 상태 전환 자체가 게이트 통과를 의미하지는 않으며 해당 edge의 조건도 함께 확인한다.

daemon 재시작은 RECOVERING부터 시작한다. 기존 프로세스가 살아 있는지 확인하고, 다른 프로세스의 PID를 종료하지 않도록 생성 시각과 실행 식별자를 비교한다. 동일 프로젝트에는 writer lease를 하나만 부여한다. 변경된 HEAD·명세·정책에는 이전 검사와 승인을 재사용하지 않는다.

lease가 만료돼도 이전 writer가 종료됐다는 확인 없이 새 writer를 시작하지 않는다. lease generation과 작업 revision이 다른 실행 결과는 게시나 적용에 사용하지 않는다.

코드 작업은 상태와 diff를 확인하고 재개할 수 있다. Git 게시나 인프라 적용의 결과가 불명확하면 NEEDS_RECONCILIATION으로 이동해 실제 외부 상태를 먼저 조회한다. 적용·병합을 무조건 재실행하지 않는다.

## 게이트와 위험도

| 게이트 | 확인 | 실패 동작 |
|---|---|---|
| G0 사용자와 프로젝트 | 허용 사용자·창구, 등록 경로, 고정 명령 계약 | 모델 호출 전에 거절 |
| G1 비용과 실행기 | 구독 인증, 제공자, 버전, 유료 대체 경로 차단, 남은 예산 | AUTH_REQUIRED 또는 BLOCKED_QUOTA |
| G2 명세와 범위 | 확정 명세 해시, 변경 경로, 새 의존성, 지침·정책 변조 | NEEDS_INPUT 또는 범위 변경 승인 |
| G3 자동 검사 | 실제 커밋과 연결된 필수 검사, 인수 조건, 구조·의존성 검사 | 제한된 수정 또는 FAILED |
| G4 리뷰 | 위험도에 맞는 별도 리뷰, 지적의 근거와 해결 확인 | 수정 또는 WAITING_APPROVAL |
| G5 게시 | 검증된 최종 diff, 허용 저장소·브랜치, 중복 PR 확인 | 게시 보류 |
| G6 배포 | 계획·환경·정책·비용·승인 일치, 잠금, 복구 조건 | 적용 보류 |
| G7 실행 후 확인 | 서비스 상태, 리소스, 검증·복구 결과 | NEEDS_RECONCILIATION |

위험도는 경로·변경 동작에 대한 정적 규칙으로 하한을 정한다. 모델은 상향 제안만 할 수 있다. 판별할 수 없는 변경은 high로 취급한다.

| 위험도 | 예시 | 검토와 승인 |
|---|---|---|
| routine | 문서·정형 수정·검증된 생성 파일 | 자동 검사, 선택적 리뷰 |
| standard | 기존 구조 안의 작은 애플리케이션 기능 | 자동 검사와 범위 확인, 표본 또는 지정 리뷰 |
| high | 인증·권한·스키마·의존성·IaC·CI·설계 변경 | 별도 리뷰와 소유자 명시 승인 |
| destructive | 운영 데이터 삭제·리소스 삭제 또는 교체·권한 대폭 확대 | 일반 자동 루프 차단, 별도 변경·복구 계획과 명시 승인 |

관리 정책·사용자 허용 목록·검사 실행 정의·인프라 적용 경로는 작업자가 수정할 수 없다. 프로젝트 manifest를 변경해 필수 검사를 빼는 방식도 동일 PR에서 적용하지 않는다. 변경된 선언은 따로 등록 검토해 승인된 스냅샷을 갱신한다.

언어별 포맷과 린트뿐 아니라 모듈 경계, 공개 API 계약, 기준 구조를 검사한다. Java Maven/Gradle, JS 패키지 매니저 등은 프로젝트에 맞는 프로필을 선택한다. 기존 위반을 허용한 경우 등록된 파일·해시를 기준으로 관리하며 새 위반이나 수정된 영역의 악화를 통과시키지 않는다.

## 커밋과 PR

이슈는 하나의 사용자 결과 또는 검증할 가설과 인수 조건으로 나눈다. 구현 내부 단계는 더 작게 실행하고 작업 로그에 기록한다. 커밋은 설명하고 되돌릴 수 있는 논리적 변경으로 남긴다. PR은 하나의 목적을 검토할 수 있는 단위로 구성한다.

Git 작업과 PR 생성은 게시 실행기가 수행한다. 모델에게 게시 토큰을 제공하지 않는다. 초기 설정에서는 Draft PR 게시만 프로젝트별로 승인할 수 있고 자동 병합은 꺼 둔다. 로컬 COMPLETED는 지정된 산출물 완료를 의미하며 제품 전체나 병합 완료를 뜻하지 않는다.

작업 ID를 브랜치와 PR 표식에 연결한다. 재시작 시 기존 브랜치·PR을 조회해 중복 생성하지 않는다. PR 설명은 명세·diff·관리자 검사 기록으로 생성하며 원격 내용은 신뢰할 수 없는 자료로 취급한다.

## 인프라 작업

~~~text
READY → PREFLIGHT → IaC 변경안 → PLAN_GENERATING → POLICY_CHECKING
→ WAITING_APPROVAL → APPLYING → VERIFYING_DEPLOYMENT → COMPLETED
~~~

plan과 apply를 서로 다른 실행기·자격증명으로 분리한다. 환경·리전·모듈·리소스 종류·크기·개수는 프로젝트 등록 설정에 제한한다. 정책 검사에는 공개 네트워크 접근, 권한 확대, 삭제·교체, 비용 증가를 포함한다. 비용이나 영향이 알려지지 않은 항목은 자동 통과시키지 않는다.

Terraform은 저장된 계획과 JSON 분석을 사용한다. 승인 문맥에는 job_id, 작업 명세 해시, 코드 커밋, plan SHA256, 대상 환경, 정책 버전, 검사 결과 해시를 묶는다. 이 값이 바뀌거나 계획이 만료되면 새 계획과 승인이 필요하다. 저장 계획 적용은 Terraform 자체 승인 프롬프트가 없으므로 적용 실행기가 이 조건을 강제한다. [Terraform 계획](https://developer.hashicorp.com/terraform/tutorials/cli/plan)

원본 plan·state는 권한 제한 저장소에 보관하고 모델·Telegram·Discord·Git에 그대로 보내지 않는다. 승인 창구에는 민감정보를 제거한 변경 목록과 비용·복구 정보를 보낸다.

첫 운영에서는 dev의 소규모 비파괴 변경도 명시 승인으로 시작한다. 운영이 검증되면 사전 승인된 dev 템플릿만 제한적 자동 적용을 허용한다. prod와 destructive는 별도 승인을 요구한다. 원격 prod 승인은 추가 인증이 구성되지 않으면 차단한다. 코드 작성자가 승인하거나 정책을 낮출 수는 없다.

DB 변경은 단계적 확장·전환·정리와 복구 가능한 백업을 계획한다. 적용 중단이나 부분 실패 뒤에는 외부 리소스와 상태를 대조하고 새 계획을 만든다. /pause와 /stop은 진행 중인 클라우드 변경을 되돌리는 명령이 아니다.

## 원격 창구

Telegram의 getUpdates 장기 폴링을 기본으로 선택한다. PC가 Telegram에 나가는 HTTPS 연결을 만들며 외부에서 PC에 접속할 공개 포트는 없다. 웹훅과 폴링은 동시에 쓰지 않는다. [Telegram Bot API](https://core.telegram.org/bots/api#getupdates)

허용 Telegram user ID와 개인 chat ID를 오프라인 설정에 등록한다. 사용자가 처음 메시지를 보내기만 했다고 소유자로 등록하지 않는다. Telegram·Discord의 표시 이름이나 역할 이름을 권한의 근거로 쓰지 않는다.

/projects, /status, /chat, /task, /ready, /run, /pause, /stop, /resume, /approvals, /approve, /reject, /plan, /deploy, /quota를 공통 명령으로 제공한다. 일반 자연어는 기획 대화·제안으로 들어간다. /status와 /quota는 저장된 상태를 반환하며 모델을 호출하지 않는다. 자세한 계약은 remote-protocol.md에 있다.

입력은 inbox에 내구성 있게 기록한 뒤 수신 offset을 갱신한다. 동일 update_id 또는 interaction_id는 한 번만 작업으로 변환한다. Telegram 알림은 outbox로 발송하고 실패 시 제한적으로 재시도한다. 전송 결과가 불명확하면 알림이 중복될 수 있으므로 이벤트 ID를 함께 표시한다.

승인은 짧은 일회성 버튼 토큰을 서버의 승인 문맥에 연결한다. 사용자·대화·작업·행동·커밋·계획·정책·만료를 검사하고 DB 트랜잭션으로 한 번 소비한다. 자연어의 '응'이나 모델의 판단으로 승인하지 않는다. Telegram 버튼 데이터에는 긴 문맥 대신 토큰 참조를 넣는다. [버튼 제한](https://core.telegram.org/bots/api#inlinekeyboardbutton)

외부 전송은 상태 요약·필요 행동·허용된 PR 링크가 기본이다. 원본 로그·소스·plan·state·비밀 값은 기본 전송하지 않는다. 알림은 접수, 완료, 실패, 중단, 승인 요청 위주로 보내고 매 모델 턴을 알리지 않는다.

Discord는 추후 같은 명령 처리기에 Gateway와 slash command 어댑터로 연결한다. 수신 후 빠르게 응답을 유예하고 긴 작업은 작업 ID로 조회하게 한다. interaction 응답 토큰에 장시간 작업 완료를 의존하지 않는다. Discord는 초기 응답을 3초 안에 요구하고 토큰은 15분 유효하다. [Discord 문서](https://docs.discord.com/developers/interactions/receiving-and-responding)

PC가 꺼지거나 잠들면 작업·응답도 멈춘다. Telegram의 미수신 업데이트 보관은 최대 24시간이다. 오래된 실행·승인 요청은 복귀 뒤 자동 실행하지 않고 새 확인을 요구한다. [Telegram 업데이트 보관](https://core.telegram.org/bots/api#getting-updates)

## 상태 저장과 복구

SQLite WAL과 외래 키를 사용한다. jobs, job_attempts, artifacts, check_runs, approvals, inbox, outbox, audit_events, project_leases, learning_checkpoints, learning_evidence를 저장한다. 단일 PC의 로컬 디스크에 DB를 두고 공유 네트워크 폴더에서 WAL을 운영하지 않는다.

작업 상태 전환, 승인 소비, 작업 예약에는 트랜잭션과 revision 비교를 적용한다. 외부 실행은 트랜잭션으로 원자화할 수 없으므로 실행 식별자와 결과 조회를 사용한다. 인프라에서는 '정확히 한 번 실행'을 약속하는 대신 결과 불명 상태를 따로 처리한다.

일반 로그와 토큰 사용량은 조회 시점까지의 관측값이다. 구독 CLI가 표시하는 추정 달러 비용을 추가 청구로 해석하지 않는다. 실제 구독 한도는 해당 서비스의 상태를 따른다. 토큰 통계는 작업·시도별로 저장하고 내부 호출 정보가 없으면 미관측으로 표시한다.

## 첫 구현의 범위

먼저 console과 Codex 실행기, 프로젝트 등록, worktree, 실제 검사, DB 복구를 만든다. 다음에 Telegram의 허용 사용자·명령·알림·승인 소비를 붙인다. Claude 리뷰와 로컬 정리는 이후에 추가하고, 인프라는 계획과 정책 검사부터 검증한 뒤 적용 실행기를 연결한다.

첫 완료 기준은 작은 기능 작업이 확정 명세에서 검증된 PR 초안까지 이어지고, 중단·중복 요청·한도 초과·오래된 승인에 올바르게 대응하는 것이다. implementation-plan.md에 단계별 인수 조건을 정의했다.


이슈 모드와 학습 진행은 modes.md의 상태 분기를 따른다. 기술 통과 없이 학습 단계가 구현 또는 배포 게이트를 우회하지 않는다.
