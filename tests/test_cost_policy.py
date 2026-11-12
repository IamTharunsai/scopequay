from dataclasses import replace
import copy
import unittest
from tharun.cost_policy import fit_cost_policy, CostPolicy, admissible, validate
from tharun.data import generate
from tharun.schema import Decision as D


class CostPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = generate()
        cls.train = [r for r in cls.rows if r.split == "train"]
        cls.cal = [r for r in cls.rows if r.split == "calibration"]
        cls.artifact = fit_cost_policy(cls.train, cls.cal)

    def case(self, name):
        return next(r for r in self.rows if r.variant == name).observation

    def test_calibration_constraints_and_minimum_cost_selection(self):
        actual = self.artifact["calibration"]
        self.assertLessEqual(actual["mean_loss"], 0.05)
        self.assertGreaterEqual(actual["useful_autonomy"], 0.5)
        feasible = [
            t
            for t in self.artifact["candidates"]
            if t["mean_loss"] <= 0.05 and t["useful_autonomy"] >= 0.5
        ]
        self.assertEqual(actual["mean_cost"], min(t["mean_cost"] for t in feasible))
        self.assertEqual(self.artifact["guarantee"], "empirical_only")

    def test_hard_constraints_override_objective(self):
        artifact = {
            **self.artifact,
            "risk_multiplier": 0.0,
            "utility_multiplier": 100.0,
        }
        policy = CostPolicy(artifact)
        self.assertEqual(policy.decide(self.case("policy_conflict")).decision, D.REFUSE)
        self.assertNotEqual(
            policy.decide(self.case("unauthorized")).decision, D.EXECUTE
        )
        self.assertNotEqual(
            policy.decide(self.case("high_consequence")).decision, D.EXECUTE
        )
        x = replace(self.case("normal"), amount=999)
        self.assertEqual(policy.decide(x).decision, D.REFUSE)

    def test_action_menu_is_observable_and_scenario_specific(self):
        self.assertIn(D.CLARIFY, admissible(self.case("ambiguous")))
        self.assertNotIn(D.CLARIFY, admissible(self.case("normal")))
        self.assertEqual(admissible(self.case("policy_conflict")), (D.REFUSE,))

    def test_no_test_fitting(self):
        with self.assertRaises(ValueError):
            fit_cost_policy([r for r in self.rows if r.split == "test"], self.cal)

    def test_infeasible_utility_constraint_is_not_silently_relaxed(self):
        with self.assertRaisesRegex(ValueError, "no empirically feasible"):
            fit_cost_policy(self.train, self.cal, minimum_autonomy=1.0)

    def test_malformed_artifact_rejected(self):
        bad = copy.deepcopy(self.artifact)
        bad["costs"]["REFUSE"] = -1.0
        with self.assertRaises(ValueError):
            validate(bad)
        bad = copy.deepcopy(self.artifact)
        bad["risk_weights"][0] = float("nan")
        with self.assertRaises(ValueError):
            validate(bad)


if __name__ == "__main__":
    unittest.main()
