from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from app.middleware.security import RateLimitMiddleware, SameOriginCSRFMiddleware, AdminAccessMiddleware
from app.services.production_security_service import mask_sensitive_text, production_security_report

def c(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)
def main():
    c(callable(production_security_report),'production güvenlik raporu yüklendi')
    c('***' in mask_sensitive_text('token=abcdef'),'gizli değer maskeleme çalışıyor')
    c(RateLimitMiddleware and SameOriginCSRFMiddleware and AdminAccessMiddleware,'güvenlik middleware sınıfları yüklendi')
    main=(ROOT/'main.py').read_text(encoding='utf-8-sig')
    c('app.add_middleware(AdminAccessMiddleware)' in main,'admin erişim middleware bağlı')
    c('app.add_middleware(SameOriginCSRFMiddleware)' in main,'CSRF middleware bağlı')
    c('app.add_middleware(RateLimitMiddleware)' in main,'rate limit middleware bağlı')
    c('admin_v10_security_router' in main,'güvenlik paneli router bağlı')
    c('Content-Security-Policy' in (ROOT/'app/middleware/production.py').read_text(encoding='utf-8'),'CSP güvenlik başlığı mevcut')
    c((ROOT/'app/templates/admin_v10_security.html').exists(),'güvenlik paneli mevcut')
    print('\nFırsatAI v10.3 smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
