from pathlib import Path
from app.services.ai_purchase_assistant_service import build_ai_purchase_assistant

ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)

def main():
    version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
    ok(version=='13.1.0','VERSION 13.1.0')
    tpl=(ROOT/'app/templates/product_group_detail_v4.html').read_text(encoding='utf-8')
    ok('ai-v131-plan' in tpl,'karar planı kartı mevcut')
    result=build_ai_purchase_assistant(
        comparison={'best_price':10000,'offer_count':3,'saving_percent':8},
        history_data={'lowest_price':9500,'highest_price':13000,'average_price':11000,'price_record_count':12,'stores':[{'history':[{'price':11000},{'price':10500},{'price':10000}],'current_price':10000}]},
        ai_analysis={'score':80,'trend':{'code':'stable','change_percent':0}},
    )
    ok(result.get('assistant_version')=='13.1','asistan sürümü 13.1')
    ok(bool(result.get('primary_action')),'net aksiyon planı üretiliyor')
    ok(result.get('data_quality') in {'Sınırlı','Orta','Güçlü'},'veri kalitesi sınıflandırılıyor')
    ok(bool(result.get('scenario')),'fiyat senaryosu üretiliyor')
    ok(result.get('decision_consistency') in {'Tutarlı','Temkinli','Yüksek risk'},'karar tutarlılığı üretiliyor')
    print('\nFırsatAI v13.1.0 Akıllı Satın Alma Asistanı smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
