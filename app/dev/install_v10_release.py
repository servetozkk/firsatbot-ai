from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()


def patch_main() -> None:
    path = ROOT / 'main.py'
    text = path.read_text(encoding='utf-8-sig').replace('\ufeff', '')
    import_line = (
        'from app.web.admin_v10_release_routes '
        'import router as admin_v10_release_router\n'
    )
    if import_line not in text:
        anchor = (
            'from app.web.admin_v9_performance_routes '
            'import router as admin_v9_performance_router\n'
        )
        if anchor in text:
            text = text.replace(anchor, anchor + import_line, 1)
        else:
            text = import_line + text
    include = 'app.include_router(admin_v10_release_router)\n'
    if include not in text:
        anchor = 'app.include_router(admin_v9_performance_router)\n'
        text = text.replace(anchor, anchor + include, 1)
    path.write_text(text, encoding='utf-8-sig')


def patch_menu() -> None:
    path = ROOT / 'app/templates/base.html'
    text = path.read_text(encoding='utf-8')
    if '/admin/v10-release' in text:
        return
    nav = (
        '\n            <a class="admin-nav-item '
        '{% if request.url.path == \'/admin/v10-release\' %}active{% endif %}" '
        'href="/admin/v10-release"><span>✓</span> V10 Release</a>'
    )
    marker = 'href="/admin/v9-performance"'
    position = text.find(marker)
    if position >= 0:
        end = text.find('</a>', position)
        text = text[:end + 4] + nav + text[end + 4:]
    else:
        text += '\n<!-- V10 Release: /admin/v10-release -->\n'
    path.write_text(text, encoding='utf-8')


def main() -> int:
    patch_main()
    patch_menu()
    print('V10.0 Release Candidate entegrasyonu tamamlandı.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
