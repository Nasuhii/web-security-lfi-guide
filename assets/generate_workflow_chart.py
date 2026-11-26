import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lfi_hunting_workflow.png")


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

    # Step badge
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


def main():
    fig, ax = plt.subplots(figsize=(13.5, 7.6), dpi=200)
    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 7.6)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # Title
    ax.text(
        6.75,
        7.22,
        "LFI & Path Traversal — Adım Adım Arama ve Sömürü Akış Şeması",
        ha="center",
        va="center",
        fontsize=14.5,
        fontweight="bold",
        color="#0F172A",
        family="DejaVu Sans",
    )
    ax.text(
        6.75,
        6.86,
        "Keşif -> Parmak İzi -> Filtre Bypass -> Wrapper/Okuma -> RCE Yükseltme -> Savunma Doğrulama",
        ha="center",
        va="center",
        fontsize=9.5,
        color="#475569",
        family="DejaVu Sans",
    )

    # Row 1 (Left to Right: Steps 1 -> 2 -> 3)
    w, h = 3.7, 1.85
    y1 = 4.55
    draw_step(
        ax, 0.45, y1, w, h,
        "ADIM 1",
        "Giriş Noktası & Parametre Keşfi",
        "• GET/POST: ?page=, ?file=, ?path=, ?doc=\n• Cookie & Header: lang=, theme=, User-Agent\n• Exposed .git/HEAD var mı? (git-dumper)\n• Araç: python3 tool/lfi_hunter.py --url ...",
        fill="#EFF6FF", border="#1D4ED8", badge="#1D4ED8"
    )
    draw_step(
        ax, 4.9, y1, w, h,
        "ADIM 2",
        "Hata & Parmak İzi Analizi",
        "• Var olmayan değer at: ?page=test_123\n• Prefix var mı? (languages/)\n• Suffix var mı? (.php)\n• Webroot derinliği ve OS (/ vs \\) nedir?",
        fill="#EFF6FF", border="#1D4ED8", badge="#1D4ED8"
    )
    draw_step(
        ax, 9.35, y1, w, h,
        "ADIM 3",
        "Raw Path & Filtre Bypass",
        "• Daima: curl --path-as-is kullan\n• Strip bypass: ....//....// ve ..././\n• Encode: %2e%2e%2f / Double: %252f\n• Prefix varsa: languages/../../../../",
        fill="#FEF3C7", border="#B45309", badge="#B45309"
    )

    arrow(ax, 4.22, y1 + h / 2, 4.83, y1 + h / 2)
    arrow(ax, 8.67, y1 + h / 2, 9.28, y1 + h / 2)

    # Connector Row 1 -> Row 2 (Step 3 down to Step 4)
    # Draw clean orthogonal connector from Step 3 bottom to Step 4 top
    ax.plot([11.2, 11.2, 2.3, 2.3], [4.48, 4.10, 4.10, 3.82], color="#334155", lw=1.6)
    ax.annotate(
        "",
        xy=(2.3, 3.76),
        xytext=(2.3, 3.90),
        arrowprops=dict(arrowstyle="-|>,head_width=0.25,head_length=0.4", color="#334155", lw=1.6),
    )

    # Row 2 (Left to Right: Steps 4 -> 5 -> 6)
    y2 = 1.85
    draw_step(
        ax, 0.45, y2, w, h,
        "ADIM 4",
        "Wrapper & Kaynak Kod Okuma",
        "• php://filter/convert.base64-encode/resource=\n• Kritik hedefler: .env, config.php, id_rsa\n• /proc/self/environ (--ignore-content-length)\n• Blind LFI: Filter Chain / ffuf -fs",
        fill="#ECFDF5", border="#047857", badge="#047857"
    )
    draw_step(
        ax, 4.9, y2, w, h,
        "ADIM 5",
        "LFI2RCE & Zehirleme (Poisoning)",
        "• Apache/Nginx access.log + curl -A (tırnaksız!)\n• PHP Session: /var/lib/php/sessions/sess_ID\n• Upload+LFI: zip:// veya phar:// deserialization\n• Docker: pearcmd.php | CVE-2024-2961",
        fill="#FEF2F2", border="#B91C1C", badge="#B91C1C"
    )
    draw_step(
        ax, 9.35, y2, w, h,
        "ADIM 6",
        "Doğrulama & Güvenli Kodlama",
        "• Kanıtı raporla (audit_report.md / JSON)\n• En iyi çözüm: Dosya adı yerine sayısal ID\n• Zorunluysa: realpath() / filepath.Rel()\n• allow_url_include=Off & Strict Allowlist",
        fill="#F1F5F9", border="#334155", badge="#334155"
    )

    arrow(ax, 4.22, y2 + h / 2, 4.83, y2 + h / 2)
    arrow(ax, 8.67, y2 + h / 2, 9.28, y2 + h / 2)

    # Bottom footer bar
    footer = patches.FancyBboxPatch(
        (0.45, 0.35),
        12.6,
        0.95,
        boxstyle="round,pad=0.05,rounding_size=0.10",
        linewidth=1.0,
        edgecolor="#CBD5E1",
        facecolor="#F8FAFC",
    )
    ax.add_patch(footer)
    ax.text(
        6.75,
        0.82,
        "Hızlı Otomasyon:  python3 tool/lfi_hunter.py --url \"http://TARGET/view?page=home\" --report audit_report.md\n"
        "Not: Yalnızca yetkili sistemlerde veya yerel test laboratuvarlarında (python3 tool/test_lfi_hunter.py) kullanın.",
        ha="center",
        va="center",
        fontsize=8.6,
        color="#1E293B",
        family="DejaVu Sans",
        linespacing=1.45,
    )

    plt.tight_layout(pad=0.2)
    fig.savefig(OUT_PATH, dpi=200, facecolor="white")
    plt.close(fig)
    print("Saved:", OUT_PATH)


if __name__ == "__main__":
    main()
