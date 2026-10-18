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
        trade = trade_call(method, params)
        if trade is not None:
            self._json(trade)
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


_TRADE = {"api": None}


def _trade_api():
    if _TRADE["api"] is not None:
        return _TRADE["api"]
    dll_path = os.path.join(ROOT, "thsapi.dll")
    if not os.path.exists(dll_path):
        raise RuntimeError("thsapi.dll not found")
    from ctypes import WinDLL, c_int, c_short, c_float, c_char_p, create_string_buffer
    dll = WinDLL(dll_path)
    dll.Init()
    dll.Logon.argtypes = [c_char_p, c_short, c_char_p, c_short, c_char_p, c_char_p, c_char_p, c_char_p, c_char_p]
    dll.Logon.restype = c_int
    dll.QueryData.argtypes = [c_int, c_int, c_char_p, c_char_p]
    dll.QueryData.restype = c_int
    dll.SendOrder.argtypes = [c_int, c_int, c_int, c_char_p, c_char_p, c_float, c_int, c_char_p, c_char_p]
    dll.CancelOrder.argtypes = [c_int, c_char_p, c_char_p, c_char_p, c_char_p]
    _TRADE["api"] = dll
    _TRADE["buf"] = create_string_buffer
    return dll


def _gbk(text):
    return str(text or "").encode("gbk", errors="replace")


def _text(buf):
    return buf.raw.split(b"\x00", 1)[0].decode("gbk", errors="replace")


def trade_call(method, params):
    """These methods load thsapi.dll. Missing DLL does not affect config or signals."""
    if method not in ("login", "balance", "positions", "orders", "send_order", "cancel_order"):
        return None
    try:
        dll = _trade_api()
    except RuntimeError as exc:
        return {"error": str(exc)}
    buf = _TRADE["buf"]
    if method == "login":
        err = buf(256)
        client_id = dll.Logon(
            _gbk(params.get("ip", "")), int(params.get("port", 8002)),
            _gbk(params.get("config", '{"qs_id":356,"account_type":0}')),
            int(params.get("yyb", 48)),
            _gbk(params.get("account", "")), _gbk(params.get("account", "")),
            _gbk(params.get("password", "")), _gbk(""), err)
        _TRADE["client_id"] = client_id
        if client_id < 0:
            return {"error": _text(err) or "Logon failed"}
        return {"result": {"client_id": client_id}}
    client_id = _TRADE.get("client_id", -1)
    result = buf(1024 * 1024)
    err = buf(256)
    if method == "balance":
        code = dll.QueryData(client_id, 0, result, err)
    elif method == "positions":
        code = dll.QueryData(client_id, 1, result, err)
    elif method == "orders":
        code = dll.QueryData(client_id, 2, result, err)
    elif method == "send_order":
        dll.SendOrder(client_id, int(params.get("category", 0)), int(params.get("price_type", 0)),
                      _gbk(params.get("shareholder", "")), _gbk(params.get("code", "")),
                      float(params.get("price", 0)), int(params.get("amount", 0)), result, err)
        code = 0 if not _text(err).strip() else -1
    elif method == "cancel_order":
        dll.CancelOrder(client_id, _gbk(params.get("exchange_id", "")), _gbk(params.get("order_id", "")), result, err)
        code = 0 if not _text(err).strip() else -1
    else:
        return {"error": "unknown method"}
    if code != 0:
        return {"error": _text(err) or "trade call failed"}
    return {"result": _text(result)}


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
