from pathlib import Path
r=Path(__file__).resolve().parents[2]
m=(r/"main.py").read_text(encoding="utf-8")
d=(r/"app/ops/runtime_crash_diagnostics_v23618.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.61.8"),
("main install","install_runtime_crash_diagnostics_v23618()" in m),
("runtime endpoint","/api/runtime-identity/v23618" in m),
("diag endpoint","/api/runtime-crash-diagnostics/v23618" in m),
("sys hook","UNHANDLED_MAIN_EXCEPTION" in d),
("thread hook","UNHANDLED_THREAD_EXCEPTION" in d),
("faulthandler","faulthandler.enable" in d),
("atexit","PROCESS_ATEXIT" in d),
("v23617 preserved","/api/runtime-identity/v23617" in m),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
