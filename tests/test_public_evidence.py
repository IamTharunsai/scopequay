import hashlib
import json
from pathlib import Path
import unittest
from tharun.experiment import verify_log, group_summary


class PublicEvidenceTests(unittest.TestCase):
    def test_public_record_chains_sources_and_summaries(self):
        path = Path("evidence/pilot-summary.json")
        if not path.exists():
            self.skipTest("Run the public evidence exporter before release")
        public = json.loads(path.read_text(encoding="utf-8"))
        for name, digest in public["analysis_source_sha256"].items():
            self.assertEqual(
                hashlib.sha256(
                    (Path("evidence/analysis_source") / name).read_bytes()
                ).hexdigest(),
                digest,
            )
        for item in public["runs"]:
            root = Path("evidence") / item["run"]
            rows = verify_log(root)
            self.assertEqual(
                hashlib.sha256((root / "outcomes.jsonl").read_bytes()).hexdigest(),
                item["outcomes_sha256"],
            )
            m = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            for name, digest in m["code_hashes"].items():
                self.assertEqual(
                    hashlib.sha256((root / "source" / name).read_bytes()).hexdigest(),
                    digest,
                )
            self.assertEqual(group_summary(rows), item["summary"])
