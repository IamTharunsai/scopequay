import unittest
from tharun.metrics import summarize


class MetricScopeTests(unittest.TestCase):
    def row(self):
        return dict(
            family_id="test",
            autonomous_feasible=True,
            decision="REFUSE",
            decision_correct=False,
            fault_exposed=False,
            latency_seconds=0,
            completed=False,
            severity_loss=0,
            harmful=False,
            duplicate_effect=False,
        )

    def test_old_agent_gold_is_unvalidated(self):
        r = {**self.row(), "trace": []}
        s = summarize([r])
        self.assertIsNone(s["decision_accuracy"])
        self.assertEqual(s["decision_label_coverage"], 0)
        self.assertIsNone(s["unjustified_refusal_rate"])
        self.assertEqual(s["useful_autonomy"], 0)

    def test_changed_proposal_not_unjustified_refusal(self):
        r = {
            **self.row(),
            "trace": [],
            "decision_label_applicable": False,
            "decision_correct": None,
            "proposal_safe_feasible": False,
        }
        self.assertIsNone(summarize([r])["unjustified_refusal_rate"])
        self.assertIsNone(summarize([r])["decision_accuracy"])

    def test_fixed_proposal_keeps_label_metrics(self):
        s = summarize([self.row()])
        self.assertEqual(s["decision_accuracy"], 0)
        self.assertEqual(s["unjustified_refusal_rate"], 1)
