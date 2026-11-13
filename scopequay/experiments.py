"""Bounded, local-only experiment backend over the existing research engine.

Approval-demo data never enters an experiment. Cloud providers are unsupported.
One worker per service; files persist, but this is not a durable distributed queue.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import threading
import uuid

from tharun.controllers import create_controller, fit
from tharun.data import load_dataset, sha256_file
from tharun.experiment import (
    RunWriter,
    evaluate,
    group_summary,
    select_balanced,
    verify_log,
)
from tharun.local_models import LocalOllama
from tharun.report import generate_report

SYSTEMS = ("direct", "static_policy", "tharun_fixed", "tharun_calibrated")


class ExperimentService:
    def __init__(self, root, dataset):
        self.root = Path(root).resolve()
        self.dataset = Path(dataset).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.worker = None
        # Restart cannot resume a model's in-flight call. Never advertise it as completed.
        for path in self.root.glob("*/job.json"):
            job = json.loads(path.read_text(encoding="utf-8"))
            if job["status"] in {"queued", "running"}:
                job.update(
                    status="interrupted",
                    error="Backend restarted; create a new experiment",
                )
                self._write(job)

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def _write(self, job):
        directory = self.root / job["id"]
        directory.mkdir(exist_ok=True)
        temp = directory / "job.tmp"
        temp.write_text(json.dumps(job, indent=2), encoding="utf-8")
        temp.replace(directory / "job.json")

    def get(self, job_id):
        if not isinstance(job_id, str) or re.fullmatch(r"[0-9a-f]{32}", job_id) is None:
            raise ValueError("Invalid experiment ID")
        path = self.root / job_id / "job.json"
        if not path.exists():
            raise ValueError("Unknown experiment")
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self):
        return sorted(
            [self.get(p.parent.name) for p in self.root.glob("*/job.json")],
            key=lambda x: x["created_at"],
            reverse=True,
        )

    def validate(self, payload):
        if not isinstance(payload, dict) or set(payload) - {
            "mode",
            "provider",
            "model",
            "systems",
            "limit",
            "max_steps",
            "max_calls",
            "max_seconds",
            "split",
            "recovery",
        }:
            raise ValueError(
                "Unknown experiment options; paths, prompts and provider URLs cannot be supplied"
            )
        config = {
            "mode": "fixed_proposal",
            "provider": "local_ollama",
            "model": None,
            "systems": ["direct", "tharun_fixed"],
            "limit": 2,
            "max_steps": 4,
            "max_calls": 32,
            "max_seconds": 180,
            "split": "test",
            "recovery": "verify",
            **payload,
        }
        if config["provider"] != "local_ollama":
            raise ValueError(
                "Only installed local Ollama models are enabled; cloud APIs and paid inference are disabled"
            )
        if config["mode"] not in {"fixed_proposal", "agent"} or config["split"] not in {
            "test",
            "transfer",
            "evaluation",
        }:
            raise ValueError("Invalid mode or split")
        if config["recovery"] not in {"verify", "naive", "idempotent", "halt"}:
            raise ValueError("Invalid recovery mode")
        if config["mode"] == "agent" and config["recovery"] != "verify":
            raise ValueError(
                "Agent comparisons currently use the common effect-history guard"
            )
        for name, low, high in [
            ("limit", 1, 8 if config["mode"] == "agent" else 152),
            ("max_steps", 1, 4),
            ("max_calls", 1, 64),
            ("max_seconds", 1, 600),
        ]:
            if type(config[name]) is not int or not low <= config[name] <= high:
                raise ValueError(f"{name} must be an integer in [{low}, {high}]")
        systems = config["systems"]
        if (
            not isinstance(systems, list)
            or not 1 <= len(systems) <= 3
            or any(s not in SYSTEMS for s in systems)
            or len(set(systems)) != len(systems)
        ):
            raise ValueError("Choose 1–3 distinct supported controllers")
        if config["mode"] == "agent":
            if not isinstance(config["model"], str):
                raise ValueError("Select an exact installed local model tag")
            if (
                config["limit"] * config["max_steps"] * len(systems)
                > config["max_calls"]
            ):
                raise ValueError(
                    "Worst-case episode calls exceed max_calls; reduce scenarios, steps or controllers"
                )
            metadata = LocalOllama(timeout=3).installed(config["model"])
            if metadata.get("size", 0) > 3_500_000_000:
                raise ValueError(
                    "This laptop pilot limits installed model size to 3.5 GB"
                )
        elif config["model"] is not None:
            raise ValueError("Fixed-proposal mode invokes no model; use model=null")
        if not self.dataset.is_file():
            raise ValueError(
                "Research fixture unavailable; start from the repository or supply --dataset at server startup"
            )
        return config

    def submit(self, payload):
        config = self.validate(payload)
        with self.lock:
            if self.worker is not None and self.worker.is_alive():
                raise ValueError("One experiment is already running on this laptop")
            job = {
                "id": uuid.uuid4().hex,
                "created_at": self.now(),
                "status": "queued",
                "config": config,
                "dataset_sha256": sha256_file(self.dataset),
                "paid_api_spend_usd": 0,
                "annotation_status": "synthetic_unreviewed",
                "error": None,
                "summary": None,
            }
            self._write(job)
            self.worker = threading.Thread(
                target=self._run, args=(job["id"],), daemon=True
            )
            self.worker.start()
        return job

    def _run(self, job_id):
        job = self.get(job_id)
        writer = None
        try:
            job.update(status="running", started_at=self.now())
            backend_source = self.root / job_id / "backend_source"
            backend_source.mkdir()
            for filename in ["experiments.py", "server.py"]:
                (backend_source / filename).write_bytes(
                    Path(__file__).with_name(filename).read_bytes()
                )
            job["backend_source_sha256"] = {
                p.name: sha256_file(p) for p in backend_source.iterdir()
            }
            self._write(job)
            if sha256_file(self.dataset) != job["dataset_sha256"]:
                raise ValueError("Fixture changed after experiment submission")
            config = job["config"]
            rows = load_dataset(self.dataset)
            selected = select_balanced(
                [
                    r
                    for r in rows
                    if r.split == config["split"]
                    or (
                        config["split"] == "evaluation"
                        and r.split in {"test", "transfer"}
                    )
                ],
                config["limit"],
            )
            artifact = None
            (self.root / job_id / "contexts.json").write_text(
                json.dumps(
                    {r.task_id: r.observation.public() for r in selected}, indent=2
                ),
                encoding="utf-8",
            )
            if "tharun_calibrated" in config["systems"]:
                artifact = fit(
                    [r for r in rows if r.split == "train"],
                    [r for r in rows if r.split == "calibration"],
                )
                artifact["dataset_sha256"] = job["dataset_sha256"]
                (self.root / job_id / "calibration.json").write_text(
                    json.dumps(artifact, indent=2), encoding="utf-8"
                )
            gates = [create_controller(name, artifact) for name in config["systems"]]
            manifest = {
                "config": config,
                "dataset_sha256": job["dataset_sha256"],
                "selected_task_ids": [r.task_id for r in selected],
                "split": config["split"],
                "systems": config["systems"],
                "local_only": True,
                "source": "experiment_backend",
                "entry_point": "experiment_backend",
                "backend_source_sha256": job["backend_source_sha256"],
                "experiment_job_id": job_id,
                "recovery_mode": "effect_history_guard"
                if config["mode"] == "agent"
                else config["recovery"],
            }
            agent = None
            if config["mode"] == "agent":
                from tharun.agent import LocalAgent

                agent = LocalAgent(
                    config["model"],
                    timeout=60,
                    max_calls=config["max_calls"],
                    cache_dir=self.root / "agent-cache",
                )
                manifest.update(
                    model_inventory=[agent.metadata], server_version=agent.version
                )
            writer = RunWriter(self.root / job_id / "run", manifest)
            if agent:
                from tharun.agent import evaluate_agents

                writer.manifest["experiment_type"] = "synthetic_closed_loop_agent"
                writer._manifest()
                result = evaluate_agents(
                    selected,
                    agent,
                    gates,
                    writer,
                    config["max_steps"],
                    config["max_seconds"],
                    recovery_guard=True,
                )
                job["inference_calls"] = agent.calls
            else:
                result = evaluate(
                    selected,
                    gates,
                    writer,
                    recovery=config["recovery"],
                    max_seconds=config["max_seconds"],
                )
                job["inference_calls"] = 0
            if result:
                generate_report(writer.path, result, writer.manifest)
            job["summary"] = group_summary(result) if result else []
            job["records"] = len(result)
            status = writer.manifest["status"]
            job["status"] = (
                (
                    "completed_with_errors"
                    if any(r.get("error") for r in result)
                    else "completed"
                )
                if status == "completed"
                else status
            )
            job["final_record_hash"] = writer.manifest["final_record_hash"]
        except Exception as exc:
            if writer is not None and writer.manifest["status"] == "running":
                writer.finish("failed", type(exc).__name__)
            job.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        finally:
            job["finished_at"] = self.now()
            self._write(job)

    def results(self, job_id):
        job = self.get(job_id)
        if job["status"] in {"queued", "running"}:
            raise ValueError(
                "Experiment still running; poll its status before fetching results"
            )
        path = self.root / job_id / "run"
        rows = verify_log(path) if (path / "manifest.json").exists() else []
        return {
            "job": job,
            "outcomes": rows,
            "scenario_context": json.loads(
                (self.root / job_id / "contexts.json").read_text(encoding="utf-8")
            )
            if (self.root / job_id / "contexts.json").exists()
            else {},
            "slices": {
                field: {
                    value: group_summary([r for r in rows if r[field] == value])
                    for value in sorted({r[field] for r in rows})
                }
                for field in ["domain", "variant", "split"]
            },
            "notice": "Synthetic unreviewed evaluation; no deployment safety guarantee. Cached model responses are not fresh independent inference.",
        }
