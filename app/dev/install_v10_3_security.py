from __future__ import annotations
from pathlib import Path
ROOT=Path.cwd()

def patch_config():
    p=ROOT/'app/core/config.py'; t=p.read_text(encoding='utf-8')
    if 'def _env_list(' not in t:
        t=t.replace('def _env_int(name: str, default: int, minimum: int = 0) -> int:\n','def _env_list(name: str, default: str = "") -> tuple[str, ...]:\n    return tuple(item.strip().casefold() for item in os.getenv(name, default).split(",") if item.strip())\n\n\ndef _env_int(name: str, default: int, minimum: int = 0) -> int:\n',1)
    fields=(
        '    secret_key: str = os.getenv("SECRET_KEY", "dev-only-change-me")\n'
        '    admin_access_token: str = os.getenv("ADMIN_ACCESS_TOKEN", "").strip()\n'
        '    admin_cookie_name: str = os.getenv("ADMIN_COOKIE_NAME", "firsat_admin")\n'
        '    admin_session_minutes: int = _env_int("ADMIN_SESSION_MINUTES", 480, 5)\n'
        '    secure_cookies: bool = _env_bool("SECURE_COOKIES", False)\n'
        '    csrf_enabled: bool = _env_bool("CSRF_ENABLED", True)\n'
        '    rate_limit_enabled: bool = _env_bool("RATE_LIMIT_ENABLED", True)\n'
        '    rate_limit_per_minute: int = _env_int("RATE_LIMIT_PER_MINUTE", 180, 10)\n'
        '    admin_rate_limit_per_minute: int = _env_int("ADMIN_RATE_LIMIT_PER_MINUTE", 90, 10)\n'
        '    trusted_hosts: tuple[str, ...] = _env_list("TRUSTED_HOSTS", "127.0.0.1:8000,localhost:8000")\n'
    )
    if 'admin_access_token:' not in t: t=t.replace('    database_path: Path = Path(\n',fields+'    database_path: Path = Path(\n',1)
    props=(
        '\n    @property\n    def secret_key_is_strong(self) -> bool:\n'
        '        return len(self.secret_key) >= 32 and self.secret_key != "dev-only-change-me"\n'
        '\n    @property\n    def admin_protection_enabled(self) -> bool:\n'
        '        return bool(self.admin_access_token) or self.is_production\n'
    )
    if 'def secret_key_is_strong' not in t: t=t.replace('\n\nsettings = Settings()',props+'\n\nsettings = Settings()',1)
    p.write_text(t,encoding='utf-8')

def patch_main():
    p=ROOT/'main.py'; t=p.read_text(encoding='utf-8-sig')
    if 'AdminAccessMiddleware' not in t:
        t=t.replace('from app.middleware.performance import RequestTimingMiddleware\n','from app.middleware.performance import RequestTimingMiddleware\nfrom app.middleware.security import AdminAccessMiddleware, SameOriginCSRFMiddleware, RateLimitMiddleware\nfrom app.web.admin_v10_security_routes import router as admin_v10_security_router\n',1)
    if 'app.add_middleware(RateLimitMiddleware)' not in t:
        t=t.replace('app.add_middleware(GZipMiddleware, minimum_size=700)\n','app.add_middleware(GZipMiddleware, minimum_size=700)\napp.add_middleware(RateLimitMiddleware)\napp.add_middleware(SameOriginCSRFMiddleware)\napp.add_middleware(AdminAccessMiddleware)\n',1)
    if 'app.include_router(admin_v10_security_router)' not in t:
        t=t.replace('app.include_router(admin_v10_scraper_health_router)\n','app.include_router(admin_v10_scraper_health_router)\napp.include_router(admin_v10_security_router)\n',1)
    p.write_text(t,encoding='utf-8-sig')

def patch_headers():
    p=ROOT/'app/middleware/production.py'; t=p.read_text(encoding='utf-8')
    if 'Content-Security-Policy' not in t:
        insertion='''        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")\n        response.headers.setdefault("Content-Security-Policy", "default-src 'self' https: data: blob:; script-src 'self' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https:; img-src 'self' https: data: blob:; connect-src 'self' https:; frame-ancestors 'self'; base-uri 'self'; form-action 'self'")\n        if request.url.scheme == "https":\n            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")\n'''
        t=t.replace('        path = request.url.path\n',insertion+'        path = request.url.path\n',1)
    p.write_text(t,encoding='utf-8')

def patch_account():
    p=ROOT/'app/web/account_routes.py'; t=p.read_text(encoding='utf-8')
    if 'from app.core.config import settings' not in t: t=t.replace('from app.database.database import SessionLocal\n','from app.database.database import SessionLocal\nfrom app.core.config import settings\n',1)
    t=t.replace('secure=False,','secure=settings.secure_cookies,')
    p.write_text(t,encoding='utf-8')

def main():
    patch_config(); patch_main(); patch_headers(); patch_account(); print('V10.3 production güvenlik sertleştirmesi entegre edildi.')
if __name__=='__main__': raise SystemExit(main())
