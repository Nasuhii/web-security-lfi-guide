# 🛡️ LFI-Path-Hunter Audit Report
- **Target URL:** `http://127.0.0.1:39723/vuln?page=home`
- **Findings Count:** `1`

| Parameter | Technique | Probe | Status | Evidence |
| :--- | :--- | :--- | :---: | :--- |
| `page` | Wordlist (custom_wl.txt) | `....//secret_canary.txt` | 200 | `CANARY_SECRET_TOKEN_98765` |

## 🔧 Recommended Hardening
1. Map numeric IDs to fixed server-side paths instead of accepting filenames.
2. Canonicalize paths (`realpath()` / `filepath.EvalSymlinks`) **before** checking base directory prefix.
3. Set `allow_url_include = Off` and restrict `open_basedir` in PHP.
