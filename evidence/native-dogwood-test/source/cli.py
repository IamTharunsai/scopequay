import argparse
from collections import Counter
from pathlib import Path
import json
from .controllers import create_controller, fit, load_artifact
from .data import generate, write_dataset, load_dataset, annotation_export, sha256_file
from .experiment import RunWriter, evaluate, verify_log, select_balanced
from .local_models import LocalOllama, ModelController
from .report import generate_report
from .annotations import agreement


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="THARUN local-only research prototype; synthetic unreviewed fixtures"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--out", default="data/pilot.jsonl")
    g.add_argument("--families-per-domain", type=int, default=5)
    g.add_argument("--seed", type=int, default=20261023)
    v = sub.add_parser("validate")
    v.add_argument("--data", default="data/pilot.jsonl")
    a = sub.add_parser("annotate")
    a.add_argument("--data", default="data/pilot.jsonl")
    a.add_argument("--out", default="data/annotation_form.csv")
    aa = sub.add_parser("agreement")
    aa.add_argument("--data", default="data/pilot.jsonl")
    aa.add_argument("--a", required=True)
    aa.add_argument("--b", required=True)
    c = sub.add_parser("calibrate")
    c.add_argument("--data", default="data/pilot.jsonl")
    c.add_argument("--alpha", type=float, default=0.05)
    c.add_argument("--out", default="artifacts/calibration.json")
    cc = sub.add_parser("cost-calibrate")
    cc.add_argument("--data", default="data/pilot_v0_2.jsonl")
    cc.add_argument("--alpha", type=float, default=0.05)
    cc.add_argument("--minimum-autonomy", type=float, default=0.5)
    cc.add_argument("--out", default="artifacts/cost_calibration_v0_2.json")
    sub.add_parser("models")
    run = sub.add_parser("run")
    run.add_argument("--data", default="data/pilot.jsonl")
    run.add_argument("--artifact", default="artifacts/calibration.json")
    run.add_argument("--out", required=True)
    run.add_argument(
        "--systems",
        nargs="+",
        default=[
            "direct",
            "static_policy",
            "intent_permission",
            "tharun_fixed",
            "tharun_calibrated",
            "refuse_all",
        ],
    )
    run.add_argument(
        "--split", choices=["train", "calibration", "test", "transfer"], default="test"
    )
    run.add_argument("--limit", type=int, default=0)
    run.add_argument("--model", default="llama3.2:3b")
    run.add_argument("--repeats", type=int, default=1)
    run.add_argument("--timeout", type=float, default=180)
    run.add_argument("--max-calls", type=int, default=64)
    run.add_argument("--max-seconds", type=float, default=1800)
    run.add_argument(
        "--recovery",
        choices=["verify", "naive", "idempotent", "compensate", "halt"],
        default="verify",
    )
    run.add_argument(
        "--thresholds",
        nargs="*",
        type=float,
        help="Exploratory threshold sweep for fixed/calibrated controllers",
    )
    run.add_argument("--cost-artifact", default="artifacts/cost_calibration_v0_2.json")
    ag = sub.add_parser("agent-run")
    ag.add_argument("--data", default="data/pilot.jsonl")
    ag.add_argument("--artifact", default="artifacts/calibration.json")
    ag.add_argument("--out", required=True)
    ag.add_argument(
        "--systems", nargs="+", default=["direct", "tharun_fixed", "tharun_calibrated"]
    )
    ag.add_argument("--split", choices=["test", "transfer"], default="test")
    ag.add_argument("--model", default="llama3.2:3b")
    ag.add_argument("--limit", type=int, default=8)
    ag.add_argument("--timeout", type=float, default=120)
    ag.add_argument("--max-calls", type=int, default=64)
    ag.add_argument("--max-seconds", type=float, default=900)
    ag.add_argument("--max-steps", type=int, default=4)
    ag.add_argument("--guarded-prompt", action="store_true")
    ag.add_argument(
        "--recovery-guard",
        action="store_true",
        help="Verify observable effect history before a subsequent mutation",
    )
    ag.add_argument("--cost-artifact", default="artifacts/cost_calibration_v0_2.json")
    report = sub.add_parser("report")
    report.add_argument("run_dir")
    check = sub.add_parser("verify-log")
    check.add_argument("run_dir")
    args = parser.parse_args(argv)
    if args.command == "generate":
        if Path(args.out).exists():
            raise ValueError(
                "dataset already exists; use a new path instead of overwriting"
            )
        rows = generate(args.seed, args.families_per_domain)
        write_dataset(rows, args.out)
        print(
            json.dumps(
                {
                    "path": args.out,
                    "scenarios": len(rows),
                    "families": len({r.family_id for r in rows}),
                    "status": "synthetic_unreviewed",
                    "sha256": sha256_file(args.out),
                }
            )
        )
        return
    if args.command == "models":
        print(json.dumps(LocalOllama().inventory(), indent=2))
        return
    if args.command in {"report", "verify-log"}:
        rows = verify_log(args.run_dir)
        if args.command == "report":
            manifest = json.loads(
                (Path(args.run_dir) / "manifest.json").read_text(encoding="utf-8")
            )
            print(
                json.dumps(
                    generate_report(args.run_dir, rows, manifest, reanalysis=True),
                    indent=2,
                )
            )
        else:
            print(json.dumps({"verified_records": len(rows)}))
        return
    rows = load_dataset(args.data)
    if args.command == "validate":
        print(
            json.dumps(
                {
                    "records": len(rows),
                    "families": len({r.family_id for r in rows}),
                    "splits": dict(Counter(r.split for r in rows)),
                }
            )
        )
        return
    if args.command == "annotate":
        annotation_export(rows, args.out)
        print(args.out)
        return
    if args.command == "agreement":
        print(
            json.dumps(agreement(args.a, args.b, {r.task_id for r in rows}), indent=2)
        )
        return
    if args.command == "cost-calibrate":
        from .cost_policy import fit_cost_policy

        result = fit_cost_policy(
            [r for r in rows if r.split == "train"],
            [r for r in rows if r.split == "calibration"],
            args.alpha,
            args.minimum_autonomy,
        )
        result["dataset_sha256"] = sha256_file(args.data)
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "path": str(path),
                    "calibration": result["calibration"],
                    "guarantee": result["guarantee"],
                    "status": result["status"],
                }
            )
        )
        return
    if args.command == "calibrate":
        artifact = fit(
            [r for r in rows if r.split == "train"],
            [r for r in rows if r.split == "calibration"],
            args.alpha,
        )
        artifact["dataset_sha256"] = sha256_file(args.data)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "path": str(out),
                    "threshold": artifact["threshold"],
                    "calibration": artifact["calibration"],
                    "guarantee": artifact["guarantee"],
                }
            )
        )
        return
    if args.command == "agent-run":
        from .agent import LocalAgent, evaluate_agents
        from .cost_policy import DEFAULT_COSTS, validate as validate_cost

        if (
            args.limit < 1
            or args.max_calls < 1
            or args.max_steps < 1
            or args.max_seconds <= 0
        ):
            raise ValueError("invalid agent bounds")
        artifact = (
            load_artifact(args.artifact)
            if {"tharun_calibrated", "action_classifier"} & set(args.systems)
            else None
        )
        cost_artifact = (
            json.loads(Path(args.cost_artifact).read_text(encoding="utf-8"))
            if "tharun_cost_calibrated" in args.systems
            else None
        )
        if cost_artifact:
            validate_cost(cost_artifact)
            if cost_artifact.get("dataset_sha256") != sha256_file(args.data):
                raise ValueError("dataset differs from cost-calibration artifact")
        if artifact and artifact.get("dataset_sha256") != sha256_file(args.data):
            raise ValueError("dataset differs from calibration artifact")
        selected = select_balanced(
            [r for r in rows if r.split == args.split], args.limit
        )
        if not selected:
            raise ValueError("no scenarios selected")
        if artifact and (
            {r.family_id for r in selected}
            & (set(artifact["train_families"]) | set(artifact["calibration_families"]))
        ):
            raise ValueError("agent evaluation-family leakage")
        if cost_artifact and (
            {r.family_id for r in selected}
            & (
                set(cost_artifact["train_families"])
                | set(cost_artifact["calibration_families"])
            )
        ):
            raise ValueError("agent cost-policy family leakage")
        judge_factor = 2 if "llm_judge" in args.systems else 1
        if (
            judge_factor * args.max_steps * len(selected) * len(args.systems)
            > args.max_calls
        ):
            raise ValueError("worst-case requested agent calls exceed explicit cap")
        agent = LocalAgent(
            args.model,
            guarded_prompt=args.guarded_prompt,
            timeout=args.timeout,
            max_calls=args.max_calls,
        )
        gates = [
            ModelController(
                args.model, "llm_judge", timeout=args.timeout, max_calls=args.max_calls
            )
            if name == "llm_judge"
            else create_controller(name, artifact, cost_artifact=cost_artifact)
            for name in args.systems
        ]
        manifest = {
            "dataset_sha256": sha256_file(args.data),
            "dataset_path": str(Path(args.data).resolve()),
            "split": args.split,
            "artifact_sha256": sha256_file(args.artifact) if artifact else None,
            "systems": args.systems,
            "config": vars(args),
            "selected_task_ids": [r.task_id for r in selected],
            "model_inventory": [agent.metadata],
            "server_version": agent.version,
            "local_only": True,
            "controller_dependencies": [
                g.dependency for g in gates if hasattr(g, "dependency")
            ],
            "cost_artifact_sha256": sha256_file(args.cost_artifact)
            if cost_artifact
            else None,
            "intervention_costs": cost_artifact["costs"]
            if cost_artifact
            else DEFAULT_COSTS,
        }
        writer = RunWriter(args.out, manifest)
        writer.manifest["experiment_type"] = "synthetic_closed_loop_agent"
        writer._manifest()
        result = evaluate_agents(
            selected,
            agent,
            gates,
            writer,
            args.max_steps,
            args.max_seconds,
            args.recovery_guard,
        )
        if result:
            generate_report(args.out, result, writer.manifest)
        print(
            json.dumps(
                {
                    "run_dir": str(writer.path.resolve()),
                    "status": writer.manifest["status"],
                    "records": len(result),
                    "inference_calls": agent.calls
                    + sum(getattr(g, "calls", 0) for g in gates),
                }
            )
        )
        return
    if (
        args.repeats < 1
        or args.limit < 0
        or args.max_calls < 0
        or args.max_seconds <= 0
    ):
        raise ValueError("invalid run bounds")
    artifact = (
        load_artifact(args.artifact)
        if {"tharun_calibrated", "action_classifier"} & set(args.systems)
        else None
    )
    from .cost_policy import DEFAULT_COSTS, validate as validate_cost

    cost_artifact = (
        json.loads(Path(args.cost_artifact).read_text(encoding="utf-8"))
        if "tharun_cost_calibrated" in args.systems
        else None
    )
    if cost_artifact:
        validate_cost(cost_artifact)
        if cost_artifact.get("dataset_sha256") != sha256_file(args.data):
            raise ValueError("dataset differs from cost-calibration artifact")
    if artifact and artifact.get("dataset_sha256") != sha256_file(args.data):
        raise ValueError("dataset hash differs from fitted artifact")
    selected = select_balanced([r for r in rows if r.split == args.split], args.limit)
    if not selected:
        raise ValueError("no scenarios selected")
    if artifact and args.split in {"test", "transfer"}:
        seen = set(artifact["train_families"]) | set(artifact["calibration_families"])
        if seen & {r.family_id for r in selected}:
            raise ValueError("evaluation-family leakage")
    if cost_artifact and args.split in {"test", "transfer"}:
        if (
            set(cost_artifact["train_families"])
            | set(cost_artifact["calibration_families"])
        ) & {r.family_id for r in selected}:
            raise ValueError("cost-policy evaluation-family leakage")
    controllers = []
    for name in args.systems:
        if name in {"llm_judge", "prompt_guardrail"}:
            controllers.append(
                ModelController(
                    args.model, name, timeout=args.timeout, max_calls=args.max_calls
                )
            )
        else:
            for threshold in (
                args.thresholds
                if args.thresholds and name in {"tharun_fixed", "tharun_calibrated"}
                else [None]
            ):
                if threshold is not None and not -1 <= threshold <= 1:
                    raise ValueError("threshold must be in [-1,1]")
                controllers.append(
                    create_controller(
                        name, artifact, threshold, cost_artifact=cost_artifact
                    )
                )
    # One total call budget across model modes; cached calls do not spend budget.
    model_count = sum(isinstance(c, ModelController) for c in controllers)
    if model_count and len(selected) * args.repeats * model_count > args.max_calls:
        raise ValueError(
            "requested model decisions exceed max-calls; reduce limit/repeats or raise explicit local call cap"
        )
    manifest = {
        "dataset_sha256": sha256_file(args.data),
        "dataset_path": str(Path(args.data).resolve()),
        "split": args.split,
        "artifact_sha256": sha256_file(args.artifact) if artifact else None,
        "selected_task_ids": [r.task_id for r in selected],
        "systems": args.systems,
        "repeats": args.repeats,
        "recovery_mode": args.recovery,
        "thresholds": args.thresholds,
        "model_inventory": [
            c.metadata for c in controllers if isinstance(c, ModelController)
        ],
        "local_only": True,
        "server_version": LocalOllama().request("/api/version")
        if model_count
        else None,
        "exploratory_sweep": bool(args.thresholds),
        "config": vars(args),
        "controller_dependencies": [
            c.dependency for c in controllers if hasattr(c, "dependency")
        ],
        "cost_artifact_sha256": sha256_file(args.cost_artifact)
        if cost_artifact
        else None,
        "intervention_costs": cost_artifact["costs"]
        if cost_artifact
        else DEFAULT_COSTS,
    }
    writer = RunWriter(args.out, manifest)
    result = evaluate(
        selected, controllers, writer, args.repeats, args.recovery, args.max_seconds
    )
    if result:
        generate_report(args.out, result, writer.manifest)
    print(
        json.dumps(
            {
                "run_dir": str(writer.path.resolve()),
                "status": writer.manifest["status"],
                "records": len(result),
                "errors": sum(bool(r["error"]) for r in result),
            }
        )
    )


if __name__ == "__main__":
    main()
