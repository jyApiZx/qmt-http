# coding: utf-8
"""Small HTTP service. Same POST body as the big-QMT client. Files stay on this machine."""

import json
import os
import secrets
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.json")
SIGNAL_PATH = os.path.join(ROOT, "signal.json")
TOKEN_PATH = os.path.join(ROOT, "token.txt")
LOG_DIR = os.path.join(ROOT, "logs")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_token():
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    token = secrets.token_hex(16)
    with open(TOKEN_PATH, "w", encoding="utf-8") as handle:
        handle.write(token + "\n")
    print("token written to token.txt:", token)
    return token


TOKEN = ""


def same_token(got):
    if len(got) != len(TOKEN):
        return False
    diff = 0
    for left, right in zip(got, TOKEN):
        diff |= ord(left) ^ ord(right)
    return diff == 0


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/ping":
            self._json({"error": "unknown path"})
            return
        if not same_token(parse_qs(parsed.query).get("token", [""])[0]):
            self._json({"error": "token error"})
            return
        self._json({"ok": True, "service": "qmt_http"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/tq":
            self._json({"error": "unknown path"})
            return
        if not same_token(parse_qs(parsed.query).get("token", [""])[0]):
            self._json({"error": "token error"})
            return
        size = int(self.headers.get("Content-Length", "0") or 0)
        try:
            body = json.loads(self.rfile.read(size).decode("utf-8", "replace") or "{}")
        except ValueError:
            self._json({"error": "body is not json"})
            return
        method = body.get("method")
        params = body.get("params") or {}
        if method == "get_config":
            self._json({"result": load_json(CONFIG_PATH, {
                "account": "YOUR_ACCOUNT",
                "stock_list": ["000001.SZ"],
                "params": {},
            })})
            return
        if method == "get_signal":
            self._json({"result": load_json(SIGNAL_PATH, {
                "date": "",
                "orders": [],
            })})
            return
        if method == "put_log":
            os.makedirs(LOG_DIR, exist_ok=True)
            path = os.path.join(LOG_DIR, datetime.now().strftime("%Y%m%d") + ".log")
            line = params.get("text") or json.dumps(params, ensure_ascii=False)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(datetime.now().strftime("%H:%M:%S ") + line + "\n")
            self._json({"result": {"ok": True}})
            return
        self._json({"error": "unknown method"})

    def _json(self, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


def main():
    global TOKEN
    TOKEN = load_token()
    host = "0.0.0.0"
    port = 17710
    httpd = ThreadingHTTPServer((host, port), Handler)
    print("listening on %s:%s" % (host, port))
    httpd.serve_forever()


if __name__ == "__main__":
    main()
