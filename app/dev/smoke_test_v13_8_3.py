from pathlib import Path
from app.services.beta_readiness_service import ENGINE_VERSION, build_beta_readiness

def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)

def main():
    root=Path(__file__).resolve().parents[2]
    version=(root/'VERSION').read_text(encoding='utf-8-sig').strip()
    ok(version=='13.8.3','VERSION 13.8.3')
    report=build_beta_readiness(False)
    ok(ENGINE_VERSION=='13.8.3','beta readiness motoru sürümü doğru')
    ok(report['summary']['total_modules']>=20,'20+ çekirdek modül denetleniyor')
    ok(report['summary']['missing_modules']==0,'tüm beta modülleri mevcut')
    ok(report['database']['integrity']=='ok','SQLite integrity başarılı')
    ok(report['database']['foreign_key_violations']==0,'foreign key ihlali yok')
    ok(report['status']=='BETA_READY','kapalı beta durumu hazır')
    main=(root/'main.py').read_text(encoding='utf-8')
    ok('beta_readiness_router' in main,'beta readiness router uygulamaya bağlı')
    routes=(root/'app/web/beta_readiness_routes.py').read_text(encoding='utf-8')
    ok('/api/system/health/v13' in routes,'merkezi sistem sağlık API mevcut')
    ok('/admin/beta' in routes,'admin beta paneli mevcut')
    ok((root/'app/templates/beta_readiness_admin.html').exists(),'beta dashboard template mevcut')
    print('\nFırsatAI v13.8.3 Kapalı Beta Hazırlığı smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
