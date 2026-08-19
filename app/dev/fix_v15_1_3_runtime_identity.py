from pathlib import Path
import ast

root = Path.cwd()
main_path = root / "main.py"
text = main_path.read_text(encoding="utf-8")

marker = "# V15_1_3_RUNTIME_IDENTITY"

if marker not in text:
    block = '''
# V15_1_3_RUNTIME_IDENTITY
@app.get("/api/runtime-identity/v1513", include_in_schema=False)
def runtime_identity_v1513():
    from pathlib import Path

    project_root = Path(__file__).resolve().parent
    version_path = project_root / "VERSION"
    version = (
        version_path.read_text(encoding="utf-8").strip()
        if version_path.exists()
        else "UNKNOWN"
    )

    multi_store_routes = [
        {
            "path": getattr(route, "path", None),
            "methods": sorted(
                getattr(route, "methods", set()) or set()
            ),
            "name": getattr(route, "name", None),
        }
        for route in app.routes
        if "multi-store-repair" in str(
            getattr(route, "path", "")
        )
    ]

    return {
        "ok": True,
        "runtime_version": version,
        "project_root": str(project_root),
        "main_file": str(Path(__file__).resolve()),
        "multi_store_routes": multi_store_routes,
    }
'''
    main_path.write_text(
        text.rstrip() + "\n\n" + block + "\n",
        encoding="utf-8",
    )
    print("OK  Runtime kimlik endpoint'i eklendi")
else:
    print("OK  Runtime kimlik endpoint'i zaten mevcut")
