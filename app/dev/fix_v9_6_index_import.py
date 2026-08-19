from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()


def main() -> int:
    path = ROOT / "app/database/models.py"
    text = path.read_text(encoding="utf-8")

    if "Index" in text.split("from sqlalchemy import", 1)[-1].split(")", 1)[0]:
        print("Index importu zaten mevcut.")
        return 0

    marker = "from sqlalchemy import (\n"
    if marker in text:
        text = text.replace(
            marker,
            marker + "    Index,\n",
            1,
        )
    else:
        single_line = "from sqlalchemy import "
        position = text.find(single_line)
        if position < 0:
            raise RuntimeError("SQLAlchemy import bloğu bulunamadı.")

        line_end = text.find("\n", position)
        line = text[position:line_end]
        if "Index" not in line:
            line = line.rstrip() + ", Index"
            text = text[:position] + line + text[line_end:]

    path.write_text(text, encoding="utf-8")
    print("SQLAlchemy Index importu eklendi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
