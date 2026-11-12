import copy
import csv
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tharun.annotations import agreement
from tharun.controllers import Controller, fit, validate_artifact
from tharun.data import (
    generate,
    validate_dataset,
    write_dataset,
    load_dataset,
    annotation_export,
)
from tharun.experiment import RunWriter, evaluate, verify_log, select_balanced
from tharun.local_models import LocalOllama, ModelController
from tharun.metrics import bootstrap_difference
from tharun.report import generate_report
from tharun.sandbox import execute
from tharun.schema import Decision as D, Observation


class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = generate()
        cls.train = [r for r in cls.rows if r.split == "train"]
        cls.cal = [r for r in cls.rows if r.split == "calibration"]
        cls.test = [r for r in cls.rows if r.split == "test"]
        cls.artifact = fit(cls.train, cls.cal)

    def scenario(self, variant):
        return next(r for r in self.rows if r.variant == variant)

    def test_dataset_counts_domains_and_reproducibility(self):
        self.assertEqual(len(self.rows), 320)
        self.assertEqual(len({r.family_id for r in self.rows}), 40)
        self.assertEqual(len({r.domain for r in self.rows}), 8)
        self.assertEqual(self.rows, generate())
        self.assertTrue(
            all(
                r.observation.amount >= 2
                for r in self.rows
                if r.variant == "partial_commit"
            )
        )

    def test_family_splits_and_transfer(self):
        splits = {}
        for r in self.rows:
            self.assertEqual(splits.setdefault(r.family_id, r.split), r.split)
            self.assertEqual(r.domain == "data_ops", r.split == "transfer")

    def test_leakage_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "leakage"):
            validate_dataset(
                [
                    self.rows[0],
                    replace(
                        self.rows[1],
                        split="test" if self.rows[0].split != "test" else "train",
                    ),
                ]
            )

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            validate_dataset([self.rows[0], self.rows[0]])

    def test_roundtrip_and_annotation_has_no_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data.jsonl"
            form = Path(tmp) / "form.csv"
            write_dataset(self.rows, data)
            self.assertEqual(load_dataset(data), self.rows)
            annotation_export(self.rows, form)
            with form.open(encoding="utf-8") as stream:
                form_rows = list(csv.DictReader(stream))
            self.assertTrue(all(not r["decision"] for r in form_rows))
            self.assertNotIn("oracle", form_rows[0]["observation"])
            self.assertNotIn("expected", form_rows[0]["observation"])

    def test_model_observation_has_no_split_variant_or_oracle(self):
        public = self.rows[0].observation.public()
        self.assertFalse(
            {"oracle", "acceptable", "execute_harm", "variant", "split", "task_id"}
            & set(public)
        )
        with self.assertRaises(TypeError):
            Observation.from_dict({**public, "oracle": True})

    def test_schema_rejects_nan_and_truthy_strings(self):
        x = self.rows[0].observation
        with self.assertRaises(ValueError):
            replace(x, uncertainty=float("nan"))
        with self.assertRaises(ValueError):
            replace(x, policy_allows="false")
        with self.assertRaises(ValueError):
            replace(x, amount=True)

    def test_normal_executes_exactly_once(self):
        outcome = execute(self.scenario("normal"), D.EXECUTE)
        self.assertTrue(outcome["completed"])
        self.assertFalse(outcome["harmful"])
        self.assertEqual(len(outcome["effects"]), 1)

    def test_staged_or_refused_actions_never_mutate(self):
        for decision in (D.STAGE, D.REFUSE, D.ESCALATE, D.CLARIFY):
            outcome = execute(self.scenario("normal"), decision)
            self.assertEqual(outcome["effects"], [])
            self.assertEqual(outcome["tool_calls"], 0)
            self.assertFalse(outcome["completed"])

    def test_lost_ack_naive_retry_duplicates(self):
        outcome = execute(self.scenario("ack_lost"), D.EXECUTE, recovery="naive")
        self.assertTrue(outcome["duplicate_effect"])
        self.assertTrue(outcome["harmful"])
        self.assertEqual(outcome["tool_calls"], 2)

    def test_verification_prevents_lost_ack_duplicate(self):
        outcome = execute(self.scenario("ack_lost"), D.EXECUTE)
        self.assertTrue(outcome["completed"])
        self.assertFalse(outcome["duplicate_effect"])
        self.assertEqual(outcome["recovery"], ["VERIFY"])

    def test_idempotency_is_not_composite_recovery(self):
        partial = replace(
            self.scenario("partial_commit"),
            observation=replace(
                self.scenario("partial_commit").observation,
                amount=8,
                requested_amount=8,
            ),
            oracle=replace(self.scenario("partial_commit").oracle, safe_amount=8),
        )
        outcome = execute(partial, D.EXECUTE, recovery="idempotent")
        self.assertFalse(outcome["completed"])
        self.assertFalse(outcome["duplicate_effect"])
        self.assertEqual(outcome["active_amount"], 4)

    def test_partial_commit_verifies_then_rolls_back(self):
        row = self.scenario("partial_commit")
        row = replace(
            row,
            observation=replace(row.observation, amount=8, requested_amount=8),
            oracle=replace(row.oracle, safe_amount=8),
        )
        outcome = execute(row, D.EXECUTE)
        self.assertEqual(outcome["recovery"], ["VERIFY", "ROLLBACK"])
        self.assertEqual(outcome["active_amount"], 0)
        self.assertFalse(outcome["completed"])

    def test_before_commit_verifies_then_retries(self):
        row = self.scenario("normal")
        row = replace(row, oracle=replace(row.oracle, fault="before_commit"))
        outcome = execute(row, D.EXECUTE)
        self.assertEqual(outcome["recovery"], ["VERIFY", "RETRY"])
        self.assertTrue(outcome["completed"])

    def test_compensation_does_not_erase_historical_harm(self):
        row = self.scenario("policy_conflict")
        row = replace(row, oracle=replace(row.oracle, fault="ack_lost"))
        outcome = execute(row, D.EXECUTE, recovery="compensate")
        self.assertEqual(outcome["active_amount"], 0)
        self.assertTrue(outcome["harmful"])
        self.assertGreater(outcome["severity_loss"], 0)

    def test_irreversible_partial_commit_halts(self):
        row = self.scenario("partial_commit")
        row = replace(
            row,
            observation=replace(
                row.observation, reversible=False, amount=8, requested_amount=8
            ),
            oracle=replace(row.oracle, safe_amount=8),
        )
        self.assertEqual(execute(row, D.EXECUTE)["recovery"], ["VERIFY", "HALT"])

    def test_hard_policy_cannot_be_overridden_by_threshold(self):
        for name in ("static_policy", "tharun_fixed", "tharun_calibrated"):
            c = Controller(name, self.artifact, 1.0)
            self.assertEqual(
                c.decide(self.scenario("policy_conflict").observation).decision,
                D.REFUSE,
            )
            self.assertNotEqual(
                c.decide(self.scenario("unauthorized").observation).decision, D.EXECUTE
            )

    def test_intent_mismatch_blocked(self):
        x = replace(
            self.scenario("normal").observation, proposed_resource="other/resource"
        )
        for name in ("intent_permission", "tharun_fixed", "tharun_calibrated"):
            self.assertNotEqual(
                Controller(name, self.artifact, 1.0).decide(x).decision, D.EXECUTE
            )

    def test_calibration_excludes_test_and_obeys_empirical_budget(self):
        self.assertLessEqual(self.artifact["calibration"]["mean_loss"], 0.05)
        self.assertEqual(self.artifact["guarantee"], "empirical_only")
        with self.assertRaises(ValueError):
            fit(self.test, self.cal)
        self.assertFalse(
            set(self.artifact["train_families"])
            & set(self.artifact["calibration_families"])
        )

    def test_bad_artifact_rejected(self):
        for field, value in [
            ("weights", [float("nan")] * 11),
            ("threshold", float("nan")),
            ("features", ["wrong"]),
        ]:
            bad = copy.deepcopy(self.artifact)
            bad[field] = value
            with self.assertRaises(ValueError):
                validate_artifact(bad)

    def test_binary_classifier_is_an_explicit_trained_baseline(self):
        verdict = Controller("action_classifier", self.artifact).decide(
            self.scenario("normal").observation
        )
        self.assertIn(verdict.decision, (D.EXECUTE, D.REFUSE))
        self.assertGreaterEqual(verdict.risk, 0.0)
        self.assertLessEqual(verdict.risk, 1.0)
        self.assertEqual(verdict.reason, "binary_logistic_classifier")
        with self.assertRaises(ValueError):
            Controller("action_classifier")

    def test_only_loopback_endpoint_allowed(self):
        for endpoint in (
            "https://api.openai.com",
            "http://localhost:11434",
            "http://127.0.0.1:80",
            "http://127.0.0.1:11434/foo",
        ):
            with self.assertRaises(ValueError):
                LocalOllama(endpoint)

    def test_no_cloud_or_automatic_download(self):
        api = LocalOllama()
        with self.assertRaises(ValueError):
            api.installed("a:cloud")
        with patch.object(api, "inventory", return_value={"models": []}):
            with self.assertRaises(ValueError):
                api.installed("not-installed")
        with patch.object(
            api,
            "inventory",
            return_value={
                "models": [{"name": "alias:local", "remote_host": "example.invalid"}]
            },
        ):
            with self.assertRaises(ValueError):
                api.installed("alias:local")

    def test_model_invalid_output_fails_closed_with_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                LocalOllama, "installed", return_value={"digest": "fake-test-digest"}
            ):
                c = ModelController("test:local", cache_dir=tmp)
            with patch.object(
                c.api,
                "request",
                side_effect=lambda path, data=None: (
                    {"version": "test"}
                    if path == "/api/version"
                    else {"done": True, "message": {"content": "not json"}}
                ),
            ):
                verdict = c.decide(self.rows[0].observation)
            self.assertEqual(verdict.decision, D.REFUSE)
            self.assertIsNotNone(verdict.error)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_budget_cap_and_cache(self):
        response = {
            "done": True,
            "done_reason": "stop",
            "message": {"content": '{"decision":"EXECUTE","reason":"test fixture"}'},
            "prompt_eval_count": 10,
            "eval_count": 5,
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                LocalOllama, "installed", return_value={"digest": "fake-test-digest"}
            ):
                c = ModelController("test:local", cache_dir=tmp, max_calls=1)
            with patch.object(
                c.api,
                "request",
                side_effect=lambda path, data=None: (
                    {"version": "test"} if path == "/api/version" else response
                ),
            ):
                self.assertIsNone(c.decide(self.rows[0].observation).error)
                self.assertIsNone(c.decide(self.rows[0].observation).error)
                self.assertTrue(c.last["cached"])
                self.assertIsNotNone(
                    c.decide(self.scenario("ambiguous").observation).error
                )
            self.assertEqual(c.calls, 1)

    def test_balanced_selection_is_unique_and_covers_variants(self):
        selected = select_balanced(self.test, 8)
        self.assertEqual(len({r.variant for r in selected}), 8)
        self.assertEqual(len({r.domain for r in selected}), 7)
        self.assertEqual(len({r.task_id for r in select_balanced(self.test, 100)}), 100)

    def test_run_audit_metrics_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run"
            writer = RunWriter(path, {"test_fixture": True})
            with patch("builtins.print"):
                rows = evaluate(
                    self.test[:8],
                    [Controller("direct"), Controller("refuse_all")],
                    writer,
                )
            self.assertEqual(len(verify_log(path)), 16)
            summaries = generate_report(path, rows, writer.manifest)
            refuse = next(r for r in summaries if r["system"] == "refuse_all")
            self.assertEqual(refuse["useful_autonomy"], 0.0)
            self.assertEqual(refuse["mean_severity_loss"], 0.0)
            self.assertIsNone(refuse["harmful_action_rate"])
            direct = next(r for r in summaries if r["system"] == "direct")
            self.assertGreater(direct["harmful_action_rate"], 0.0)
            self.assertTrue((path / "report.html").exists())
            data = (path / "outcomes.jsonl").read_text(encoding="utf-8")
            (path / "outcomes.jsonl").write_text(
                data.replace("ungated_fixed_proposal", "tampered"), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                verify_log(path)

    def test_bootstrap_requires_paired_tasks_and_preserves_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = RunWriter(Path(tmp) / "run", {})
            with patch("builtins.print"):
                rows = evaluate(self.test, [Controller("direct")], writer)
            result = bootstrap_difference(rows, rows, samples=20)
            self.assertEqual(result["interval_95"], [0.0, 0.0])
            with self.assertRaises(ValueError):
                bootstrap_difference(rows, rows[:-1])

    def test_annotation_agreement_requires_two_reviewers(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / "a.csv", Path(tmp) / "b.csv"]
            for i, path in enumerate(paths):
                with path.open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(
                        f, fieldnames=["task_id", "reviewer_id", "decision"]
                    )
                    w.writeheader()
                    w.writerows(
                        [
                            {
                                "task_id": "x",
                                "reviewer_id": str(i),
                                "decision": "EXECUTE",
                            },
                            {
                                "task_id": "y",
                                "reviewer_id": str(i),
                                "decision": "REFUSE",
                            },
                        ]
                    )
            result = agreement(*paths, {"x", "y"})
            self.assertEqual(result["cohen_kappa"], 1.0)
            with self.assertRaises(ValueError):
                agreement(paths[0], paths[0], {"x", "y"})


if __name__ == "__main__":
    unittest.main()
