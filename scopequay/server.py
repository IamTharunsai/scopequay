"""Loopback-only demo server; deliberately not a production deployment server."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import urlsplit

from .workflow import Workflow
from .experiments import ExperimentService

WEB = Path(__file__).with_name("web")
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/lab.js": ("lab.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/logo-dark.png": ("logo-dark.png", "image/png"),
    "/logo-light.png": ("logo-light.png", "image/png"),
}


def make_server(port=8765, database="local-data/approvals.sqlite3", dataset=None):
    workflow = Workflow(database)
    experiments = ExperimentService(
        Path(database).parent / "experiments",
        dataset or Path(__file__).resolve().parents[1] / "data/pilot_v0_2.jsonl",
    )
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = "ScopeQuayLocal/0.4-alpha"

        def reply(self, status, body, content_type="application/json; charset=utf-8"):
            raw = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
            self.end_headers()
            self.wfile.write(raw)

        def valid_host(self):
            return self.headers.get("Host") in {
                f"127.0.0.1:{self.server.server_port}",
                f"localhost:{self.server.server_port}",
            }

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, {"error": "Invalid local host"})
            path = urlsplit(self.path).path
            if path in STATIC:
                name, mime = STATIC[path]
                return self.reply(200, (WEB / name).read_bytes(), mime)
            if path == "/api/state":
                return self.reply(200, {**workflow.snapshot(), "csrf_token": token})
            if path == "/api/audit":
                return self.reply(
                    200,
                    {
                        "events": workflow.snapshot()["events"],
                        "verification": workflow.verify_events(),
                    },
                )
            if path == "/api/experiments":
                return self.reply(200, {"experiments": experiments.list()})
            if path == "/api/capabilities":
                from tharun.data import load_dataset

                rows = load_dataset(experiments.dataset)
                return self.reply(
                    200,
                    {
                        "cloud_enabled": False,
                        "agent_limit": 8,
                        "fixed_limit": 152,
                        "domains": sorted({r.domain for r in rows}),
                        "variants": sorted({r.variant for r in rows}),
                        "splits": {
                            s: sum(r.split == s for r in rows)
                            for s in ["train", "calibration", "test", "transfer"]
                        },
                    },
                )
            if path == "/api/evidence":
                path = (
                    Path(__file__).resolve().parents[1] / "evidence/pilot-summary.json"
                )
                if not path.is_file():
                    return self.reply(
                        503,
                        {
                            "error": "Recorded evidence is available in the source checkout"
                        },
                    )
                return self.reply(200, json.loads(path.read_text(encoding="utf-8")))
            if path == "/api/models":
                from tharun.local_models import LocalOllama

                try:
                    return self.reply(
                        200,
                        {
                            "provider": "local_ollama",
                            "inventory": LocalOllama(timeout=3).inventory(),
                            "cloud_enabled": False,
                        },
                    )
                except (OSError, ValueError) as exc:
                    return self.reply(503, {"error": str(exc), "cloud_enabled": False})
            if path.startswith("/api/experiments/"):
                parts = path.split("/")
                try:
                    if len(parts) == 5 and parts[4] == "results":
                        return self.reply(200, experiments.results(parts[3]))
                    if len(parts) == 4:
                        return self.reply(200, experiments.get(parts[3]))
                except ValueError as exc:
                    return self.reply(400, {"error": str(exc)})
            return self.reply(404, {"error": "Not found"})

        def do_POST(self):
            origin = self.headers.get("Origin")
            allowed_origins = {
                f"http://127.0.0.1:{self.server.server_port}",
                f"http://localhost:{self.server.server_port}",
            }
            if (
                not self.valid_host()
                or (origin is not None and origin not in allowed_origins)
                or not secrets.compare_digest(
                    self.headers.get("X-ScopeQuay-Token", ""), token
                )
            ):
                return self.reply(
                    403,
                    {
                        "error": "Open the local dashboard and refresh before making changes"
                    },
                )
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.reply(415, {"error": "JSON request required"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 4096:
                    return self.reply(
                        413, {"error": "Request body must be 1–4096 bytes"}
                    )
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("JSON object required")
                path = urlsplit(self.path).path
                if path == "/api/review":
                    from .policy import assess

                    return self.reply(200, assess(payload))
                if path == "/api/experiments":
                    return self.reply(202, experiments.submit(payload))
                if path == "/api/seed":
                    state = workflow.seed()
                elif path == "/api/action":
                    if not isinstance(payload.get("id"), str) or not isinstance(
                        payload.get("action"), str
                    ):
                        raise ValueError("Request ID and action required")
                    state = workflow.act(
                        payload["id"],
                        payload["action"],
                        payload.get("revision"),
                        payload.get("note", ""),
                    )
                else:
                    return self.reply(404, {"error": "Unknown action endpoint"})
                return self.reply(200, {**state, "csrf_token": token})
            except (ValueError, TypeError, UnicodeDecodeError, OSError) as exc:
                return self.reply(400, {"error": str(exc)})

        def log_message(self, fmt, *args):
            # No request body, review note or credentials are logged to terminal.
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.experiments = experiments
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="ScopeQuay local approval sandbox")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--database", default="local-data/approvals.sqlite3")
    parser.add_argument(
        "--dataset",
        help="Research fixture path, set by the operator rather than an API client",
    )
    args = parser.parse_args(argv)
    with make_server(args.port, args.database, args.dataset) as server:
        print(
            f"ScopeQuay local demo: http://127.0.0.1:{server.server_port}", flush=True
        )
        print(
            "Single-user sandbox. Explicit agent experiments can invoke installed local models. Cloud APIs and real business actions are disabled.",
            flush=True,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
