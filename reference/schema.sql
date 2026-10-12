PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS projects (
  project_id TEXT PRIMARY KEY,
  repo_path TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK(status IN ('active','parked','archived')),
  manifest_sha256 TEXT,
  rules_version TEXT,
  revision INTEGER NOT NULL DEFAULT 1,
  created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  kind TEXT NOT NULL,
  mode TEXT NOT NULL CHECK(mode IN ('delivery','portfolio')),
  mode_revision INTEGER NOT NULL DEFAULT 1 CHECK(mode_revision >= 1),
  learning_json TEXT CHECK(learning_json IS NULL OR json_valid(learning_json))
    CHECK((mode = 'delivery' AND learning_json IS NULL) OR
          (mode = 'portfolio' AND learning_json IS NOT NULL AND json_type(learning_json) = 'object')),
  state TEXT NOT NULL CHECK(state IN ('PROPOSED','PLANNING','NEEDS_INPUT','READY','PREFLIGHT','CONTEXT','IMPLEMENTING','CHECKING','REVIEWING','REVISING','READY_FOR_PR','PUBLISHING','PR_OPENED','PLAN_GENERATING','POLICY_CHECKING','WAITING_APPROVAL','APPLYING','VERIFYING_DEPLOYMENT','PAUSED','BLOCKED_QUOTA','AUTH_REQUIRED','BUDGET_EXHAUSTED','FAILED','RECOVERING','NEEDS_RECONCILIATION','COMPLETED','CANCELLED','LEARNING_PLAN','WAITING_OWNER_DECISION','EXPERIMENTING','WAITING_OWNER_INTERPRETATION','WAITING_OWNER_EXPLANATION','PORTFOLIO_RECORD')),
  spec_json TEXT NOT NULL CHECK(json_valid(spec_json)),
  spec_sha256 TEXT NOT NULL,
  base_sha TEXT,
  head_sha TEXT,
  worktree_path TEXT,
  phase_before_pause TEXT,
  risk TEXT NOT NULL CHECK(risk IN ('routine','standard','high','destructive')),
  revision INTEGER NOT NULL DEFAULT 1,
  spent_wall_seconds INTEGER NOT NULL DEFAULT 0 CHECK(spent_wall_seconds >= 0),
  subscription_stages INTEGER NOT NULL DEFAULT 0 CHECK(subscription_stages >= 0),
  repair_attempts INTEGER NOT NULL DEFAULT 0 CHECK(repair_attempts >= 0),
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_state_idx ON jobs(state, project_id);

CREATE TABLE IF NOT EXISTS job_attempts (
  attempt_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(job_id),
  role TEXT NOT NULL,
  adapter_id TEXT NOT NULL,
  adapter_contract_version TEXT NOT NULL,
  provider_session_id TEXT,
  pid INTEGER,
  process_created_at_utc TEXT,
  status TEXT NOT NULL,
  result_json TEXT CHECK(result_json IS NULL OR json_valid(result_json)),
  observed_usage_json TEXT CHECK(observed_usage_json IS NULL OR json_valid(observed_usage_json)),
  started_at_utc TEXT NOT NULL,
  finished_at_utc TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(job_id),
  kind TEXT NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  head_sha TEXT,
  restricted INTEGER NOT NULL DEFAULT 0 CHECK(restricted IN (0,1)),
  created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS check_runs (
  check_run_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(job_id),
  check_id TEXT NOT NULL,
  head_sha TEXT NOT NULL,
  spec_sha256 TEXT NOT NULL,
  definition_sha256 TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('passed','failed','skipped','missing')),
  exit_code INTEGER,
  output_artifact_id TEXT REFERENCES artifacts(artifact_id),
  created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
  approval_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(job_id),
  action TEXT NOT NULL,
  context_json TEXT NOT NULL CHECK(json_valid(context_json)),
  context_sha256 TEXT NOT NULL,
  nonce_sha256 TEXT NOT NULL UNIQUE,
  required_actor_id TEXT NOT NULL,
  required_source TEXT NOT NULL,
  required_conversation_id TEXT NOT NULL,
  expires_at_utc TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','expired','consumed')),
  approved_at_utc TEXT,
  consumed_at_utc TEXT,
  revision INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS inbox (
  inbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  command_json TEXT NOT NULL CHECK(json_valid(command_json)),
  status TEXT NOT NULL DEFAULT 'received',
  received_at_utc TEXT NOT NULL,
  UNIQUE(source, external_id)
);
CREATE TABLE IF NOT EXISTS transport_offsets (
  source TEXT PRIMARY KEY,
  durable_offset TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outbox (
  event_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  destination_id TEXT NOT NULL,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  next_attempt_at_utc TEXT,
  created_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
  event_id TEXT PRIMARY KEY,
  job_id TEXT REFERENCES jobs(job_id),
  actor_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
  created_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS project_leases (
  project_id TEXT PRIMARY KEY REFERENCES projects(project_id),
  job_id TEXT NOT NULL REFERENCES jobs(job_id),
  owner_id TEXT NOT NULL,
  generation INTEGER NOT NULL,
  expires_at_utc TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS learning_checkpoints (
  checkpoint_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(job_id),
  kind TEXT NOT NULL CHECK(kind IN ('decision','interpretation','explanation')),
  spec_sha256 TEXT NOT NULL,
  mode_revision INTEGER NOT NULL CHECK(mode_revision >= 1),
  head_sha TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('waiting','answered','stale','abandoned'))
    CHECK(status != 'answered' OR (owner_actor_id IS NOT NULL AND
          owner_response_artifact_id IS NOT NULL AND source_inbox_id IS NOT NULL)),
  owner_actor_id TEXT,
  owner_response_artifact_id TEXT REFERENCES artifacts(artifact_id),
  source_inbox_id INTEGER REFERENCES inbox(inbox_id),
  updated_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learning_evidence (
  evidence_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(job_id),
  checkpoint_id TEXT REFERENCES learning_checkpoints(checkpoint_id),
  kind TEXT NOT NULL CHECK(kind IN ('decision','experiment','interpretation','explanation','case_study')),
  origin TEXT NOT NULL CHECK(origin IN ('owner','agent','controller')),
  actor_id TEXT NOT NULL,
  artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
  spec_sha256 TEXT NOT NULL,
  mode_revision INTEGER NOT NULL CHECK(mode_revision >= 1),
  head_sha TEXT NOT NULL,
  created_at_utc TEXT NOT NULL
);
