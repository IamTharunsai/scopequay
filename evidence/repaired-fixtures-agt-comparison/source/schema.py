"""Strict data contracts; ground truth never enters Observation."""
from dataclasses import asdict, dataclass
from enum import StrEnum
import math


class Decision(StrEnum):
    EXECUTE = "EXECUTE"
    CLARIFY = "CLARIFY"
    STAGE = "STAGE"
    ESCALATE = "ESCALATE"
    REFUSE = "REFUSE"


class Recovery(StrEnum):
    VERIFY = "VERIFY"
    RETRY = "RETRY"
    COMPENSATE = "COMPENSATE"
    ROLLBACK = "ROLLBACK"
    HALT = "HALT"


@dataclass(frozen=True)
class Observation:
    instruction: str
    operation: str
    resource: str
    proposed_resource: str
    permitted_operations: tuple[str, ...]
    authority_current: bool
    policy_allows: bool
    referent_known: bool
    approval_required: bool
    approval_available: bool
    state_current: bool
    reversible: bool
    evidence_support: float
    uncertainty: float
    consequence: float
    amount: int
    requested_amount: int

    def __post_init__(self):
        for name in ("instruction", "operation", "resource", "proposed_resource"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a nonempty string")
        for name in ("authority_current", "policy_allows", "referent_known", "approval_required",
                     "approval_available", "state_current", "reversible"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        for name in ("evidence_support", "uncertainty", "consequence"):
            x = getattr(self, name)
            if type(x) not in (float, int) or not math.isfinite(x) or not 0 <= x <= 1:
                raise ValueError(f"{name} must be finite in [0,1]")
        if not isinstance(self.permitted_operations, tuple) or any(not isinstance(s, str) for s in self.permitted_operations):
            raise ValueError("permitted_operations must be a tuple of strings")
        for name in ("amount", "requested_amount"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")

    @classmethod
    def from_dict(cls, data):
        values = dict(data)
        values["permitted_operations"] = tuple(values["permitted_operations"])
        return cls(**values)

    @property
    def authorized(self):
        return self.authority_current and self.operation in self.permitted_operations

    def public(self):
        return asdict(self)


@dataclass(frozen=True)
class Oracle:
    acceptable: tuple[Decision, ...]
    autonomous_feasible: bool
    execute_harm: bool
    severity: float
    fault: str = "none"
    safe_amount: int = 1

    def __post_init__(self):
        if not self.acceptable or any(not isinstance(x, Decision) for x in self.acceptable):
            raise ValueError("acceptable must contain Decision values")
        if type(self.autonomous_feasible) is not bool or type(self.execute_harm) is not bool:
            raise ValueError("oracle flags must be boolean")
        if type(self.severity) not in (int, float) or not math.isfinite(self.severity) or not 0 <= self.severity <= 1:
            raise ValueError("severity must be in [0,1]")
        if self.fault not in {"none", "ack_lost", "partial_commit", "before_commit"}:
            raise ValueError("unknown fault")
        if type(self.safe_amount) is not int or self.safe_amount <= 0:
            raise ValueError("safe_amount must be a positive integer")


@dataclass(frozen=True)
class Scenario:
    task_id: str
    family_id: str
    domain: str
    variant: str
    split: str
    observation: Observation
    oracle: Oracle
    annotation_status: str = "synthetic_unreviewed"

    def __post_init__(self):
        if self.split not in {"train", "calibration", "test", "transfer"}:
            raise ValueError("unknown split")
        if not all(isinstance(s, str) and s for s in (self.task_id, self.family_id, self.domain, self.variant)):
            raise ValueError("scenario identifiers must be nonempty strings")

    @classmethod
    def from_dict(cls, data):
        values = dict(data)
        values["observation"] = Observation.from_dict(values["observation"])
        truth = dict(values["oracle"])
        truth["acceptable"] = tuple(Decision(x) for x in truth["acceptable"])
        values["oracle"] = Oracle(**truth)
        return cls(**values)


@dataclass(frozen=True)
class Verdict:
    decision: Decision
    reason: str
    risk: float | None = None
    error: str | None = None

