import concurrent.futures
from pathlib import Path
import tempfile
import unittest

from scopequay.workflow import Workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "demo.sqlite3"
        self.w = Workflow(self.path)
        self.state = self.w.seed()

    def pick(self, title):
        return next(r for r in self.w.snapshot()["requests"] if title in r["title"])

    def act(self, r, action, note="Test review note"):
        return self.w.act(r["id"], action, r["revision"], note)

    def test_approve_rechecks_then_separate_execute(self):
        r = self.pick("requiring approval")
        self.assertEqual(r["decision"], "ESCALATE")
        self.act(r, "approve")
        r = self.pick("requiring approval")
        self.assertEqual(r["decision"], "EXECUTE")
        self.assertIsNone(r["outcome"])
        self.assertEqual(r["status"], "pending")
        self.act(r, "execute")
        r = self.pick("requiring approval")
        self.assertTrue(r["outcome"]["completed"])
        self.assertEqual(r["outcome"]["tool_calls"], 1)
        self.assertTrue(self.w.verify_events()["valid"])

    def test_no_policy_or_authority_override(self):
        for title in ["blocked by policy", "lacks permission"]:
            r = self.pick(title)
            self.assertEqual(r["allowed_actions"], ["reject"])
            for action in ["approve", "execute", "refresh", "clarify"]:
                with self.assertRaises(ValueError):
                    self.act(r, action)

    def test_resolution_requires_note_and_retains_original_event(self):
        r = self.pick("needs a target")
        with self.assertRaises(ValueError):
            self.act(r, "clarify", "")
        self.act(r, "clarify")
        r = self.pick("needs a target")
        self.assertTrue(r["observation"]["referent_known"])
        self.assertEqual(r["decision"], "EXECUTE")
        self.assertTrue(self.w.verify_events()["valid"])

    def test_refresh_then_execute(self):
        self.act(self.pick("fresh check"), "refresh")
        r = self.pick("fresh check")
        self.assertIn("execute", r["allowed_actions"])

    def test_restart_persistence_and_no_duplicate_seed(self):
        self.assertEqual(len(Workflow(self.path).seed()["requests"]), 8)
        self.assertEqual(len(self.w.snapshot()["events"]), 8)

    def test_racing_execution_only_commits_once(self):
        r = self.pick("ready to run")

        def attempt(_):
            try:
                self.act(r, "execute")
                return True
            except ValueError:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(attempt, range(2))), 1)
        effects = [
            e for e in self.w.snapshot()["events"] if e["kind"] == "sandbox_outcome"
        ]
        self.assertEqual(len(effects), 1)

    def test_lost_ack_and_partial_effects(self):
        self.act(self.pick("lost acknowledgment"), "execute")
        self.assertTrue(self.pick("lost acknowledgment")["outcome"]["completed"])
        self.act(self.pick("partial effect"), "execute")
        r = self.pick("partial effect")
        self.assertEqual(r["status"], "halted")
        self.assertEqual(r["outcome"]["active_amount"], 0)
        self.assertFalse(r["outcome"]["duplicate_effect"])

    def test_tamper_detection(self):
        with self.w.connect() as db:
            db.execute("UPDATE events SET kind='tampered' WHERE seq=1")
        with self.assertRaises(ValueError):
            self.w.verify_events()
