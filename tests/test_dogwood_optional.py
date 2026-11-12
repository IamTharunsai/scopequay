from pathlib import Path
from dataclasses import replace
import os
import unittest
from tharun.data import generate
from tharun.schema import Decision
from tharun.dogwood import DogwoodController


@unittest.skipUnless(
    os.environ.get("THARUN_DOGWOOD_BIN")
    or Path("external/dogwood/target/debug/dogwood.exe").exists(),
    "optional native Dogwood CLI unavailable",
)
class NativeDogwoodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = DogwoodController()
        cls.rows = generate()

    def test_native_policy_all_variants(self):
        for row in self.rows[:8]:
            with self.subTest(variant=row.variant):
                v = self.gate.decide(row.observation)
                self.assertIsNone(v.error)
                self.assertIn(v.decision, row.oracle.acceptable)
                self.assertIn("native_dogwood", self.gate.last)

    def test_native_deny_changed_arguments(self):
        row = next(r for r in self.rows if r.variant == "normal")
        v = self.gate.decide(
            replace(row.observation, proposed_resource="wrong/resource")
        )
        self.assertIsNone(v.error)
        self.assertEqual(v.decision, Decision.REFUSE)
        self.assertEqual(
            self.gate.last["native_dogwood"]["verdicts"][0]["verdict"], "deny"
        )

    def test_unknown_action_is_error_not_successful_refusal(self):
        row = self.rows[0]
        v = self.gate.decide(replace(row.observation, operation="unknown_action"))
        self.assertIsNotNone(v.error)
