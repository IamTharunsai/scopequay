"""Export synthetic fixed-proposal evidence with no local machine paths.

Run locally where historical run folders exist. Original bytes remain untouched.
"""

from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tharun.experiment import verify_log, group_summary

root = Path(__file__).resolve().parents[1]
out = root / "evidence"
out.mkdir(exist_ok=True)
selected = [
    "repaired-fixtures-agt-comparison",
    "native-dogwood-test",
    "exploratory-cost-policy",
]
records = []
for name in selected:
    path = root / "runs" / name
    rows = verify_log(path)
    manifest_bytes = (path / "manifest.json").read_bytes()
    m = json.loads(manifest_bytes)
    if m["status"] != "completed":
        raise ValueError("Only completed runs can be exported")
    dest = out / name
    dest.mkdir(exist_ok=True)
    (dest / "outcomes.jsonl").write_bytes((path / "outcomes.jsonl").read_bytes())
    safe = {
        k: m[k]
        for k in [
            "status",
            "records",
            "final_record_hash",
            "run_id",
            "dataset_sha256",
            "code_hashes",
            "split",
            "created_at",
            "experiment_type",
            "annotation_status",
            "paid_api_spend_usd",
        ]
    }
    safe["export_note"] = (
        "Redacted metadata copy; outcome bytes unchanged. Machine paths/configuration omitted. Original manifest hash is in provenance."
    )
    (dest / "manifest.json").write_text(json.dumps(safe, indent=2), encoding="utf-8")
    summary = group_summary(rows)
    (dest / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    source = dest / "source"
    source.mkdir(exist_ok=True)
    for filename, digest in m["code_hashes"].items():
        data = (path / "source" / filename).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        (source / filename).write_bytes(data)
    records.append(
        {
            "run": name,
            "original_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "outcomes_sha256": hashlib.sha256(
                (dest / "outcomes.jsonl").read_bytes()
            ).hexdigest(),
            "source_files_verified": len(m["code_hashes"]),
            "summary": summary,
        }
    )
analysis = out / "analysis_source"
analysis.mkdir(exist_ok=True)
for name in ["metrics.py", "experiment.py"]:
    (analysis / name).write_bytes((root / "tharun" / name).read_bytes())
(out / "pilot-summary.json").write_text(
    json.dumps(
        {
            "status": "synthetic_unreviewed_engineering_pilot",
            "analysis_source_sha256": {
                f: hashlib.sha256((root / "tharun" / f).read_bytes()).hexdigest()
                for f in ["metrics.py", "experiment.py"]
            },
            "runs": records,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps({"exported_runs": len(records), "path": str(out)}))
