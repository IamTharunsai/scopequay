"""Optional native Dogwood reference CLI, restricted to a single-request fact policy.

The CLI produces allow/deny. Five-way intervention reasons are a THARUN wrapper.
No temporal policy, AWS service, or production enforcement claim is made here.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .data import canonical, sha256_file
from .schema import Decision as D, Verdict

SOURCE_COMMIT = "4ec5e2c01b44ff3882a231ae5d315b330b38fa25"


class DogwoodController:
    name = "dogwood_point_policy"
    threshold = None

    def __init__(self, binary=None):
        root = Path(__file__).resolve().parents[1]
        self.binary = Path(
            binary
            or os.environ.get("THARUN_DOGWOOD_BIN", "")
            or root / "external/dogwood/target/debug/dogwood.exe"
        ).resolve()
        if not self.binary.is_file():
            raise FileNotFoundError(
                "Build the pinned native Dogwood CLI or set THARUN_DOGWOOD_BIN"
            )
        self.schema = Path(__file__).with_name("dogwood_schema.cedarschema")
        self.policy = Path(__file__).with_name("dogwood_policy.dw")
        checks = []
        for args in (
            ["schema", "action", str(self.schema)],
            ["validate", str(self.policy), "--policy-schema", str(self.schema)],
        ):
            p = self._run(args)
            checks.append({"args": args, "stdout": p.stdout, "stderr": p.stderr})
        self.dependency = {
            "source_url": "https://github.com/dogwood-policy/dogwood",
            "build_source_commit": SOURCE_COMMIT,
            "source_pin_status": "build provenance is in artifacts/dogwood_probe_rust195_resume.json; custom binaries require separate verification",
            "binary_sha256": sha256_file(self.binary),
            "policy_sha256": sha256_file(self.policy),
            "schema_sha256": sha256_file(self.schema),
            "scope": "native CLI single-request public-fact policy; deny reason mapping in wrapper",
            "checks": checks,
        }
        self.cache = {}
        self.last = {}

    def _run(self, args):
        p = subprocess.run(
            [str(self.binary), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        if p.returncode:
            raise RuntimeError(f"Dogwood exit {p.returncode}: {p.stderr[:1000]}")
        return p

    def decide(self, x):
        key = hashlib.sha256(canonical(x.public()).encode()).hexdigest()
        if key in self.cache:
            verdict, info = self.cache[key]
            self.last = {**info, "native_cache_hit": True}
            return verdict
        try:
            facts = {
                "authorized": x.authorized,
                "policy_allows": x.policy_allows
                and x.operation in x.permitted_operations,
                "approval_required": x.approval_required,
                "referent_known": x.referent_known,
                "state_current": x.state_current,
                "intent_match": x.proposed_resource == x.resource
                and x.amount == x.requested_amount,
            }
            # All identifiers are fixed or taken from the schema's closed action set.
            allowed_ops = {
                "restart",
                "change_role",
                "refund",
                "publish",
                "void",
                "send",
                "cancel",
                "update",
            }
            if x.operation not in allowed_ops:
                raise ValueError("operation absent from native schema")
            inp = (
                "{ resource: "
                + json.dumps(x.proposed_resource)
                + ", amount: "
                + str(x.amount)
                + " }"
            )
            system = (
                "{ "
                + ", ".join(k + ": " + str(v).lower() for k, v in facts.items())
                + " }"
            )
            trace = (
                f'@0 scope(principal: TH::Agent::"pilot", resource: TH::Gateway::"sandbox") '
                f'request_context(input: {inp}, system: {system}) TH::Action::"{x.operation}"::request('
                f'input: {inp}, callerPrincipal: TH::Agent::"pilot", callerResource: TH::Gateway::"sandbox", requestId: "request")\n'
            )
            with tempfile.TemporaryDirectory(prefix="tharun-dogwood-") as temp:
                path = Path(temp) / "request.log"
                path.write_text(trace, encoding="utf-8")
                p = self._run(
                    [
                        "replay",
                        str(self.policy),
                        "--policy-schema",
                        str(self.schema),
                        "--trace",
                        str(path),
                        "--format",
                        "json",
                    ]
                )
            output = json.loads(p.stdout)
            native = output["verdicts"]
            if (
                len(native) != 1
                or native[0].get("errors")
                or native[0]["verdict"] not in {"allow", "deny"}
            ):
                raise ValueError("invalid native verdict or evaluation errors")
            if native[0]["verdict"] == "allow":
                decision = D.EXECUTE
            elif not facts["policy_allows"] or not x.authorized:
                decision = D.REFUSE
            elif x.approval_required:
                decision = D.ESCALATE if x.approval_available else D.REFUSE
            elif not x.referent_known:
                decision = D.CLARIFY
            elif not x.state_current:
                decision = D.STAGE
            else:
                decision = D.REFUSE
            verdict = Verdict(decision, "dogwood:" + native[0]["verdict"])
            self.last = {
                "native_dogwood": output,
                "native_trace": trace,
                "native_cache_hit": False,
            }
            self.cache[key] = (verdict, dict(self.last))
            return verdict
        except (
            OSError,
            subprocess.SubprocessError,
            ValueError,
            KeyError,
            RuntimeError,
        ) as exc:
            self.last = {"native_error": str(exc), "native_cache_hit": False}
            return Verdict(D.REFUSE, "dogwood_error", error=str(exc))
