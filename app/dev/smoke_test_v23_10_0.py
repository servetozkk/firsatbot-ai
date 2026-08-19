from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "app" / "services" / "cross_store_search_service.py"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def load_isolated_namespace() -> dict:
    source = SERVICE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = {
        "_fold_search_text", "_extract_search_hardware",
        "_canonical_family_query_identity_v2310",
        "_canonical_family_candidate_score_v2310",
        "_query_identity_tokens", "_product_type_gate_reason",
        "_search_result_candidate_score", "_wearable_card_identity",
        "_wearable_candidate_score",
    }
    chunks = ["import re\n"]
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ACCESSORY_STRONG_TOKENS":
                    chunks.append(ast.get_source_segment(source, node) + "\n")
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            chunks.append(ast.get_source_segment(source, node) + "\n")
    ns: dict = {}
    exec("\n".join(chunks), ns)
    return ns


def main() -> None:
    check((ROOT / "VERSION").read_text(encoding="utf-8-sig").strip() == "23.10.0", "VERSION 23.10.0")
    ns = load_isolated_namespace()
    identity = ns["_query_identity_tokens"]
    score = ns["_search_result_candidate_score"]

    positive = [
        ("LENOVO ideapad slim 3 intel n100 4gb ram 128gb ssd 15.6 82xb009gtx", "https://x/82xb009gtx", "Lenovo Ideapad Slim 3 N100 4GB 128GB 82XB009GTX"),
        ("Apple 13 macbook neo indigo 256gb", "https://x/macbook-neo-256", "Apple MacBook Neo 13 inc 256GB"),
        ("Apple watch se 3", "https://x/apple-watch-se-3", "Apple Watch SE 3 GPS 44mm"),
        ("Xiaomi redmi buds 6 play", "https://x/redmi-buds-6-play", "Xiaomi Redmi Buds 6 Play Pembe Bluetooth Kulaklik"),
        ("Samsung galaxy tab a11 8gb ram 128gb ssd", "https://x/galaxy-tab-a11-128gb", "Samsung Galaxy Tab A11 8GB 128GB Tablet"),
    ]
    for query, href, label in positive:
        result = score(search_query=query, href=href, label=label)
        check(result[0] > 0, f"gercek aday kabul: {identity(query)['family']} -> {result[0]}")

    negative = [
        ("LENOVO ideapad slim 3 intel n100 4gb ram 128gb ssd 15.6 82xb009gtx", "https://x/82xb009htx", "Lenovo Ideapad Slim 3 N100 4GB 128GB 82XB009HTX"),
        ("Xiaomi redmi buds 6 play", "https://x/redmi-buds-6-play-kilif", "Xiaomi Redmi Buds 6 Play Kilif Silikon Koruma Kabi"),
        ("Samsung galaxy tab a11 8gb ram 128gb ssd", "https://x/galaxy-tab-a11-256gb", "Samsung Galaxy Tab A11 8GB 256GB Tablet"),
        ("Apple watch se 3", "https://x/apple-watch-se-2", "Apple Watch SE 2 GPS 44mm"),
    ]
    for query, href, label in negative:
        result = score(search_query=query, href=href, label=label)
        check(result[0] < 0, f"yanlis aday RED: {result[1]}")

    text = SERVICE.read_text(encoding="utf-8")
    check("V23.6 aftermarket/uyumlu aksesuar kesin red" in text, "v23.6 original-vs-compatible guard korundu")
    check("telefon ağ varyantı" in text, "v23.3 base/5G guard korundu")
    check("telefon varyantı farklı" in text, "phone Pro/Pro+ varyant guard korundu")
    print("OK  FirsatAI v23.10 smoke test tamamlandi")


if __name__ == "__main__":
    main()
