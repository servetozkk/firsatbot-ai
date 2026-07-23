from pathlib import Path
import shutil
from datetime import datetime

PROJECT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PROJECT_DIR / "app" / "templates"

REPLACEMENTS = {
    "Ä±": "ı",
    "Ä°": "İ",
    "Ã¼": "ü",
    "Ãœ": "Ü",
    "Ã¶": "ö",
    "Ã–": "Ö",
    "Ã§": "ç",
    "Ã‡": "Ç",
    "ÄŸ": "ğ",
    "Äž": "Ğ",
    "ÅŸ": "ş",
    "Åž": "Ş",
    "â€¢": "•",
    "â€“": "-",
    "â€”": "-",
    "â€™": "'",
    "Â": "",
}


def fix_text(text: str) -> str:
    for broken, correct in REPLACEMENTS.items():
        text = text.replace(broken, correct)
    return text


def main():
    if not TEMPLATES_DIR.exists():
        print("Templates klasörü bulunamadı.")
        return

    backup_dir = (
        PROJECT_DIR
        / "template_backups"
        / datetime.now().strftime("%Y%m%d_%H%M%S")
    )

    backup_dir.mkdir(parents=True, exist_ok=True)

    html_files = list(TEMPLATES_DIR.rglob("*.html"))

    print(f"Toplam {len(html_files)} HTML dosyası bulundu.\n")

    changed = 0

    for file in html_files:

        relative = file.relative_to(TEMPLATES_DIR)

        backup_file = backup_dir / relative
        backup_file.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(file, backup_file)

        original = file.read_text(
            encoding="utf-8",
            errors="replace",
        )

        fixed = fix_text(original)

        if fixed != original:

            file.write_text(
                fixed,
                encoding="utf-8",
                newline="\n",
            )

            changed += 1
            print(f"[DÜZELTİLDİ] {relative}")

        else:
            print(f"[OK]          {relative}")

    print("\n===================================")
    print(f"Düzeltilen dosya : {changed}")
    print(f"Toplam dosya     : {len(html_files)}")
    print(f"Yedek klasörü    : {backup_dir}")


if __name__ == "__main__":
    main()