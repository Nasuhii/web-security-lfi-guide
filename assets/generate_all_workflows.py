import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))


def draw_step(ax, x, y, w, h, step_no, title, detail, fill="#F8FAFC", border="#1E293B", badge="#0F172A"):
    box = patches.FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.06,rounding_size=0.14",
        linewidth=1.5,
        edgecolor=border,
        facecolor=fill,
    )
    ax.add_patch(box)

    b = patches.FancyBboxPatch(
        (x + 0.14, y + h - 0.42),
        1.15,
        0.30,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=0,
        facecolor=badge,
    )
    ax.add_patch(b)
    ax.text(
        x + 0.715,
        y + h - 0.27,
        step_no,
        ha="center",
        va="center",
        fontsize=8.2,
        fontweight="bold",
        color="white",
        family="DejaVu Sans",
    )

    ax.text(
        x + 0.16,
        y + h - 0.68,
        title,
        ha="left",
        va="top",
        fontsize=9.5,
        fontweight="bold",
        color="#0F172A",
        family="DejaVu Sans",
    )
    ax.text(
        x + 0.16,
        y + h - 1.02,
        detail,
        ha="left",
        va="top",
        fontsize=8.0,
        color="#334155",
        family="DejaVu Sans",
        linespacing=1.35,
    )


def arrow(ax, x1, y1, x2, y2):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>,head_width=0.25,head_length=0.4", color="#334155", lw=1.6),
    )


def render_6step_chart(filename, main_title, subtitle, steps, footer_text):
    fig, ax = plt.subplots(figsize=(13.5, 7.6), dpi=200)
    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 7.6)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(
        6.75, 7.22, main_title,
        ha="center", va="center", fontsize=14.5, fontweight="bold",
        color="#0F172A", family="DejaVu Sans",
    )
    ax.text(
        6.75, 6.86, subtitle,
        ha="center", va="center", fontsize=9.5, color="#475569", family="DejaVu Sans",
    )

    w, h = 3.7, 1.85
    y1, y2 = 4.55, 1.85
    xs = [0.45, 4.9, 9.35]

    for i in range(3):
        s = steps[i]
        draw_step(ax, xs[i], y1, w, h, f"ADIM {i+1}", s["title"], s["detail"], s["fill"], s["border"], s["badge"])
    arrow(ax, 4.22, y1 + h / 2, 4.83, y1 + h / 2)
    arrow(ax, 8.67, y1 + h / 2, 9.28, y1 + h / 2)

    ax.plot([11.2, 11.2, 2.3, 2.3], [4.48, 4.10, 4.10, 3.82], color="#334155", lw=1.6)
    ax.annotate(
        "", xy=(2.3, 3.76), xytext=(2.3, 3.90),
        arrowprops=dict(arrowstyle="-|>,head_width=0.25,head_length=0.4", color="#334155", lw=1.6),
    )

    for i in range(3):
        s = steps[i + 3]
        draw_step(ax, xs[i], y2, w, h, f"ADIM {i+4}", s["title"], s["detail"], s["fill"], s["border"], s["badge"])
    arrow(ax, 4.22, y2 + h / 2, 4.83, y2 + h / 2)
    arrow(ax, 8.67, y2 + h / 2, 9.28, y2 + h / 2)

    footer = patches.FancyBboxPatch(
        (0.45, 0.35), 12.6, 0.95,
        boxstyle="round,pad=0.05,rounding_size=0.10",
        linewidth=1.0, edgecolor="#CBD5E1", facecolor="#F8FAFC",
    )
    ax.add_patch(footer)
    ax.text(
        6.75, 0.82, footer_text,
        ha="center", va="center", fontsize=8.5, color="#1E293B",
        family="DejaVu Sans", linespacing=1.45,
    )

    out_path = os.path.join(ASSETS_DIR, filename)
    plt.tight_layout(pad=0.2)
    fig.savefig(out_path, dpi=200, facecolor="white")
    plt.close(fig)
    print("Saved:", out_path)


