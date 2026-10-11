#coding:gbk
# Big-QMT strategy. Do not read or write config, signal, or log files.
# Paste TOKEN below. This process cannot see setx environment variables.

HOST = "YOUR_HTTP_HOST"
PORT = 17710
TOKEN = "YOUR_TOKEN"

http = None
config = None


def init(ContextInfo):
    global http, config
    from qmt_http import QmtHttp
    http = QmtHttp(HOST, PORT, TOKEN)
    http.ping()
    config = http.call("get_config", {}).get("result") or {}


def handlebar(ContextInfo):
    signal = http.call("get_signal", {}).get("result") or {}
    orders = signal.get("orders") or []
    http.call("put_log", {"text": "orders %s" % len(orders)})
    for order in orders:
        code = order.get("code")
        side = order.get("side")
        volume = int(order.get("volume") or 0)
        if not code or volume <= 0:
            continue
        # 23 buy, 24 sell. Fill price and account from config on the HTTP server.
        op = 23 if side == "buy" else 24
        account = config.get("account") or ""
        if account and account != "YOUR_ACCOUNT":
            passorder(op, 1101, account, code, 5, -1, volume, "qmt-http", 2, side, ContextInfo)
