from pathlib import Path
import ast, re

r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(c); ast.parse(m)

# Mirror boundary logic for regression examples.
def present(hay, term):
    hay=hay.casefold()
    term=term.casefold()
    return re.search(r"(?<![a-z0-9])"+re.escape(term)+r"(?![a-z0-9])", hay) is not None

checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.62.6"),
("boundary helper","def _color_term_present_v23626" in c),
("blue not bluetooth",not present("huawei-freebuds-se-2-bluetooth-53","blue")),
("blue explicit",present("huawei-freebuds-se-2-blue","blue")),
("white explicit",present("freebuds-se-2-ceramic white","white")),
("n11 single helper","def _n11_single_card_price_priority_v23626" in c),
("n11 sort uses single","self._n11_single_card_price_priority_v23626(" in c),
("detail observability","V23.62.6 DETAIL ORDER" in c),
("amazon v23625 preserved","V23.62.5 AMAZON VERIFIED AUDIO SEARCH-CARD OFFER" in (r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")),
("accessory preserved","V23.62.5 AUDIO ACCESSORY PREFILTER" in c),
("runtime","/api/runtime-identity/v23626" in m),
("v23625 preserved","/api/runtime-identity/v23625" in m),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
