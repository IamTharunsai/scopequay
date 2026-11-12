"""Manage this project's GitHub repo using the existing Git credential helper.

Never prints/stores credentials or places tokens in URLs. Publishing is explicit.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["create", "pages", "status"])
args = parser.parse_args()
owner, repo = "IamTharunsai", "scopequay"
env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
result = subprocess.run(
    ["git", "credential", "fill"],
    input="protocol=https\nhost=github.com\n\n",
    text=True,
    capture_output=True,
    env=env,
    timeout=20,
)
if result.returncode:
    raise SystemExit(
        "Existing GitHub credentials unavailable. Sign in with Git first; never paste a token into chat."
    )
credentials = dict(
    line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
)
token = credentials.get("password")
if not token:
    raise SystemExit("No GitHub credential returned")


def request(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "User-Agent": "ScopeQuay-project-setup",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = r.read()
            return r.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as e:
        return e.code, {"error": "GitHub returned HTTP " + str(e.code)}


status, user = request("/user")
if status != 200 or user.get("login", "").lower() != owner.lower():
    raise SystemExit(
        "Authenticated Git account does not match the selected project owner"
    )
base = f"/repos/{owner}/{repo}"
if args.action == "create":
    status, existing = request(base)
    if status == 200:
        raise SystemExit(
            "Repository already exists; refusing to replace existing content"
        )
    if status != 404:
        raise SystemExit("Unable to verify repository availability: " + str(status))
    status, payload = request(
        "/user/repos",
        "POST",
        {
            "name": repo,
            "description": "Local action-approval sandbox and reproducible research on risk-calibrated selective autonomy for tool-using LLM agents.",
            "private": False,
            "auto_init": False,
            "has_issues": True,
        },
    )
    if status != 201:
        raise SystemExit("Repository creation failed: " + str(status))
    print(
        json.dumps(
            {"created": True, "url": payload["html_url"], "private": payload["private"]}
        )
    )
elif args.action == "pages":
    status, payload = request(base + "/pages")
    if status == 404:
        status, payload = request(
            base + "/pages", "POST", {"source": {"branch": "main", "path": "/docs"}}
        )
    if status not in {200, 201}:
        raise SystemExit("Pages configuration unavailable: " + str(status))
    print(
        json.dumps(
            {
                "pages_url": payload.get("html_url"),
                "status": payload.get("status"),
                "source": payload.get("source"),
            }
        )
    )
else:
    repo_status, r = request(base)
    pages_status, p = request(base + "/pages")
    workflows_status, w = request(base + "/actions/runs?per_page=3")
    result = {
        "repository": {
            "status": repo_status,
            "url": r.get("html_url"),
            "private": r.get("private"),
            "default_branch": r.get("default_branch"),
        },
        "pages": {
            "http_status": pages_status,
            "url": p.get("html_url"),
            "status": p.get("status"),
        },
        "workflows": [
            {
                k: x.get(k)
                for k in ["name", "status", "conclusion", "html_url", "head_sha"]
            }
            for x in w.get("workflow_runs", [])
        ]
        if workflows_status == 200
        else [],
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/github_status_2026_11_12.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
