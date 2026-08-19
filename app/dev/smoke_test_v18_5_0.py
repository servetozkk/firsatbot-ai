from app.services.cross_store_search_service import _search_result_candidate_score
from app.parsers.teknosa_parser import TeknosaParser

q="ASUS vivobook 15 x1504va-bq5391 intel core 5 120u 8gb ram 512gb ssd"
wrong="https://www.teknosa.com/asus-vivobook-15-x1504vaa9-nj3665a9-intel-core-5-120u-8gb-1tb-ssd-w11home-156-fhd-laptop-p-786361415"
right="https://www.teknosa.com/asus-vivobook-15-x1504vaa9-bq5391a9-intel-core-5-120u-8gb-512gb-ssd-156-fhd-laptop-p-1"
assert _search_result_candidate_score(search_query=q,href=wrong,label=wrong)[0] < 0
assert _search_result_candidate_score(search_query=q,href=right,label=right)[0] > 0
assert TeknosaParser._model_from_name_or_url("", wrong) == "X1504VA-NJ3665"
assert TeknosaParser._model_from_name_or_url("", right) == "X1504VA-BQ5391"
print("OK v18.5 Teknosa A9/varyant/depolama testleri")
