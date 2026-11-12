"""Reproduce the v0.2 fixed-proposal core pilot without inference/downloads."""

from pathlib import Path
import argparse
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument(
    "--out",
    required=True,
    help="New run directory; existing runs cannot be overwritten",
)
args = parser.parse_args()
destination = Path(args.out)
if not destination.is_absolute():
    destination = root / destination
if (
    destination.exists()
    or destination.with_suffix(".calibration.json").exists()
    or destination.with_suffix(".cost.json").exists()
):
    raise SystemExit("Choose a new output path")
destination.parent.mkdir(parents=True, exist_ok=True)
artifact = str(destination.with_suffix(".calibration.json"))
cost = str(destination.with_suffix(".cost.json"))


def run(*argv):
    subprocess.run([sys.executable, "-m", "scopequay", *argv], cwd=root, check=True)


run("calibrate", "--data", "data/pilot_v0_2.jsonl", "--out", artifact)
run("cost-calibrate", "--data", "data/pilot_v0_2.jsonl", "--out", cost)
run(
    "run",
    "--data",
    "data/pilot_v0_2.jsonl",
    "--artifact",
    artifact,
    "--cost-artifact",
    cost,
    "--out",
    str(destination),
    "--systems",
    "direct",
    "static_policy",
    "tharun_fixed",
    "tharun_calibrated",
    "tharun_cost_calibrated",
    "refuse_all",
)
run("verify-log", str(destination))
