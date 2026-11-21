#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Run with: python3 -m unittest discover -s server/tests -t server
# build-images.sh runs them inside the built image.

import http.client
import json
import logging
import threading
import unittest

from dnsapi_server.app import make_server


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)
        cls.server = make_server("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        logging.disable(logging.NOTSET)

    def request(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, path, body=body)
            resp = conn.getresponse()
            raw = resp.read()
            return resp, (json.loads(raw) if raw else None)
        finally:
            conn.close()

    def test_status(self):
        resp, body = self.request("GET", "/v1/status")
        self.assertEqual(resp.status, 200)
        self.assertEqual(body, {"status": "ok"})
        self.assertEqual(resp.getheader("Content-Type"), "application/json")
        self.assertEqual(resp.getheader("Server"), "dnsapi")

    def test_status_query_string(self):
        resp, body = self.request("GET", "/v1/status?x=1")
        self.assertEqual(resp.status, 200)

    def test_head(self):
        resp, body = self.request("HEAD", "/v1/status")
        self.assertEqual(resp.status, 200)
        self.assertIsNone(body)

    def test_unknown_path(self):
        resp, body = self.request("GET", "/v1/nothing")
        self.assertEqual(resp.status, 404)
        self.assertEqual(body["error"]["code"], "not_found")
        self.assertIn("field", body["error"])

    def test_wrong_method(self):
        resp, body = self.request("POST", "/v1/status", body=b"{}")
        self.assertEqual(resp.status, 405)
        self.assertEqual(body["error"]["code"], "method_not_allowed")
        self.assertEqual(resp.getheader("Allow"), "GET, HEAD")


if __name__ == "__main__":
    unittest.main()
