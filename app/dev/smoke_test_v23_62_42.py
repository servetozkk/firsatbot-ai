from pathlib import Path
r=Path(__file__).resolve().parents[2]
main=(r/"main.py").read_text(encoding="utf-8")
hb=(r/"app/scrapers/hepsiburada.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.62.42"),
("runtime v236242","/api/runtime-identity/v236242" in main),
("single source","_RUNTIME_VERSION_V236242 = \"23.62.42\"" in main),
("force single source","\"runtime_version\": _RUNTIME_VERSION_V236242" in main),
("hb one second recheck","enumerate((1_000,), start=1)" in hb),
("hb no two second recheck","enumerate((1_000, 2_000), start=1)" not in hb),
("hb one attempt marker","challenge kontrolü {attempt}/1" in hb),
("security bypass disabled","security_challenge_bypass\": \"disabled" in main),
("n11 hysteresis preserved","n11_strong_first_hysteresis_ms\": 3750" in main),
("n11 detail cap preserved","n11_detail_http_timeout_seconds\": 4.5" in main),
("itopya preserved","v23.62.38-preserved" in main),
("idefix preserved","v23.62.36-preserved" in main),
]
for name,ok in checks:
    assert ok,name
    print("OK ",name)
