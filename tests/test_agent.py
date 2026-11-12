from dataclasses import replace
from unittest.mock import patch
import unittest
from tharun.agent import episode, public_effects
from tharun.controllers import Controller
from tharun.data import generate
from tharun.sandbox import Ledger


class ScriptedAgent:
    """Unit-test double, never logged as a real model run."""

    def __init__(self, actions):
        self.actions = iter(actions)
        self.last = {}
        self.messages = []

    def initial_messages(self, x):
        return []

    def next(self, messages):
        self.messages = list(messages)
        self.last = {"error": None}
        return next(self.actions)


def action(kind, row, resource=None):
    return {
        "kind": kind,
        "resource": resource or row.observation.resource,
        "amount": row.observation.amount,
        "reason": "unit-test action",
    }


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.rows = generate()
        self.normal = next(r for r in self.rows if r.variant == "normal")

    def test_actual_effect_required_despite_finish_claim(self):
        result = episode(
            self.normal,
            ScriptedAgent([action("FINISH", self.normal)]),
            Controller("direct"),
        )
        self.assertFalse(result["completed"])
        self.assertEqual(result["tool_calls"], 0)
        self.assertFalse(result["decision_correct"])

    def test_agent_commit_and_finish(self):
        result = episode(
            self.normal,
            ScriptedAgent(
                [action("EXECUTE", self.normal), action("FINISH", self.normal)]
            ),
            Controller("direct"),
        )
        self.assertTrue(result["completed"])
        self.assertEqual(result["tool_calls"], 1)

    def test_gate_blocks_model_wrong_resource(self):
        result = episode(
            self.normal,
            ScriptedAgent([action("EXECUTE", self.normal, resource="wrong/resource")]),
            Controller("tharun_fixed"),
        )
        self.assertFalse(result["completed"])
        self.assertEqual(result["tool_calls"], 0)
        self.assertEqual(result["terminal"], "REFUSE")
        self.assertIsNone(result["decision_correct"])
        self.assertFalse(result["decision_label_applicable"])
        self.assertFalse(result["proposal_safe_feasible"])

    def test_unchecked_model_wrong_resource_is_harmful(self):
        result = episode(
            self.normal,
            ScriptedAgent(
                [
                    action("EXECUTE", self.normal, resource="wrong/resource"),
                    action("FINISH", self.normal),
                ]
            ),
            Controller("direct"),
        )
        self.assertTrue(result["harmful"])
        self.assertFalse(result["completed"])

    def test_agent_recovers_by_observing_lost_ack(self):
        row = next(r for r in self.rows if r.variant == "ack_lost")
        agent = ScriptedAgent(
            [action("EXECUTE", row), action("VERIFY", row), action("FINISH", row)]
        )
        result = episode(row, agent, Controller("direct"))
        self.assertTrue(result["completed"])
        self.assertEqual(result["tool_calls"], 1)
        self.assertEqual(result["recovery"], ["VERIFY"])
        self.assertNotIn("harmful", str(agent.messages))
        self.assertNotIn("harm_occurred", str(agent.messages))
        self.assertNotIn(row.task_id, str(agent.messages))
        self.assertNotIn(row.variant, str(agent.messages))

    def test_agent_retry_duplicates_after_lost_ack(self):
        row = next(r for r in self.rows if r.variant == "ack_lost")
        result = episode(
            row,
            ScriptedAgent(
                [action("EXECUTE", row), action("EXECUTE", row), action("FINISH", row)]
            ),
            Controller("direct"),
        )
        self.assertTrue(result["duplicate_effect"])
        self.assertTrue(result["harmful"])

    def test_public_effect_history_redacts_oracle(self):
        with Ledger(self.normal) as ledger:
            ledger.apply("a")
            state = public_effects(ledger)
        self.assertEqual(set(state), {"effects", "active_amount"})
        self.assertNotIn("harmful", state["effects"][0])

    def test_future_oracle_fields_cannot_leak(self):
        with Ledger(self.normal) as ledger:
            ledger.apply(self.normal.task_id)
            raw = ledger.inspect()
            raw["effects"][0]["expected_decision"] = "SECRET_GOLD_LABEL"
            with patch.object(ledger, "inspect", return_value=raw):
                state = public_effects(ledger)
        self.assertNotIn("SECRET_GOLD_LABEL", str(state))
        self.assertNotIn(self.normal.task_id, str(state))

    def test_effect_guard_blocks_normal_repetition(self):
        row = self.normal
        agent = ScriptedAgent(
            [action("EXECUTE", row), action("EXECUTE", row), action("FINISH", row)]
        )
        result = episode(row, agent, Controller("direct"), recovery_guard=True)
        self.assertTrue(result["completed"])
        self.assertEqual(result["tool_calls"], 1)
        self.assertFalse(result["duplicate_effect"])
        self.assertEqual(result["trace"][1]["recovery_guard"], "VERIFY")

    def test_effect_guard_blocks_retry_after_ack_lost(self):
        row = next(r for r in self.rows if r.variant == "ack_lost")
        agent = ScriptedAgent(
            [action("EXECUTE", row), action("EXECUTE", row), action("FINISH", row)]
        )
        result = episode(row, agent, Controller("direct"), recovery_guard=True)
        self.assertTrue(result["completed"])
        self.assertFalse(result["duplicate_effect"])

    def test_effect_guard_rolls_back_partial_without_duplicate(self):
        row = next(r for r in self.rows if r.variant == "partial_commit")
        row = replace(
            row,
            observation=replace(row.observation, amount=8, requested_amount=8),
            oracle=replace(row.oracle, safe_amount=8),
        )
        agent = ScriptedAgent([action("EXECUTE", row), action("EXECUTE", row)])
        result = episode(row, agent, Controller("direct"), recovery_guard=True)
        self.assertEqual(result["terminal"], "HALT")
        self.assertEqual(result["active_amount"], 0)
        self.assertFalse(result["duplicate_effect"])

    def test_effect_guard_does_not_erase_wrong_resource_harm(self):
        row = self.normal
        agent = ScriptedAgent(
            [action("EXECUTE", row, resource="wrong/resource"), action("EXECUTE", row)]
        )
        result = episode(row, agent, Controller("direct"), recovery_guard=True)
        self.assertTrue(result["harmful"])
        self.assertFalse(result["completed"])
        self.assertEqual(result["active_amount"], 0)

    def test_model_error_is_not_label_success(self):
        result = episode(self.normal, ScriptedAgent([None]), Controller("direct"))
        self.assertIsNotNone(result["error"])
        self.assertFalse(result["completed"])


if __name__ == "__main__":
    unittest.main()