def main():
    BLUE = ("#EFF6FF", "#1D4ED8", "#1D4ED8")
    AMBER = ("#FEF3C7", "#B45309", "#B45309")
    GREEN = ("#ECFDF5", "#047857", "#047857")
    RED = ("#FEF2F2", "#B91C1C", "#B91C1C")
    SLATE = ("#F1F5F9", "#334155", "#334155")

    # 1. SQLi
    render_6step_chart(
        "sqli_hunting_workflow.png",
        "SQL Injection & SQLMap — Adım Adım Arama ve Sömürü Akış Şeması",
        "Giriş Noktası -> String vs Sayısal Test -> Manuel Payload -> SQLMap (-r / -p) -> Veri / Shell -> Savunma",
        [
            {"title": "Giriş Noktası & İstek Yakala", "detail": "• GET (?id=, ?cat=), POST form, Cookie\n• Burp Suite'te isteği req.txt yap\n• Sayısal mı (?id=10) Metin mi (?q=abc)?", "fill": BLUE[0], "border": BLUE[1], "badge": BLUE[2]},
            {"title": "Manuel Hata & Mantık Testi", "detail": "• String: ' veya ';-- gönder\n• Sayısal: 10 OR 1=1 -- - (tırnak yok!)\n• SQL hatası / satır sayısı farkı var mı?", "fill": BLUE[0], "border": BLUE[1], "badge": BLUE[2]},
            {"title": "Blind / Time-Based & UNION", "detail": "• SLEEP(2) ile gecikme ölç (n × t)\n• ORDER BY N ile sütun sayısı bul\n• UNION SELECT table_name FROM ...", "fill": AMBER[0], "border": AMBER[1], "badge": AMBER[2]},
            {"title": "SQLMap ile Hedefli Tarama", "detail": "• POST için: sqlmap -r req.txt -p param\n• DB listele: --dbs\n• Tablo/Veri: -D db -T tbl --dump", "fill": GREEN[0], "border": GREEN[1], "badge": GREEN[2]},
            {"title": "Foothold & Sistem Erişimi", "detail": "• Hash'leri kır / admin girişi yap\n• Dosya oku: --file-read=\"/etc/passwd\"\n• RCE dene: --os-shell", "fill": RED[0], "border": RED[1], "badge": RED[2]},
            {"title": "Güvenli Kodlama (Remediation)", "detail": "• String birleştirme (f-string) YASAK\n• Prepared Statements / PDO kullan\n• Sayısal input için intval() / int()", "fill": SLATE[0], "border": SLATE[1], "badge": SLATE[2]},
        ],
        "Altın Kural: SQLMap'i tüm header'lara körü körüne salmak yerine -r req.txt ve -p <parametre> ile kilitle!\nTime-Based testlerde sunucuyu kilitlememek için SLEEP(1) veya SLEEP(2) kullan.",
    )

    # 2. XSS
    render_6step_chart(
        "xss_hunting_workflow.png",
        "XSS (Reflected / Stored / DOM) — Adım Adım Arama ve Sömürü Akış Şeması",
        "PortSwigger 6 Adımlı Metodoloji: Giriş Noktası -> Canary -> Context -> Payload -> CSP/Filtre Bypass -> Doğrulama",
        [
            {"title": "Tüm Giriş Noktalarını Tara", "detail": "• GET/POST parametreleri (?q=, ?msg=)\n• URL path (/profile/val) & JSON body\n• User-Agent, Referer, Cookie", "fill": BLUE[0], "border": BLUE[1], "badge": BLUE[2]},
            {"title": "Benzersiz Canary Gönder", "detail": "• Kısa alfa-nümerik değer: xss83k9a\n• Yanıt HTML'inde nereye yansıyor?\n• DOM XSS için JS Source->Sink ara", "fill": BLUE[0], "border": BLUE[1], "badge": BLUE[2]},
            {"title": "Yansıma Bağlamını (Context) Çöz", "detail": "• HTML içi: <p>xss83k9a</p>\n• Attribute içi: <input value=\"xss83k9a\">\n• JS string içi: var x = \"xss83k9a\";", "fill": AMBER[0], "border": AMBER[1], "badge": AMBER[2]},
            {"title": "Aday Payload & Intruder Fuzz", "detail": "• Bağlama göre: <script>, \"><img onerror=...>\n• Burp Intruder ile açık tag/event tara\n• DOM: innerHTML, eval(), location.href", "fill": GREEN[0], "border": GREEN[1], "badge": GREEN[2]},
            {"title": "WAF / CSP Bypass & Etki", "detail": "• CSP header oku (script-src, CDN)\n• JSONP / Angular / Dangling Markup\n• Tarayıcıda alert(document.domain) doğrula", "fill": RED[0], "border": RED[1], "badge": RED[2]},
            {"title": "Güvenli Kodlama (Remediation)", "detail": "• Context-aware Output Encoding\n• innerHTML yerine textContent kullan\n• Sıkı CSP + HttpOnly Session Cookie", "fill": SLATE[0], "border": SLATE[1], "badge": SLATE[2]},
        ],
        "Altın Kural: Sadece <script>alert(1)</script> deneyip bırakma; önce xss83k9a ile bağlamı (HTML / Attribute / JS) gör!\nDOM XSS için tarayıcıda Burp DOM Invader ile Source -> Sink akışını takip et.",
    )

    # 3. Session Management
    render_6step_chart(
        "session_hunting_workflow.png",
        "Session Management & Auth — Adım Adım Test Akış Şeması",
        "Oturum Türü -> Cookie Bayrakları -> Token/JWT Kontrolü -> Session Fixation -> Timeout -> Savunma",
        [
            {"title": "Oturum Mekanizmasını Belirle", "detail": "• Set-Cookie (Stateful) mı yoksa\n• Authorization: Bearer JWT (Stateless) mı?\n• Login öncesi cookie veriliyor mu?", "fill": BLUE[0], "border": BLUE[1], "badge": BLUE[2]},
            {"title": "Cookie Güvenlik Bayrakları", "detail": "• HttpOnly var mı? (XSS çalmayı önler)\n• Secure var mı? (Sadece HTTPS)\n• SameSite=Strict/Lax var mı? (CSRF)", "fill": BLUE[0], "border": BLUE[1], "badge": BLUE[2]},
            {"title": "Tahmin & JWT İmza Analizi", "detail": "• Session ID Base64/sıralı sayı mı?\n• JWT alg:none veya zayıf secret?\n• Payload manipüle edilince kabul ediyor mu?", "fill": AMBER[0], "border": AMBER[1], "badge": AMBER[2]},
            {"title": "Session Fixation Testi", "detail": "• Login öncesi verilen PHPSESSID'i kaydet\n• Giriş yaptıktan sonra ID değişti mi?\n• Değişmediyse Session Fixation ZAFİYETİ!", "fill": GREEN[0], "border": GREEN[1], "badge": GREEN[2]},
            {"title": "Logout & Yetki (IDOR) Kontrolü", "detail": "• Logout sonrası eski cookie/JWT hâlâ\n  sunucuda çalışıyor mu (Replay)?\n• Başka kullanıcının yetkisine erişim var mı?", "fill": RED[0], "border": RED[1], "badge": RED[2]},
            {"title": "Güvenli Kodlama (Remediation)", "detail": "• Login'de session_regenerate_id(true)\n• Logout'ta sunucu tarafında iptal et\n• HttpOnly+Secure+SameSite & Idle Timeout", "fill": SLATE[0], "border": SLATE[1], "badge": SLATE[2]},
        ],
        "Altın Kural: Authentication (Kimsin?) ve Authorisation (Yetkin var mı?) ayrı kontrollerdir.\nLogout butonuna basınca sadece tarayıcıdan çerez silmek yetmez; sunucuda da oturum öldürülmelidir.",
    )

    # 4. Network (Wireshark + Metasploit)
    render_6step_chart(
        "network_pentest_workflow.png",
        "Network Analizi (Wireshark) & Metasploit — Adım Adım Akış Şeması",
        "PCAP İnceleme (Wireshark / tshark) -> Exfiltration Çözümü | db_nmap -> search -> hosts -R -> Exploit",
        [
            {"title": "PCAP: Genel Bakış (Wireshark)", "detail": "• Statistics -> Protocol Hierarchy\n• Red Herring (sahte /flag) tuzaklarını ele\n• Display Filter: dns, http, tcp.stream eq X", "fill": BLUE[0], "border": BLUE[1], "badge": BLUE[2]},
            {"title": "PCAP: Stream & Exfiltration", "detail": "• Follow -> TCP Stream (ROT13 / metin)\n• DNS Exfiltration: dns && ip.dst == IP\n• Subdomain parçalarını Base64 decode et", "fill": BLUE[0], "border": BLUE[1], "badge": BLUE[2]},
            {"title": "CLI Otomasyon (tshark)", "detail": "• tshark -r file.pcapng -Y \"...\" -T fields\n• -e dns.qry.name | cut -d '.' -f 1\n• tr -d '\\n' | base64 -d", "fill": AMBER[0], "border": AMBER[1], "badge": AMBER[2]},
            {"title": "MSF: Keşif & DB Kaydı", "detail": "• workspace -a <proje_adi>\n• db_nmap -sV -sC <HEDEF_IP>\n• hosts ve services -S <servis> ile bak", "fill": GREEN[0], "border": GREEN[1], "badge": GREEN[2]},
            {"title": "MSF: Tarama & Sömürü", "detail": "• search type:auxiliary <servis/CVE>\n• hosts -R veya services -p 445 -R\n• Exploit öncesi check komutu ile doğrula", "fill": RED[0], "border": RED[1], "badge": RED[2]},
            {"title": "Post-Exploitation & Rapor", "detail": "• Meterpreter / Shell oturumu al\n• Hash dump, yetki & kanıt topla\n• vulns çıktısıyla kapatma önerisi yaz", "fill": SLATE[0], "border": SLATE[1], "badge": SLATE[2]},
        ],
        "Operasyon Döngüsü: Wireshark'ta önce katman/protokol süz, sonra tshark ile otomatikleştir.\nMetasploit'te altın döngü: Scan (db_nmap) -> Store (workspace) -> Identify (auxiliary) -> Exploit (hosts -R).",
    )


if __name__ == "__main__":
    main()
