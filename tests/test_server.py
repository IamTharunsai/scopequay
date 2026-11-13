import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from scopequay.server import make_server


class LocalServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = make_server(0, Path(self.tmp.name) / "db.sqlite3")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port

    def tearDown(self):
        if self.server.experiments.worker:
            self.server.experiments.worker.join(timeout=30)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def request(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        c.request(method, path, body, headers or {})
        r = c.getresponse()
        value = r.read()
        status, response_headers = r.status, dict(r.getheaders())
        c.close()
        return status, value, response_headers

    def test_local_approval_api_and_static_files(self):
        for path in ["/", "/style.css", "/app.js", "/logo-dark.png", "/logo-light.png"]:
            status, body, headers = self.request("GET", path)
            self.assertEqual(status, 200)
            self.assertTrue(body)
            self.assertIn("frame-ancestors", headers["Content-Security-Policy"])
        _, body, _ = self.request("GET", "/api/state")
        token = json.loads(body)["csrf_token"]
        status, body, _ = self.request(
            "POST",
            "/api/seed",
            "{}",
            {"Content-Type": "application/json", "X-ScopeQuay-Token": token},
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)["requests"]), 8)

    def test_experiment_http_create_poll_and_verified_results(self):
        _, body, _ = self.request("GET", "/api/state")
        token = json.loads(body)["csrf_token"]
        headers = {"Content-Type": "application/json", "X-ScopeQuay-Token": token}
        status, body, _ = self.request(
            "POST",
            "/api/experiments",
            json.dumps({"systems": ["direct"], "limit": 1}),
            headers,
        )
        self.assertEqual(status, 202)
        jid = json.loads(body)["id"]
        self.server.experiments.worker.join(timeout=30)
        status, body, _ = self.request("GET", f"/api/experiments/{jid}/results")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)["outcomes"]), 1)
        self.assertEqual(
            self.request(
                "POST", "/api/experiments", "{}", {"Content-Type": "application/json"}
            )[0],
            403,
        )
        self.assertEqual(
            self.request("POST", "/api/experiments", '{"provider":"openai"}', headers)[
                0
            ],
            400,
        )

    def test_cross_origin_and_missing_token_rejected(self):
        self.assertEqual(
            self.request(
                "POST", "/api/seed", "{}", {"Content-Type": "application/json"}
            )[0],
            403,
        )
        _, body, _ = self.request("GET", "/api/state")
        token = json.loads(body)["csrf_token"]
        self.assertEqual(
            self.request(
                "POST",
                "/api/seed",
                "{}",
                {
                    "Content-Type": "application/json",
                    "X-ScopeQuay-Token": token,
                    "Origin": "https://example.org",
                },
            )[0],
            403,
        )

    def test_host_header_and_path_traversal(self):
        self.assertEqual(
            self.request("GET", "/api/state", headers={"Host": "evil.example"})[0], 403
        )
        self.assertEqual(self.request("GET", "/../README.md")[0], 404)

    def test_invalid_json_and_request_shape(self):
        _, body, _ = self.request("GET", "/api/state")
        token = json.loads(body)["csrf_token"]
        headers = {"Content-Type": "application/json", "X-ScopeQuay-Token": token}
        for data in ["[1]", "{invalid", '{"id":5,"action":null}']:
            self.assertEqual(self.request("POST", "/api/action", data, headers)[0], 400)
