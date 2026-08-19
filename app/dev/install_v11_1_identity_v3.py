from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()


def patch_identity_parser() -> None:
    path = ROOT / "app/services/product_identity_service.py"
    text = path.read_text(encoding="utf-8")

    if "COMPACT_RAM_STORAGE_PATTERN" not in text:
        marker = (
            '    CAPACITY_PATTERN = re.compile('
            'r"(?<!\\d)(\\d+(?:[.,]\\d+)?)\\s*(tb|gb|mb)\\b", re.I)\n'
        )
        addition = marker + (
            '    COMPACT_RAM_STORAGE_PATTERN = re.compile(\n'
            '        r"(?<!\\d)([2-9]|1[0-9]|2[0-4])\\s*(?:gb?|g)?\\s*'
            '(?:\\+|/|x)\\s*"\n'
            '        r"(64|128|256|512|1024|2048)\\s*(?:gb?|g|tb)?\\b",\n'
            '        re.I,\n'
            '    )\n'
            '    JOINED_RAM_STORAGE_PATTERN = re.compile(\n'
            '        r"(?<!\\d)([2-9]|1[0-9]|2[0-4])\\s*g\\s*"\n'
            '        r"(64|128|256|512|1024|2048)\\s*(?:gb?|g|tb)?\\b",\n'
            '        re.I,\n'
            '    )\n'
        )
        if marker not in text:
            raise RuntimeError("CAPACITY_PATTERN noktası bulunamadı.")
        text = text.replace(marker, addition, 1)

    old = (
        "    def _extract_ram_storage(cls, text: str) -> tuple[int | None, int | None]:\n"
        "        ram: int | None = None\n"
        "        ram_match = cls.RAM_CONTEXT_PATTERN.search(text)\n"
    )
    new = (
        "    def _extract_ram_storage(cls, text: str) -> tuple[int | None, int | None]:\n"
        "        folded = cls._ascii_fold(text)\n\n"
        "        # 12G+256G, 12/256 ve 12G512GB biçimleri kesin ayrıştırılır.\n"
        "        compact = cls.COMPACT_RAM_STORAGE_PATTERN.search(folded)\n"
        "        if compact is None:\n"
        "            compact = cls.JOINED_RAM_STORAGE_PATTERN.search(folded)\n"
        "        if compact is not None:\n"
        "            return int(compact.group(1)), int(compact.group(2))\n\n"
        "        ram: int | None = None\n"
        "        ram_match = cls.RAM_CONTEXT_PATTERN.search(text)\n"
    )
    if "12G+256G" not in text:
        if old not in text:
            raise RuntimeError("_extract_ram_storage başlangıcı bulunamadı.")
        text = text.replace(old, new, 1)

    path.write_text(text, encoding="utf-8")


def patch_cross_store_gate() -> None:
    path = ROOT / "app/services/cross_store_search_service.py"
    text = path.read_text(encoding="utf-8")

    import_line = "from app.services.offer_integrity_service import validate_variant\n"
    if import_line not in text:
        anchor = (
            "from app.services.product_identity_service import "
            "ProductIdentityService\n"
        )
        if anchor not in text:
            raise RuntimeError("ProductIdentityService importu bulunamadı.")
        text = text.replace(anchor, anchor + import_line, 1)

    marker = (
        "        source_model = (\n"
        "            ProductIdentityService.get_normalized_model(\n"
        "                source_product\n"
        "            )\n"
        "        )\n"
    )
    gate = (
        "        source_identity = ProductIdentityService.parse(source_product)\n"
        "        candidate_identity = ProductIdentityService.parse(candidate_product)\n"
        "        variant_check = validate_variant(source_identity, candidate_identity)\n"
        "        if not variant_check.compatible:\n"
        "            return (\n"
        "                False,\n"
        "                0.0,\n"
        "                'Zorunlu varyant kapısı: ' + '; '.join(variant_check.reasons),\n"
        "            )\n\n"
        + marker
    )
    if "Zorunlu varyant kapısı:" not in text:
        if marker not in text:
            raise RuntimeError("_is_same_product model noktası bulunamadı.")
        text = text.replace(marker, gate, 1)

    path.write_text(text, encoding="utf-8")


def patch_version() -> None:
    version = ROOT / "VERSION"
    if version.exists():
        version.write_text("11.1.0\n", encoding="utf-8")


def main() -> int:
    patch_identity_parser()
    patch_cross_store_gate()
    patch_version()
    print("FırsatAI v11.1 Kimlik Motoru V3 entegre edildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
