"""Check blueprint contracts; this does not test an implemented controller."""
from copy import deepcopy
import json
from pathlib import Path
import re
import sqlite3
import unittest

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINTS = ["decision", "interpretation", "explanation"]
LEARNING_STATES = {
    "LEARNING_PLAN", "WAITING_OWNER_DECISION", "EXPERIMENTING",
    "WAITING_OWNER_INTERPRETATION", "WAITING_OWNER_EXPLANATION", "PORTFOLIO_RECORD",
}


def read_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def read_yaml(name):
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


def validator(name):
    return jsonschema.Draft202012Validator(read_json(f"schemas/{name}.schema.json"))


class BlueprintContracts(unittest.TestCase):
    def test_json_yaml_syntax_and_schema_definitions(self):
        for path in ROOT.rglob("*"):
            if ".git" in path.parts or not path.is_file():
                continue
            if path.suffix == ".json":
                value = json.loads(path.read_text(encoding="utf-8"))
                if path.name.endswith(".schema.json"):
                    jsonschema.Draft202012Validator.check_schema(value)
            elif path.suffix in {".yaml", ".yml"}:
                yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_all_positive_fixtures(self):
        fixtures = {
            "examples/job.example.json": "job",
            "examples/portfolio-recovery.job.json": "job",
            "examples/portfolio-deduplication.job.json": "job",
            "examples/portfolio-approval-gates.job.json": "job",
            "examples/agent-result.example.json": "agent-result",
            "examples/approval-context.example.json": "approval-context",
        }
        for fixture, schema in fixtures.items():
            with self.subTest(fixture=fixture):
                validator(schema).validate(read_json(fixture))
        manifest = read_yaml("templates/project/.agent/project.yaml")
        validator("project").validate(manifest)
        self.assertLessEqual(set(manifest["checks"]["required"]), set(manifest["commands"]))
        self.assertEqual(read_json("examples/approval-context.example.json")["policy_version"],
                         read_yaml("policies/default.policy.yaml")["version"])

    def test_delivery_rejects_learning_payload(self):
        job = read_json("examples/job.example.json")
        job["learning"] = read_json("examples/portfolio-recovery.job.json")["learning"]
        self.assertFalse(validator("job").is_valid(job))

    def test_portfolio_requires_learning_and_owner_steps(self):
        original = read_json("examples/portfolio-recovery.job.json")
        for value in (None, {}, {**original["learning"], "owner_steps": []}):
            job = deepcopy(original)
            job["learning"] = value
            with self.subTest(learning=value):
                self.assertFalse(validator("job").is_valid(job))

    def test_targets_and_mode_revision_reject_ambiguous_values(self):
        original = read_json("examples/portfolio-recovery.job.json")
        for targets in ([], ["recovery", "recovery"], ["recovery", "deduplication", "approval-gates"]):
            job = deepcopy(original)
            job["learning"]["targets"] = targets
            self.assertFalse(validator("job").is_valid(job))
        for mode, revision in (("fast", 1), ("delivery", 0)):
            job = read_json("examples/job.example.json")
            job.update(mode=mode, mode_revision=revision)
            self.assertFalse(validator("job").is_valid(job))

    def test_apply_context_requires_plan_environment_and_checks(self):
        original = read_json("examples/approval-context.example.json")
        for key in ("artifact_sha256", "environment", "checks_sha256"):
            context = deepcopy(original)
            context[key] = None
            with self.subTest(key=key):
                self.assertFalse(validator("approval-context").is_valid(context))

    def test_portfolio_publish_and_apply_require_evidence_hash(self):
        for action in ("publish_draft_pr", "apply_plan"):
            context = read_json("examples/approval-context.example.json")
            context.update(mode="portfolio", action=action)
            self.assertFalse(validator("approval-context").is_valid(context))
            context["learning_evidence_sha256"] = "e" * 64
            validator("approval-context").validate(context)

    def test_shared_gates_and_zero_paid_fallback_defaults(self):
        runner = read_yaml("config/runner.example.yaml")
        policy = read_yaml("policies/default.policy.yaml")
        adapters = read_yaml("config/adapters.example.yaml")["adapters"]
        manifest = read_yaml("templates/project/.agent/project.yaml")
        for key in ("paid_ai_api_enabled", "extra_usage_enabled", "automatic_paid_fallback"):
            self.assertIs(runner["billing"][key], False)
        self.assertIs(runner["limits"]["reset_budget_on_resume"], False)
        self.assertIs(runner["publication"]["auto_merge"], False)
        self.assertIs(runner["work_modes"]["shared_technical_gates"], True)
        self.assertEqual(runner["work_modes"]["portfolio"]["model_calls_while_waiting"], 0)
        self.assertEqual(runner["work_modes"]["portfolio"]["owner_checkpoints"], CHECKPOINTS)
        self.assertEqual(policy["learning_gate"]["owner_checkpoints"], CHECKPOINTS)
        self.assertIs(policy["learning_gate"]["replace_technical_gate"], False)
        self.assertIs(policy["learning_gate"]["agent_may_answer_as_owner"], False)
        self.assertEqual(set(policy["approvals"]["bind"]),
                         set(read_json("schemas/approval-context.schema.json")["required"]))
        self.assertLessEqual(set(runner["models"].values()), set(adapters))
        self.assertLessEqual(set(manifest["roles"].values()), set(adapters))
        for adapter in adapters.values():
            self.assertIn(adapter["billing_mode"], runner["billing"]["allowed_modes"])
            self.assertIs(adapter["verified"], False)
        for transport in ("telegram", "discord"):
            self.assertIs(runner["remote"][transport]["enabled"], False)
            self.assertFalse(runner["remote"][transport]["allowed_user_ids"])
        self.assertIs(runner["deployment"]["auto_apply_prod"], False)

    def test_state_references_mode_routes_and_invalidation(self):
        contract = read_json("reference/state-machine.json")
        states = set(contract["states"])
        transitions = contract["transitions"]
        self.assertEqual(states, set(transitions))
        for targets in transitions.values():
            self.assertLessEqual(set(targets), states)
        for state in contract["terminal"]:
            self.assertFalse(transitions[state])
        self.assertLessEqual(LEARNING_STATES, states)
        guards = contract["mode_guards"]
        self.assertIs(guards["delivery"]["learning_states_allowed"], False)
        self.assertEqual(guards["portfolio"]["preflight_next"], "CONTEXT")
        self.assertEqual(guards["portfolio"]["context_next"], "LEARNING_PLAN")
        self.assertIn("learning_evidence_current", guards["portfolio"]["apply_requires"])
        self.assertIn("technical_gates_passed", guards["portfolio"]["ready_for_pr_requires"])
        self.assertIs(contract["mode_change"]["owner_explicit_only"], True)
        self.assertIn("approvals", contract["mode_change"]["invalidate"])
        self.assertIn("budget_usage", contract["mode_change"]["preserve"])
        for action, modes in contract["awaiting_approval_action_to_next_by_mode"].items():
            self.assertEqual(set(modes), {"delivery", "portfolio"}, action)
            self.assertLessEqual(set(modes.values()), set(transitions["WAITING_APPROVAL"]))

    def test_skill_metadata_and_reference_links(self):
        for name in ("deliver-task", "learn-and-build"):
            folder = ROOT / ".agents" / "skills" / name
            text = (folder / "SKILL.md").read_text(encoding="utf-8")
            header = yaml.safe_load(text.split("---", 2)[1])
            self.assertEqual(header["name"], name)
            self.assertIsInstance(header["description"], str)
            metadata = yaml.safe_load((folder / "agents" / "openai.yaml").read_text(encoding="utf-8"))
            interface = metadata["interface"]
            self.assertTrue(25 <= len(interface["short_description"]) <= 64)
            self.assertIn(f"${name}", interface["default_prompt"])

    def test_internal_markdown_links(self):
        for path in ROOT.rglob("*.md"):
            if ".git" in path.parts:
                continue
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if target.startswith(("https://", "http://", "#", "mailto:")):
                    continue
                with self.subTest(file=str(path.relative_to(ROOT)), target=target):
                    self.assertTrue((path.parent / target.split("#", 1)[0]).exists())


