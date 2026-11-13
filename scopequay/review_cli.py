import argparse
import json
from pathlib import Path
import shutil
from .policy import assess


def review(argv=None):
    parser = argparse.ArgumentParser(
        description="Review action facts locally; execute no tool"
    )
    parser.add_argument("--input", required=True)
    args = parser.parse_args(argv)
    data = Path(args.input).read_bytes()
    if len(data) > 64_000:
        raise ValueError("Action context exceeds 64 KB")
    print(json.dumps(assess(json.loads(data)), indent=2))


def install_skill(argv=None):
    parser = argparse.ArgumentParser(
        description="Copy the ScopeQuay review skill to an explicit destination"
    )
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    destination = Path(args.target).resolve()
    if destination.exists():
        raise ValueError("Destination exists; choose a new skill folder")
    source = Path(__file__).with_name("skill")
    shutil.copytree(source, destination)
    print(
        json.dumps(
            {
                "installed_to": str(destination),
                "enforcement": False,
                "tools_executed": False,
            }
        )
    )
