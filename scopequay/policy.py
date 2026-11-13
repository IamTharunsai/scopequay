"""Small SDK for reviewing supplied action facts. It never executes tools."""

from dataclasses import asdict
from tharun.controllers import Controller
from tharun.schema import Observation


def assess(observation):
    if not isinstance(observation, dict):
        raise ValueError("Action context must be a JSON object")
    if not isinstance(observation.get("permitted_operations"), list):
        raise ValueError("permitted_operations must be a JSON array")
    x = Observation.from_dict(observation)
    verdict = Controller("tharun_fixed").decide(x)
    return {
        "schema_version": 1,
        **asdict(verdict),
        "controller": "fixed_reference",
        "tool_executed": False,
        "boundary": "Assessment of supplied facts only; not authenticated authorization or a global tool-call interceptor.",
    }
