from app.services.cross_store_search_service import _search_result_candidate_score, STORE_DEFINITIONS


def ok(c,m):
    if not c: raise AssertionError(m)
    print("OK ",m)


def main():
    q="ASUS vivobook 15 x1504va-bq5391 intel core 5 120u 8gb ram 512gb ssd"
    wrong="https://www.teknosa.com/asus-vivobook-15-x1504vaa69-nj3665a69-intel-core-5-120u-8gb-512gb-ssd-w11home-156-fhd-laptop-p-786361483"
    right="https://www.teknosa.com/asus-vivobook-15-x1504vaa69-bq5391a69-intel-core-5-120u-8gb-512gb-ssd-156-fhd-laptop-p-1"
    s1,r1=_search_result_candidate_score(search_query=q,href=wrong,label=wrong)
    s2,r2=_search_result_candidate_score(search_query=q,href=right,label=right)
    ok(s1 < 0, f"Teknosa NJ3665 farklı varyant reddedildi: {r1}")
    ok(s2 > 0, f"Teknosa BQ5391A69 normalize edilip kabul edildi: {r2}")
    gg=next(x for x in STORE_DEFINITIONS if x.code=="gaminggen")
    ok("a[href]" not in gg.product_link_selectors, "Gaming.Gen genel link fallback kaldırıldı")
    ok(all("woocommerce" in x or "product" in x for x in gg.product_link_selectors), "Gaming.Gen yalnızca ürün kartı seçicileri kullanıyor")
    print("FırsatAI v18.4.0 smoke test başarılı.")
    return 0

if __name__=="__main__": raise SystemExit(main())
