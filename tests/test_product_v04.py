from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from scopequay.experiments import ExperimentService
from scopequay.policy import assess
from scopequay.review_cli import install_skill

ROOT = Path(__file__).resolve().parents[1]


class ProductTests(unittest.TestCase):
    def test_review_no_execution_and_no_fabricated_authority(self):
        action = json.loads((ROOT / "examples/action-review.json").read_text())
        result = assess(action)
        self.assertEqual(result["decision"], "ESCALATE")
        self.assertFalse(result["tool_executed"])
        action.update(approval_required=False, policy_allows=False)
        self.assertEqual(assess(action)["decision"], "REFUSE")
        action["permitted_operations"] = "refund"
        with self.assertRaises(ValueError):
            assess(action)

    def test_skill_install_is_self_contained_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()):
            target = Path(temp) / "scopequay-review"
            install_skill(["--target", str(target)])
            self.assertTrue((target / "SKILL.md").exists())
            self.assertTrue((target / "references/action-context.json").exists())
            with self.assertRaises(ValueError):
                install_skill(["--target", str(target)])

    def run_job(self, service, payload):
        with redirect_stdout(io.StringIO()):
            job = service.submit(payload)
            while service.worker.is_alive():
                service.worker.join(timeout=1)
        result = service.results(job["id"])
        self.assertEqual(
            result["job"]["status"], "completed", result["job"].get("error")
        )
        return result

    def test_full_heldout_suite_includes_all_domain_vocabularies_and_variants(self):
        with tempfile.TemporaryDirectory() as temp:
            service = ExperimentService(temp, ROOT / "data/pilot_v0_2.jsonl")
            result = self.run_job(
                service, {"systems": ["direct"], "split": "evaluation", "limit": 152}
            )
            self.assertEqual(len(result["outcomes"]), 152)
            self.assertEqual(set(result["slices"]["split"]), {"test", "transfer"})
            self.assertEqual(len(result["slices"]["domain"]), 8)
            self.assertEqual(len(result["slices"]["variant"]), 8)
            self.assertEqual(len(result["scenario_context"]), 152)

    def test_naive_retry_has_more_duplicate_effects_than_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            service = ExperimentService(temp, ROOT / "data/pilot_v0_2.jsonl")
            naive = self.run_job(
                service, {"systems": ["direct"], "limit": 8, "recovery": "naive"}
            )
            verify = self.run_job(
                service, {"systems": ["direct"], "limit": 8, "recovery": "verify"}
            )
            self.assertGreater(
                sum(r["duplicate_effect"] for r in naive["outcomes"]),
                sum(r["duplicate_effect"] for r in verify["outcomes"]),
            )
