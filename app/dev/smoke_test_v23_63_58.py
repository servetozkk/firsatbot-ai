from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/"main.py").read_text(encoding="utf-8")
launcher=(ROOT/"BASLAT.bat").read_text(encoding="utf-8",errors="replace")
repair=(ROOT/"app"/"dev"/"repair_v23_63_58_existing_canonical.py").read_text(encoding="utf-8")
checks=[
("runtime endpoint","/api/runtime-identity/v236358" in main),
("runtime version",'_RUNTIME_VERSION_V236323 = "23.63.58"' in main),
("history scope","h27-to-gp28-null-h175-to-gp29-v30-h244-to-gp127-v155-only" in main),
("delete scope","v27-v154-v188-after-zero-fk-refs" in main),
("preserve scope","v155-exact-snapshot-no-write" in main),
("null variant policy","allowed-only-for-h27-because-current-offer-and-raw-both-null" in main),
("no merge","disabled-no-canonical-merge-no-new-variant-creation" in main),
("repair hook","repair_v23_63_58_existing_canonical.py" in launcher),
("launcher title","FirsatAI v23.63.58 MASTER" in launcher),
("plans","27:(27,26,28,None)" in repair and "175:(154,126,29,30)" in repair and "244:(188,150,127,155)" in repair),
("preserve v155","PRESERVE_VARIANT=155" in repair),
]
p=f=0
for n,c in checks:
    if c: p+=1; print("OK  ",n)
    else: f+=1; print("FAIL",n)
print("V23.63.58 smoke PASS={} FAIL={}".format(p,f))
if f: raise SystemExit(1)
