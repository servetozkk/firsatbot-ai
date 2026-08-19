from pathlib import Path
from tempfile import TemporaryDirectory
import os, sqlite3
ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)
def main():
    ok((ROOT/'VERSION').read_text(encoding='utf-8-sig').strip()=='13.8.1','VERSION 13.8.1')
    from app.services import advanced_alert_service as svc
    with TemporaryDirectory(ignore_cleanup_errors=True) as td:
        db=Path(td)/'test.db'; os.environ['FIRSATAI_ALERT_DB_PATH']=str(db)
        with sqlite3.connect(db) as c:
            c.executescript('CREATE TABLE global_products(id INTEGER PRIMARY KEY); INSERT INTO global_products(id) VALUES(1);')
        svc.ensure_schema()
        for typ,threshold in [('price_target',1000),('stock_back',None),('coupon_available',None),('campaign_available',None),('new_seller',None),('official_seller',None)]:
            a=svc.create_alert(owner_key='test',alert_type=typ,global_product_id=1,threshold_value=threshold)
            ok(a['alert_type']==typ,f'{typ} alarmı oluşturuluyor')
        price=svc.list_alerts(owner_key='test')[0]
        result=svc.evaluate_alert(owner_key='test',alert_id=price['id'],signals={'official_seller':True,'current_price':500,'in_stock':True})
        # evaluate the selected alert according to its type; status must always be valid
        ok(result['status'] in {'WAITING','READY_FOR_NOTIFICATION'},'alarm değerlendirmesi geçerli durum üretiyor')
        created=svc.create_alert(owner_key='test',alert_type='price_target',global_product_id=1,threshold_value=1000)
        trig=svc.evaluate_alert(owner_key='test',alert_id=created['id'],signals={'current_price':900})
        ok(trig['status']=='READY_FOR_NOTIFICATION','READY_FOR_NOTIFICATION durumu üretiliyor')
        ok(len(svc.events(owner_key='test',alert_id=created['id']))>=2,'alarm geçmişi tutuluyor')
        os.environ.pop('FIRSATAI_ALERT_DB_PATH',None)
    main_text=(ROOT/'main.py').read_text(encoding='utf-8-sig')
    route=(ROOT/'app/web/advanced_alert_routes.py').read_text(encoding='utf-8-sig')
    ok('advanced_alert_router' in main_text,'alarm router uygulamaya bağlı')
    ok('/api/alerts/v13' in route and '/alarmlar' in route,'alarm merkezi ve API mevcut')
    ok('/admin/alerts' in route,'admin alarm paneli mevcut')
    print('\nFırsatAI v13.8.1 Gelişmiş Alarm Sistemi smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
