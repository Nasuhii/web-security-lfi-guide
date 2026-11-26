#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local self-test for LFI-Path-Hunter:
Spins up a temporary localhost HTTP server with:
  - /vuln?page=...   (simulated non-recursive ../ strip flaw)
  - /safe?page=...   (properly canonicalized os.path.realpath containment)
and verifies that LFI-Path-Hunter detects /vuln and passes /safe with 0 findings.
"""

import http.server
import os
import tempfile
import threading
import urllib.parse

from lfi_hunter import audit_url, write_markdown_report


class MockHandler(http.server.BaseHTTPRequestHandler):
    base_dir = ""
    canary_file = ""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        page = qs.get("page", ["home"])[0]

        if parsed.path == "/vuln":
            # Simulated bug: non-recursive strip of "../"
            cleaned = page.replace("../", "")
            target = os.path.abspath(os.path.join(self.base_dir, cleaned))
            if os.path.isfile(target):
                with open(target, "r", encoding="utf-8", errors="ignore") as f:
                    self._send(200, f.read())
                return
            self._send(404, "Not found")
        elif parsed.path == "/safe":
            # Proper hardening: canonicalize first, then enforce containment
            base_real = os.path.realpath(self.base_dir)
            target_real = os.path.realpath(os.path.join(base_real, page))
            if target_real.startswith(base_real + os.sep) and os.path.isfile(target_real):
                with open(target_real, "r", encoding="utf-8", errors="ignore") as f:
                    self._send(200, f.read())
                return
            self._send(403, "Forbidden")
        else:
            self._send(200, "OK")

    def _send(self, code: int, text: str):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        safe_dir = os.path.join(tmp, "public")
        os.makedirs(safe_dir)
        with open(os.path.join(safe_dir, "home"), "w") as f:
            f.write("Welcome Home")
        canary = os.path.join(tmp, "secret_canary.txt")
        with open(canary, "w") as f:
            f.write("CANARY_SECRET_TOKEN_98765")

        MockHandler.base_dir = safe_dir
        MockHandler.canary_file = canary
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), MockHandler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        try:
            wl_path = os.path.join(tmp, "custom_wl.txt")
            with open(wl_path, "w") as f:
                f.write("# custom wordlist\n../../../../etc/shadow\n....//secret_canary.txt\n")

            vuln_findings = audit_url(
                f"http://127.0.0.1:{port}/vuln?page=home",
                delay=0.0,
                wordlist_path=wl_path,
                match_regex="CANARY_SECRET_TOKEN_98765",
            )
            safe_findings = audit_url(
                f"http://127.0.0.1:{port}/safe?page=home",
                delay=0.0,
                wordlist_path=wl_path,
                match_regex="CANARY_SECRET_TOKEN_98765",
            )
            assert len(vuln_findings) == 1, f"Expected 1 finding on /vuln, got {len(vuln_findings)}"
            assert len(safe_findings) == 0, f"Expected 0 findings on /safe, got {len(safe_findings)}"

            report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_audit_report.md")
            write_markdown_report(f"http://127.0.0.1:{port}/vuln?page=home", vuln_findings, report_path)
            print(f"✅ All local tests passed! Vulnerable findings={len(vuln_findings)}, Patched findings={len(safe_findings)}")
            print(f"📄 Sample report generated: {report_path}")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
