"""Stub of the internal accounts API.

Stands in for accounts.internal on the isolated backend network. It has no
internet access and always reports a plain, non-privileged member, so the
honest console flow can never elevate or export.
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

RESPONSE = json.dumps({
    "role": "member",
    "export_enabled": False,
    "name": "member",
    "vcpu": 0,
    "quota": 0,
    "capacity": 0,
}).encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(RESPONSE)))
        self.end_headers()
        self.wfile.write(RESPONSE)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 80), Handler).serve_forever()
