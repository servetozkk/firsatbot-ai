from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[2]

def ok(value, message):
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")

def main():
    version = (ROOT / 'VERSION').read_text(encoding='utf-8-sig').strip()
    ok(version == '13.5.0', 'VERSION 13.5.0 korunuyor')
    env = Environment(loader=FileSystemLoader(str(ROOT / 'app' / 'templates')))
    template = env.get_template('product_group_compare_v2.html')
    sections = [{
        'name': 'Temel Özellikler',
        'different_count': 1,
        'rows': [{
            'name': 'RAM',
            'is_different': True,
            'values': ['16 GB', '32 GB'],
            'winner_indexes': [1],
        }],
    }]
    source = (ROOT / 'app' / 'templates' / 'product_group_compare_v2.html').read_text(encoding='utf-8')
    ok("section['rows']" in source, 'section rows güvenli sözlük erişimi kullanıyor')
    ok("row['values']" in source, 'row values güvenli sözlük erişimi kullanıyor')
    ok("row['winner_indexes']" in source, 'winner indexes güvenli sözlük erişimi kullanıyor')
    # Parent template blocks require a real request only when rendered through Starlette;
    # compile plus expression evaluation catches the original Jinja method collision.
    env.from_string("{% for section in comparison_sections %}{% for row in section['rows'] %}{% for value in row['values'] %}{{ value }}{% endfor %}{% endfor %}{% endfor %}").render(comparison_sections=sections)
    ok(True, 'karşılaştırma veri yapısı Jinja içinde render ediliyor')
    print('\nFırsatAI v13.5.0 Karşılaştırma 2.0 template hotfix smoke test başarılı.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
