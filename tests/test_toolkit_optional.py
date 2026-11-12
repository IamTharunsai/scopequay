from dataclasses import replace
import importlib.util
import unittest
from tharun.data import generate
from tharun.schema import Decision as D

HAS_TOOLKIT = importlib.util.find_spec("agentmesh") is not None


@unittest.skipUnless(
    HAS_TOOLKIT,
    "optional pinned Microsoft toolkit environment is not installed in this Python",
)
class ActualToolkitTests(unittest.TestCase):
    def setUp(self):
        from tharun.third_party import AGTController

        self.controller = AGTController()
        self.rows = generate()

    def case(self, variant):
        return next(r for r in self.rows if r.variant == variant).observation

    def test_real_engine_allow_and_deny(self):
        self.assertEqual(
            self.controller.decide(self.case("normal")).decision, D.EXECUTE
        )
        self.assertEqual(
            self.controller.decide(self.case("policy_conflict")).decision, D.REFUSE
        )
        self.assertEqual(self.controller.last["native_agt"]["action"], "deny")

    def test_explicit_reason_mapping_and_native_approval(self):
        self.assertEqual(
            self.controller.decide(self.case("ambiguous")).decision, D.CLARIFY
        )
        self.assertEqual(
            self.controller.decide(self.case("state_changed")).decision, D.STAGE
        )
        self.assertEqual(
            self.controller.decide(self.case("unauthorized")).decision, D.ESCALATE
        )
        self.assertEqual(
            self.controller.last["native_agt"]["action"], "require_approval"
        )
        self.assertEqual(
            self.controller.decide(
                replace(self.case("unauthorized"), approval_available=False)
            ).decision,
            D.REFUSE,
        )

    def test_native_deny_on_intent_mismatch(self):
        x = replace(self.case("normal"), proposed_resource="wrong/resource")
        self.assertEqual(self.controller.decide(x).decision, D.REFUSE)
        self.assertEqual(
            self.controller.last["native_agt"]["matched_rule"], "intent_mismatch"
        )


if __name__ == "__main__":
    unittest.main()
