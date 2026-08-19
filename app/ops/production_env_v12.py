from __future__ import annotations

import argparse
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="FırsatAI production .env oluşturucu")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--public-url", default="https://example.com")
    parser.add_argument("--output", default=str(ROOT / ".env.production"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists() and not args.force:
        print(f"HATA  Dosya zaten var: {output}")
        print("Mevcut anahtarları korumak için işlem durduruldu. Yenilemek için --force kullanın.")
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    secret_key = secrets.token_urlsafe(64)
    admin_token = secrets.token_urlsafe(48)
    content = "\n".join([
        "# FırsatAI v12.1.0 production ortamı",
        "APP_ENV=production",
        "APP_HOST=127.0.0.1",
        "APP_PORT=8000",
        "APP_NAME=Fırsat AI",
        f"PUBLIC_BASE_URL={args.public_url.rstrip('/')}",
        f"TRUSTED_HOSTS={args.host},www.{args.host}",
        f"SECRET_KEY={secret_key}",
        f"ADMIN_ACCESS_TOKEN={admin_token}",
        "SECURE_COOKIES=1",
        "CSRF_ENABLED=1",
        "RATE_LIMIT_ENABLED=1",
        "ENABLE_SCHEDULER=1",
        "",
    ])
    output.write_text(content, encoding="utf-8")
    print(f"OK  Production ortam dosyası oluşturuldu: {output}")
    print("UYARI  Bu dosyayı Git'e eklemeyin ve güvenli şekilde saklayın.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
