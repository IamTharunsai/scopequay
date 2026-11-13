import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scopequay.experiments import ExperimentService

DATA = Path(__file__).resolve().parents[1] / "data/pilot_v0_2.jsonl"


class ExperimentBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.service = ExperimentService(self.root, DATA)

    def tearDown(self):
        if self.service.worker:
            self.service.worker.join(timeout=30)
            self.assertFalse(self.service.worker.is_alive())
        self.temp.cleanup()

    def test_real_fixed_proposal_job_persists_and_verifies(self):
        with patch("builtins.print"):
            job = self.service.submit({"limit": 2})
            self.service.worker.join(timeout=30)
        result = self.service.results(job["id"])
        self.assertEqual(result["job"]["status"], "completed")
        self.assertEqual(result["job"]["inference_calls"], 0)
        self.assertEqual(len(result["outcomes"]), 4)
        self.assertTrue(
            all(r["entry_point"] == "experiment_backend" for r in result["outcomes"])
        )
        self.assertEqual(
            ExperimentService(self.root, DATA).get(job["id"])["status"], "completed"
        )
        self.assertEqual(len(result["job"]["backend_source_sha256"]), 2)

    def test_cloud_paths_arbitrary_controllers_and_unbounded_requests_rejected(self):
        bad = [
            {"provider": "openai"},
            {"provider": "anthropic"},
            {"dataset": "private.csv"},
            {"model": "llama3.2:3b"},
            {"limit": True},
            {"limit": 153},
            {"max_seconds": 601},
            {"systems": ["direct", "direct"]},
            {"systems": ["shell"]},
            {"split": "train"},
            {"mode": "agent", "model": "anything", "limit": 8, "max_calls": 1},
        ]
        for payload in bad:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.service.submit(payload)
        self.assertEqual(self.service.list(), [])

    def test_single_worker_limit(self):
        hold = threading.Event()

        def blocked(job_id):
            hold.wait(timeout=5)

        with patch.object(self.service, "_run", side_effect=blocked):
            self.service.submit({"systems": ["direct"]})
            try:
                with self.assertRaises(ValueError):
                    self.service.submit({"systems": ["direct"]})
            finally:
                hold.set()

    def test_restart_marks_unfinished_work_interrupted(self):
        jid = "a" * 32
        directory = self.root / jid
        directory.mkdir()
        (directory / "job.json").write_text(
            json.dumps({"id": jid, "status": "running", "created_at": "2026-11-12"})
        )
        self.assertEqual(
            ExperimentService(self.root, DATA).get(jid)["status"], "interrupted"
        )
        with self.assertRaises(ValueError):
            self.service.get("../private")

    def test_failed_model_preflight_creates_no_job(self):
        with patch(
            "scopequay.experiments.LocalOllama.installed",
            side_effect=ValueError("not installed"),
        ):
            with self.assertRaises(ValueError):
                self.service.submit({"mode": "agent", "model": "missing:local"})
        self.assertEqual(self.service.list(), [])

    def test_run_failure_is_visible_not_success(self):
        with patch(
            "scopequay.experiments.load_dataset",
            side_effect=ValueError("fixture failure"),
        ):
            job = self.service.submit({"systems": ["direct"]})
            self.service.worker.join(timeout=10)
        self.assertEqual(self.service.get(job["id"])["status"], "failed")
        self.assertIn("fixture failure", self.service.get(job["id"])["error"])

    def test_agent_pipeline_with_explicit_test_double_not_real_inference(self):
        class TestAgent:
            metadata = {"name": "unit:local", "digest": "test-double"}
            version = {"version": "unit-test"}
            model = "unit:local"
            guarded_prompt = False
            seed = 23
            calls = 0
            last = {}

            def __init__(self, *args, **kwargs):
                pass

            def initial_messages(self, x):
                self.x = x
                self.step = 0
                return []

            def next(self, messages):
                self.calls += 1
                self.step += 1
                self.last = {"error": None, "cached": False}
                return {
                    "kind": "EXECUTE" if self.step == 1 else "FINISH",
                    "resource": self.x.proposed_resource,
                    "amount": self.x.amount,
                    "reason": "Explicit unit-test double",
                }

        with (
            patch(
                "scopequay.experiments.LocalOllama.installed",
                return_value={"name": "unit:local", "size": 1},
            ),
            patch("tharun.agent.LocalAgent", TestAgent),
            patch("builtins.print"),
        ):
            job = self.service.submit(
                {
                    "mode": "agent",
                    "model": "unit:local",
                    "limit": 1,
                    "max_steps": 2,
                    "max_calls": 4,
                }
            )
            self.service.worker.join(timeout=30)
        result = self.service.results(job["id"])
        self.assertEqual(result["job"]["status"], "completed")
        self.assertEqual(len(result["outcomes"]), 2)
        self.assertTrue(all("trace" in r for r in result["outcomes"]))
