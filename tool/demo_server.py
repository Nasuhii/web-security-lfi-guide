#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LFI-Path-Hunter: Safe Local Demo Server (127.0.0.1:8090)
Demonstrates /vuln (non-recursive ../ strip bug) vs /safe (realpath containment)
inside an isolated temporary directory with sample text files only.
"""

import http.server
import os
import tempfile
import urllib.parse

TMP_DIR = tempfile.TemporaryDirectory()
PUBLIC_DIR = os.path.join(TMP_DIR.name, "public")
os.makedirs(PUBLIC_DIR, exist_ok=True)
with open(os.path.join(PUBLIC_DIR, "home.txt"), "w", encoding="utf-8") as f:
    f.write("Merhaba! Burasi guvenli public/home.txt sayfasi.")
with open(os.path.join(TMP_DIR.name, "secret_canary.txt"), "w", encoding="utf-8") as f:
    f.write("CANARY_SECRET_TOKEN_98765 (public disindaki dosya!)")


class DemoHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        page = qs.get("page", ["home.txt"])[0]

        if parsed.path == "/":
            html = """<!doctype html>
<html><head><meta charset="utf-8"><title>LFI-Path-Hunter Local Lab</title>
<style>body{font-family:system-ui;background:#0f172a;color:#f8fafc;padding:40px;max-width:780px;margin:auto}
a{color:#38bdf8} .card{background:#1e293b;padding:20px;border-radius:12px;margin:16px 0;border:1px solid #334155}</style>
</head><body>
<h1>🛡️ LFI-Path-Hunter Yerel Test Labı (127.0.0.1:8090)</h1>
<div class="card"><h3>🔴 Zafiyetli Uç Nokta (/vuln)</h3>
<p>Normal: <a href="/vuln?page=home.txt">/vuln?page=home.txt</a></p>
<p>Bypass Denemesi: <a href="/vuln?page=....//secret_canary.txt">/vuln?page=....//secret_canary.txt</a></p></div>
<div class="card"><h3>🟢 Yamalı Uç Nokta (/safe — realpath)</h3>
<p>Normal: <a href="/safe?page=home.txt">/safe?page=home.txt</a></p>
<p>Bypass Denemesi (403): <a href="/safe?page=....//secret_canary.txt">/safe?page=....//secret_canary.txt</a></p></div>
</body></html>"""
            self._send(200, html, "text/html; charset=utf-8")
        elif parsed.path == "/vuln":
            cleaned = page.replace("../", "")
            target = os.path.abspath(os.path.join(PUBLIC_DIR, cleaned))
            if os.path.isfile(target) and target.startswith(TMP_DIR.name):
                with open(target, "r", encoding="utf-8", errors="ignore") as f:
                    self._send(200, f.read())
                return
            self._send(404, "Not found")
        elif parsed.path == "/safe":
            base_real = os.path.realpath(PUBLIC_DIR)
            target_real = os.path.realpath(os.path.join(base_real, page))
            if target_real.startswith(base_real + os.sep) and os.path.isfile(target_real):
                with open(target_real, "r", encoding="utf-8", errors="ignore") as f:
                    self._send(200, f.read())
                return
            self._send(403, "403 Forbidden (Path Traversal Blocked by realpath!)")
        else:
            self._send(404, "Not found")

    def _send(self, code: int, text: str, ctype: str = "text/plain; charset=utf-8"):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 8090), DemoHandler)
    print("🚀 LFI-Path-Hunter Demo Lab çalışıyor: http://127.0.0.1:8090/", flush=True)
    server.serve_forever()
