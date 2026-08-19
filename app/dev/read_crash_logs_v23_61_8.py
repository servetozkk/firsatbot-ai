from pathlib import Path

r=Path(__file__).resolve().parents[2]
log_dir=r/"logs"
for name in ("runtime_crash_v23618.log","runtime_faulthandler_v23618.log","uvicorn_console_v23618.log"):
    p=log_dir/name
    print("\n" + "="*20, name, "="*20)
    if not p.exists():
        print("DOSYA YOK")
        continue
    text=p.read_text(encoding="utf-8",errors="replace")
    print(text[-20000:] if text else "BOS")
