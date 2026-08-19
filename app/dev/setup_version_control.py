from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.dev.db_migrate import migrate


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=PROJECT_ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def ensure_git_repository() -> None:
    if shutil.which("git") is None:
        print("Git bulunamadı. Alembic kurulumu tamamlandı; Git daha sonra kurulabilir.")
        return

    if not (PROJECT_ROOT / ".git").exists():
        run("git", "init")
        print("Git deposu oluşturuldu.")

    # Local fallback identity; existing user configuration is not overwritten.
    email = run("git", "config", "user.email", check=False).stdout.strip()
    name = run("git", "config", "user.name", check=False).stdout.strip()
    if not email:
        run("git", "config", "user.email", "firsatai@localhost")
    if not name:
        run("git", "config", "user.name", "FirsatAI Local")

    run("git", "add", ".")
    result = run("git", "diff", "--cached", "--quiet", check=False)
    if result.returncode != 0:
        run("git", "commit", "-m", "FirsatAI v6.7 baseline")
        print("İlk güvenli Git kaydı oluşturuldu.")
    else:
        print("Git çalışma alanında kaydedilecek yeni değişiklik yok.")


def main() -> None:
    migrate()
    ensure_git_repository()
    print("Git + Alembic düzeni hazır.")


if __name__ == "__main__":
    main()
