# coding: utf-8
"""HTTP client for big-QMT strategies. Stdlib only. No files, no environment variables."""

import json
import urllib.parse
import urllib.request


class QmtHttpError(Exception):
    pass


class QmtHttp(object):
    def __init__(self, host, port, token, timeout=30):
        self.base = "http://%s:%s" % (host, int(port))
        self.token = token
        self.timeout = timeout

    def ping(self, timeout=None):
        url = "%s/ping?token=%s" % (self.base, urllib.parse.quote(self.token))
        return self._read(url, None, timeout)

    def call(self, method, params=None, timeout=None):
        url = "%s/tq?token=%s" % (self.base, urllib.parse.quote(self.token))
        body = json.dumps(
            {"method": method, "params": params or {}},
            ensure_ascii=False,
        ).encode("utf-8")
        return self._read(url, body, timeout)

    def _read(self, url, body, timeout):
        headers = {}
        data = None
        if body is not None:
            data = body
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = urllib.request.Request(url, data=data, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=timeout or self.timeout)
            raw = response.read()
        except Exception as exc:
            raise QmtHttpError(str(exc))
        try:
            payload = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            raise QmtHttpError("response is not json")
        if isinstance(payload, dict) and payload.get("error"):
            raise QmtHttpError(payload.get("error"))
        return payload
