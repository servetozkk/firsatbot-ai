from __future__ import annotations

import ast
import hashlib
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "app/services/canonical_identity_convergence_v223_service.py"


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)
    print("OK ", msg)


def load_identity_functions():
    tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
    wanted = {"_parse_identity_source", "_is_phone_identity", "canonical_phone_identity_source"}
    body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    module = ast.Module(body=body, type_ignores=[])
    ns = {"re": re}
    exec(compile(module, str(SERVICE), "exec"), ns)
    return ns["canonical_phone_identity_source"]


def simulate_unique_conflict_safe_merge() -> None:
    con = sqlite3.connect(":memory:")
    con.execute("create table product_groups(id integer primary key, identity_source text, group_key text unique)")
    con.execute("create unique index ux_identity_source on product_groups(identity_source) where identity_source is not null and trim(identity_source) <> ''")
    source_with_ram = "identity_v3:brand=xiaomi|family=redmi note 15|variant=pro|ram=8gb|storage=256gb"
    canonical = "identity_v3:brand=xiaomi|family=redmi note 15|variant=pro|storage=256gb"
    con.execute("insert into product_groups values(1, ?, 'legacy-a')", (source_with_ram,))
    con.execute("insert into product_groups values(2, ?, 'legacy-b')", (canonical,))
    try:
        con.execute("update product_groups set identity_source=? where id=1", (canonical,))
        raise AssertionError("legacy update UNIQUE çakışması üretmeliydi")
    except sqlite3.IntegrityError:
        pass
    pending = "identity_v3:merge_pending=group-2-" + hashlib.sha256(f"group:2:{canonical}".encode()).hexdigest()[:16]
    con.execute("update product_groups set identity_source=? where id=2", (pending,))
    con.execute("update product_groups set identity_source=? where id=1", (canonical,))
    con.execute("delete from product_groups where id=2")
    rows = con.execute("select id,identity_source from product_groups").fetchall()
    check(rows == [(1, canonical)], "UNIQUE conflict owner vacate -> winner canonical identity -> duplicate merge sırası çalışıyor")


def main() -> None:
    check((ROOT / "VERSION").read_text(encoding="utf-8-sig").strip() == "23.13.0", "VERSION 23.13.0")
    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    service_text = SERVICE.read_text(encoding="utf-8")
    check('/api/runtime-identity/v2313' in main_text, "v23.13 runtime endpoint mevcut")
    check('VERSION = "23.13.0"' in service_text, "canonical convergence engine 23.13.0")
    check('_vacate_group_identity_conflicts' in service_text and '_vacate_global_identity_conflicts' in service_text, "ProductGroup + GlobalProduct conflict-safe vacate katmanı mevcut")
    check('unsafe ProductGroup identity collision' in service_text and 'unsafe GlobalProduct identity collision' in service_text, "cross-bucket collision fail-closed koruması mevcut")

    canonical_phone_identity_source = load_identity_functions()
    tablet_source = "identity_v3:brand=samsung|family=galaxy tab a11|ram=8gb|storage=128gb"
    check(canonical_phone_identity_source(tablet_source, category="Elektronik > Bilgisayar&Tablet > Tablet > Samsung Tablet") is None, "V22.3 phone convergence Galaxy Tab A11'e dokunmuyor")
    watch_source = "identity_v3:brand=samsung|family=galaxy watch 8|variant=base"
    check(canonical_phone_identity_source(watch_source, category="Giyilebilir Teknoloji > Akıllı Saat") is None, "V22.3 phone convergence wearable'a dokunmuyor")
    phone_source = "identity_v3:brand=xiaomi|family=redmi note 15|variant=pro|ram=8gb|storage=256gb"
    check(canonical_phone_identity_source(phone_source, category="Cep Telefonu") == "identity_v3:brand=xiaomi|family=redmi note 15|variant=pro|storage=256gb", "telefon convergence RAM'i sözleşmeden güvenle çıkarıyor")

    simulate_unique_conflict_safe_merge()

    proc = subprocess.run([sys.executable, str(ROOT / "app/dev/smoke_test_v23_12_0.py")], cwd=str(ROOT), text=True)
    check(proc.returncode == 0, "v23.12 matcher/evidence regression seti korundu")
    print("OK  FirsatAI v23.13 smoke test tamamlandi")


if __name__ == "__main__":
    main()
