"""Opt-in live smoke tests for BioMCP clinical-trial access.

These tests speak MCP over stdio using only the Python standard library. They
are skipped during normal test runs because they require a BioMCP executable
and live access to public upstream services.
"""

import json
import os
import re
import selectors
import shutil
import subprocess
import tempfile
import unittest


RUN_LIVE = os.environ.get("RUN_BIOMCP_LIVE") == "1"


class BioMCPStdioClient:
    """Minimal JSON-RPC client used only to verify the BioMCP connection."""

    def __init__(self, executable):
        self._cache_dir = tempfile.TemporaryDirectory(prefix="oncomatchmaker-biomcp-")
        environment = os.environ.copy()
        environment["BIOMCP_CACHE_DIR"] = self._cache_dir.name
        self._process = subprocess.Popen(
            [executable, "serve"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=environment,
        )
        self._selector = selectors.DefaultSelector()
        self._selector.register(self._process.stdout, selectors.EVENT_READ)
        self._next_id = 1

    def close(self):
        try:
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=5)
        finally:
            self._selector.close()
            self._process.stdin.close()
            self._process.stdout.close()
            self._process.stderr.close()
            self._cache_dir.cleanup()

    def _send(self, message):
        self._process.stdin.write(json.dumps(message) + "\n")
        self._process.stdin.flush()

    def _receive(self, expected_id, timeout=30):
        while True:
            events = self._selector.select(timeout)
            if not events:
                raise TimeoutError("Timed out waiting for BioMCP")
            line = self._process.stdout.readline()
            if not line:
                error = self._process.stderr.read()
                raise RuntimeError("BioMCP stopped unexpectedly: {}".format(error))
            message = json.loads(line)
            if message.get("id") == expected_id:
                return message

    def request(self, method, params):
        request_id = self._next_id
        self._next_id += 1
        self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
        response = self._receive(request_id)
        if "error" in response:
            raise RuntimeError("BioMCP error: {}".format(response["error"]))
        return response["result"]

    def initialize(self):
        result = self.request(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "oncomatchmaker-connectivity-test",
                    "version": "0.1.0",
                },
            },
        )
        self._send(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
        )
        return result

    def call_tool(self, name, arguments):
        result = self.request(
            "tools/call", {"name": name, "arguments": arguments}
        )
        if result.get("isError"):
            raise RuntimeError("BioMCP tool returned an error: {}".format(result))
        text_items = [
            item["text"]
            for item in result.get("content", [])
            if item.get("type") == "text"
        ]
        if not text_items:
            raise RuntimeError("BioMCP returned no text content")
        return json.loads(text_items[0])


@unittest.skipUnless(RUN_LIVE, "set RUN_BIOMCP_LIVE=1 to run live BioMCP tests")
class BioMCPConnectivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.environ.get("BIOMCP_BIN", "biomcp")
        cls.executable = (
            configured
            if os.path.isabs(configured)
            else shutil.which(configured)
        )
        if not cls.executable or not os.path.isfile(cls.executable):
            raise unittest.SkipTest("BioMCP executable was not found")

    def setUp(self):
        self.client = BioMCPStdioClient(self.executable)
        self.initialize_result = self.client.initialize()

    def tearDown(self):
        self.client.close()

    def test_mcp_handshake_and_tool_surface(self):
        self.assertEqual(self.initialize_result["serverInfo"]["name"], "biomcp")
        self.assertRegex(
            self.initialize_result["serverInfo"]["version"], r"^\d+\.\d+\.\d+"
        )
        tools = self.client.request("tools/list", {}).get("tools", [])
        self.assertTrue({"biomcp", "search", "get"}.issubset({t["name"] for t in tools}))

    def test_recruiting_nsclc_kras_g12c_search(self):
        payload = self.client.call_tool(
            "biomcp",
            {
                "command": (
                    'search trial -c "non-small cell lung cancer" '
                    '--mutation "KRAS G12C" --status recruiting '
                    "--source ctgov --limit 5"
                ),
                "json": True,
            },
        )
        self.assertGreater(payload["count"], 0)
        self.assertLessEqual(payload["count"], 5)
        for trial in payload["results"]:
            self.assertRegex(trial["nct_id"], r"^NCT\d{8}$")
            self.assertEqual(trial["status"], "RECRUITING")
            self.assertTrue(trial["title"])

    def test_trial_detail_includes_provenance_and_matching_inputs(self):
        trial = self.client.call_tool(
            "get",
            {
                "entity": "trial",
                "id": "NCT05920356",
                "sections": ["contacts", "eligibility", "locations"],
                "json": True,
            },
        )
        self.assertEqual(trial["nct_id"], "NCT05920356")
        self.assertTrue(trial["eligibility_text"])
        self.assertTrue(trial["locations"])
        evidence_urls = trial["_meta"]["evidence_urls"]
        self.assertTrue(
            any(item["url"].startswith("https://clinicaltrials.gov/") for item in evidence_urls)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