class DatabaseContracts(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript((ROOT / "reference/schema.sql").read_text(encoding="utf-8"))
        self.db.execute("INSERT INTO projects (project_id,repo_path,status,created_at_utc) "
                        "VALUES ('p','/tmp/example','active','2026-10-12T00:00:00Z')")

    def tearDown(self):
        self.db.close()

    def insert_job(self, job_id="job-1", mode="delivery", state="PROPOSED", learning=None, revision=1):
        self.db.execute("INSERT INTO jobs (job_id,project_id,kind,mode,mode_revision,learning_json,state,"
                        "spec_json,spec_sha256,risk,created_at_utc,updated_at_utc) VALUES "
                        "(?,'p','feature',?,?,?,?, '{}',?,'standard',?,?)",
                        (job_id, mode, revision, learning, state, "a" * 64,
                         "2026-10-12T00:00:00Z", "2026-10-12T00:00:00Z"))

    def test_thirteen_tables_and_foreign_keys(self):
        tables = self.db.execute("SELECT name FROM sqlite_master WHERE type='table' "
                                 "AND name NOT LIKE 'sqlite_%'").fetchall()
        self.assertEqual(len(tables), 13)
        self.assertEqual(self.db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.assertFalse(self.db.execute("PRAGMA foreign_key_check").fetchall())

    def test_sql_accepts_every_declared_state(self):
        for index, state in enumerate(read_json("reference/state-machine.json")["states"]):
            mode = "portfolio" if state in LEARNING_STATES else "delivery"
            self.insert_job(f"job-{index}", mode, state, "{}" if mode == "portfolio" else None)
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_job("job-invalid", state="UNKNOWN")

    def test_sql_rejects_mode_learning_mismatch(self):
        for mode, learning, revision in (("fast", None, 1), ("delivery", "{}", 1),
                                         ("portfolio", None, 1), ("delivery", None, 0)):
            with self.subTest(mode=mode, learning=learning, revision=revision):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.insert_job(mode=mode, learning=learning, revision=revision)

    def test_inbox_duplicate_key_rejected_new_event_allowed(self):
        sql = ("INSERT INTO inbox (source,external_id,actor_id,conversation_id,command_json,received_at_utc) "
               "VALUES ('telegram:bot-1',?,'owner','chat','{}','2026-10-12T00:00:00Z')")
        self.db.execute(sql, ("update-1",))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(sql, ("update-1",))
        self.db.execute(sql, ("update-2",))
        self.assertEqual(self.db.execute("SELECT count(*) FROM inbox").fetchone()[0], 2)

    def test_answered_checkpoint_requires_owner_source_and_artifact(self):
        self.insert_job(mode="portfolio", learning="{}")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO learning_checkpoints "
                            "(checkpoint_id,job_id,kind,spec_sha256,mode_revision,head_sha,status,updated_at_utc) "
                            "VALUES ('cp-1','job-1','decision',?,1,?,'answered',?)",
                            ("a" * 64, "b" * 40, "2026-10-12T00:00:00Z"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
