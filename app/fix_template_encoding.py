from datetime import datetime
from pathlib import Path
import shutil


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
TEMPLATES_DIR = SCRIPT_DIR / "templates"

REPLACEMENTS = {
    "\u00c4\u00b1": "\u0131",
    "\u00c4\u00b0": "\u0130",
    "\u00c3\u00bc": "\u00fc",
    "\u00c3\u0153": "\u00dc",
    "\u00c3\u00b6": "\u00f6",
    "\u00c3\u2013": "\u00d6",
    "\u00c3\u00a7": "\u00e7",
    "\u00c3\u2021": "\u00c7",
    "\u00c4\u0178": "\u011f",
    "\u00c4\u017e": "\u011e",
    "\u00c5\u0178": "\u015f",
    "\u00c5\u017e": "\u015e",
    "\u00e2\u20ac\u00a2": "\u2022",
    "\u00e2\u20ac\u201c": "-",
    "\u00e2\u20ac\u201d": "-",
    "\u00e2\u20ac\u2122": "'",
    "\u00c2": "",
}


def fix_text(text: str) -> str:
    fixed_text = text

    for broken, correct in REPLACEMENTS.items():
        fixed_text = fixed_text.replace(broken, correct)

    return fixed_text


def main() -> None:
    print(f"Proje klasoru   : {PROJECT_DIR}")
    print(f"Templates yolu  : {TEMPLATES_DIR}")
    print()

    if not TEMPLATES_DIR.exists():
        print("HATA: Templates klasoru bulunamadi.")
        return

    backup_dir = (
        PROJECT_DIR
        / "template_backups"
        / datetime.now().strftime("%Y%m%d_%H%M%S")
    )

    html_files = list(TEMPLATES_DIR.rglob("*.html"))

    if not html_files:
        print("HATA: Templates klasorunde HTML dosyasi bulunamadi.")
        return

    backup_dir.mkdir(parents=True, exist_ok=True)

    print(f"Toplam {len(html_files)} HTML dosyasi bulundu.")
    print()

    changed_count = 0

    for file_path in html_files:
        relative_path = file_path.relative_to(TEMPLATES_DIR)

        backup_file = backup_dir / relative_path
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_file)

        original_text = file_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        fixed_text = fix_text(original_text)

        if fixed_text != original_text:
            file_path.write_text(
                fixed_text,
                encoding="utf-8",
                newline="\n",
            )

            changed_count += 1
            print(f"[DUZELTILDI] {relative_path}")
        else:
            print(f"[DEGISMEDI]  {relative_path}")

    print()
    print("========================================")
    print(f"Duzeltilen dosya : {changed_count}")
    print(f"Toplam dosya     : {len(html_files)}")
    print(f"Yedek klasoru    : {backup_dir}")


if __name__ == "__main__":
    main()
