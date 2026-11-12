"""Persistent single-user approval demo. No real tool or model is invoked.

Demo outcomes are not research observations. All changes and simulated effects
commit in one SQLite transaction, so repeated approvals cannot duplicate effects.
"""

from dataclasses import replace
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

from tharun.controllers import Controller
from tharun.data import canonical, generate
from tharun.sandbox import execute
from tharun.schema import Decision, Observation, Oracle, Scenario

EXPLANATIONS = {
    "risk_within_threshold": "The supplied evidence passes this fixed gate's checks.",
    "approval_required": "This action needs your explicit approval before it can run.",
    "authority_missing": "The agent does not have permission for this operation. Approval cannot grant missing authority here.",
    "policy_denied": "The action violates the configured policy. It cannot be approved here.",
    "missing_referent": "Confirm the exact target before the agent acts.",
    "state_requires_refresh": "The underlying state needs a fresh check before execution.",
    "risk_exceeds_threshold": "The fixed risk heuristic requires an intervention.",
}


class Workflow:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, observation TEXT NOT NULL,
                    fault TEXT NOT NULL, status TEXT NOT NULL, decision TEXT NOT NULL,
                    reason TEXT NOT NULL, risk REAL, outcome TEXT, revision INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY, request_id TEXT NOT NULL, timestamp TEXT NOT NULL,
                    kind TEXT NOT NULL, detail TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def event(self, db, request_id, kind, detail):
        previous = db.execute(
            "SELECT hash FROM events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        body = dict(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            kind=kind,
            detail=detail,
            previous_hash=previous[0] if previous else "0" * 64,
        )
        digest = hashlib.sha256(canonical(body).encode()).hexdigest()
        db.execute(
            "INSERT INTO events(request_id,timestamp,kind,detail,previous_hash,hash) VALUES(?,?,?,?,?,?)",
            (
                request_id,
                body["timestamp"],
                kind,
                canonical(detail),
                body["previous_hash"],
                digest,
            ),
        )

    def seed(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT COUNT(*) FROM requests").fetchone()[0]:
                return self.snapshot(db)
            rows = generate()
            examples = [
                ("support", "high_consequence", "Refund requiring approval"),
                ("communications", "ambiguous", "Client message needs a target"),
                ("scheduling", "state_changed", "Appointment needs a fresh check"),
                ("saas_admin", "policy_conflict", "Role change blocked by policy"),
                ("support", "normal", "Routine refund ready to run"),
                ("devops", "ack_lost", "Restart with a lost acknowledgment"),
                ("data_ops", "unauthorized", "Record update lacks permission"),
                ("support", "partial_commit", "Refund with a partial effect"),
            ]
            for domain, variant, title in examples:
                row = next(
                    r for r in rows if r.domain == domain and r.variant == variant
                )
                obs = row.observation
                # Approval resolves approval_required, not a residual heuristic hold.
                if variant == "high_consequence":
                    obs = replace(obs, consequence=0.5)
                verdict = Controller("tharun_fixed").decide(obs)
                rid = uuid.uuid4().hex[:12]
                db.execute(
                    "INSERT INTO requests(id,title,observation,fault,status,decision,reason,risk) VALUES(?,?,?,?,?,?,?,?)",
                    (
                        rid,
                        title,
                        canonical(obs.public()),
                        row.oracle.fault,
                        "pending",
                        verdict.decision.value,
                        verdict.reason,
                        verdict.risk,
                    ),
                )
                self.event(
                    db,
                    rid,
                    "proposed",
                    {"decision": verdict.decision.value, "reason": verdict.reason},
                )
            return self.snapshot(db)

    def snapshot(self, db=None):
        if db is None:
            with self.connect() as connection:
                return self.snapshot(connection)
        requests = []
        for row in db.execute("SELECT * FROM requests ORDER BY rowid"):
            item = dict(row)
            item["observation"] = json.loads(item["observation"])
            item["outcome"] = json.loads(item["outcome"]) if item["outcome"] else None
            item["explanation"] = EXPLANATIONS.get(item["reason"], item["reason"])
            x = Observation.from_dict(item["observation"])
            item["allowed_actions"] = self.allowed(item, x)
            requests.append(item)
        events = []
        for row in db.execute("SELECT * FROM events ORDER BY seq"):
            event = dict(row)
            event["detail"] = json.loads(event["detail"])
            events.append(event)
        return {
            "brand": "ScopeQuay",
            "mode": "local_demo",
            "requests": requests,
            "events": events,
            "notice": "Illustrative, single-user approval demo. Effects stay in a local sandbox. These sessions are not benchmark evidence.",
        }

    @staticmethod
    def allowed(item, x):
        if item["status"] != "pending":
            return []
        actions = ["reject"]
        if not x.authorized or not x.policy_allows:
            return actions
        if item["decision"] == "EXECUTE":
            actions.append("execute")
        elif item["decision"] == "ESCALATE" and x.approval_required:
            actions.append("approve")
        elif item["decision"] == "CLARIFY":
            actions.append("clarify")
        elif item["decision"] == "STAGE" and not x.state_current:
            actions.append("refresh")
        return actions

    def act(self, request_id, action, revision, note=""):
        if type(revision) is not int or not isinstance(note, str) or len(note) > 500:
            raise ValueError("Invalid revision or note (maximum 500 characters)")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM requests WHERE id=?", (request_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Unknown request")
            item = dict(row)
            x = Observation.from_dict(json.loads(item["observation"]))
            if revision != item["revision"] or action not in self.allowed(item, x):
                raise ValueError(
                    "This request changed or the action is unavailable. Refresh the queue."
                )
            if (
                action in {"approve", "clarify", "refresh", "reject"}
                and not note.strip()
            ):
                raise ValueError("Add a short review note before continuing")
            status, outcome = "pending", None
            if action == "reject":
                status = "rejected"
            elif action == "approve":
                x = replace(x, approval_required=False)
            elif action == "clarify":
                x = replace(
                    x,
                    referent_known=True,
                    instruction=f"Confirmed target {x.resource}; operation {x.operation}; quantity {x.requested_amount}.",
                )
            elif action == "refresh":
                x = replace(x, state_current=True)
            verdict = Controller("tharun_fixed").decide(x)
            self.event(
                db,
                request_id,
                action,
                {"note": note.strip(), "decision": verdict.decision.value},
            )
            # Resolution re-evaluates the gate and leaves execution to a separate click.
            if action == "execute":
                if verdict.decision != Decision.EXECUTE:
                    raise ValueError("The gate no longer permits execution")
                unsafe = not (
                    x.authorized
                    and x.policy_allows
                    and x.referent_known
                    and x.state_current
                    and not x.approval_required
                    and x.resource == x.proposed_resource
                    and x.amount == x.requested_amount
                )
                scenario = Scenario(
                    request_id,
                    "demo",
                    "demo",
                    "interactive",
                    "test",
                    x,
                    Oracle(
                        (Decision.EXECUTE,),
                        not unsafe,
                        unsafe,
                        x.consequence,
                        item["fault"],
                        x.requested_amount,
                    ),
                    "demo_not_research",
                )
                outcome = execute(scenario, verdict.decision, recovery="verify")
                status = "completed" if outcome["completed"] else "halted"
                self.event(db, request_id, "sandbox_outcome", outcome)
            db.execute(
                "UPDATE requests SET observation=?,status=?,decision=?,reason=?,risk=?,outcome=?,revision=revision+1 WHERE id=?",
                (
                    canonical(x.public()),
                    status,
                    verdict.decision.value,
                    verdict.reason,
                    verdict.risk,
                    canonical(outcome) if outcome is not None else None,
                    request_id,
                ),
            )
            return self.snapshot(db)

    def verify_events(self):
        previous = "0" * 64
        for event in self.snapshot()["events"]:
            body = {
                k: event[k]
                for k in ("request_id", "timestamp", "kind", "detail", "previous_hash")
            }
            if (
                body["previous_hash"] != previous
                or hashlib.sha256(canonical(body).encode()).hexdigest() != event["hash"]
            ):
                raise ValueError("Audit chain mismatch")
            previous = event["hash"]
        return {"valid": True, "last_hash": previous}
