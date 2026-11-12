"""Optional actual toolkit adapter, not a hand-written toolkit imitation.

Pinned package/source inspected locally: agent-governance-toolkit-core==5.0.0.
Official wrapper/API source: https://github.com/microsoft/agent-governance-toolkit
Only its agentmesh PolicyEngine is evaluated, not identity/sandbox/production AGT.
"""

from importlib.metadata import version
from pathlib import Path
import hashlib
from .schema import Decision as D, Verdict


class AGTController:
    name = "agt_policy"
    threshold = None

    def __init__(self):
        from agentmesh.governance.policy import PolicyEngine

        installed = version("agent-governance-toolkit-core")
        if installed != "5.0.0":
            raise ValueError(
                f"AGT adapter requires pinned core 5.0.0, found {installed}"
            )
        self.engine = PolicyEngine(conflict_strategy="priority_first_match")
        raw = Path(__file__).with_name("agt_policy.yaml").read_bytes()
        self.engine.load_yaml(raw.decode("utf-8"))
        self.dependency = {
            "package": "agent-governance-toolkit-core",
            "version": installed,
            "policy_sha256": hashlib.sha256(raw).hexdigest(),
            "scope": "agentmesh PolicyEngine only",
            "mapping": "allow->EXECUTE; approval->ESCALATE/REFUSE; deny reason handler->CLARIFY/STAGE/REFUSE",
        }
        self.last = {}

    def decide(self, x):
        # All transformations are deterministic functions of public observation.
        context = {
            "action": {"type": x.operation},
            "facts": {
                "policy": "allow" if x.policy_allows else "deny",
                "authority": "present" if x.authorized else "missing",
                "approval": "required" if x.approval_required else "not_required",
                "referent": "known" if x.referent_known else "unknown",
                "state": "current" if x.state_current else "stale",
                "intent": "match"
                if x.resource == x.proposed_resource and x.amount == x.requested_amount
                else "mismatch",
            },
        }
        native = self.engine.evaluate("tharun-pilot", context)
        self.last = {
            "native_agt": native.model_dump(mode="json"),
            "policy_sha256": self.dependency["policy_sha256"],
        }
        if native.action == "require_approval":
            decision = D.ESCALATE if x.approval_available else D.REFUSE
        elif native.allowed:
            decision = D.EXECUTE
        else:
            decision = {"missing_referent": D.CLARIFY, "stale_state": D.STAGE}.get(
                native.matched_rule, D.REFUSE
            )
        return Verdict(decision, f"agt:{native.matched_rule or native.action}")
