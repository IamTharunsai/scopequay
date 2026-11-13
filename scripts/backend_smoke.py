"""Run an actual backend fixed-proposal smoke; never invokes an LLM or paid API."""

import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from scopequay.experiments import ExperimentService

service = ExperimentService(
    root / "local-data/experiments", root / "data/pilot_v0_2.jsonl"
)
job = service.submit({"limit": 8, "systems": ["direct", "tharun_fixed"]})
while service.worker.is_alive():
    service.worker.join(timeout=1)
result = service.results(job["id"])
if result["job"]["status"] != "completed":
    raise SystemExit(result["job"]["error"] or result["job"]["status"])
record = {
    "job_id": job["id"],
    "status": result["job"]["status"],
    "verified_records": len(result["outcomes"]),
    "mode": "fixed_proposal",
    "inference_calls": result["job"]["inference_calls"],
    "paid_api_spend_usd": 0,
    "summary": result["job"]["summary"],
}
(root / "artifacts").mkdir(exist_ok=True)
(root / "artifacts/backend_smoke_latest.json").write_text(
    json.dumps(record, indent=2), encoding="utf-8"
)
print(json.dumps(record, indent=2))
