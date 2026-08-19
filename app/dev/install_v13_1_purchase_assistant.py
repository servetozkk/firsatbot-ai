from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TPL = ROOT / 'app' / 'templates' / 'product_group_detail_v4.html'
MARK = '<div class="ai-actions">'
BLOCK = '''                    <div class="ai-v131-plan">
                        <div class="ai-v131-plan-head"><strong>Karar planı</strong><span>{{ purchase_assistant.decision_consistency }}</span></div>
                        <div class="ai-v131-plan-grid">
                            <div><small>Önerilen zaman</small><strong>{{ purchase_assistant.timing }}</strong></div>
                            <div><small>Veri kalitesi</small><strong>{{ purchase_assistant.data_quality }}</strong></div>
                        </div>
                        <p>{{ purchase_assistant.primary_action }}</p>
                        <small>{{ purchase_assistant.data_quality_note }}</small>
                    </div>

'''
CSS = '''
.ai-v131-plan{margin-top:14px;padding:14px;border:1px solid #dbeafe;border-radius:16px;background:linear-gradient(135deg,#eff6ff,#f8fafc)}
.ai-v131-plan-head{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:10px}.ai-v131-plan-head span{font-size:.68rem;font-weight:900;color:#1d4ed8;background:#dbeafe;padding:5px 8px;border-radius:999px}.ai-v131-plan-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:9px}.ai-v131-plan-grid div{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:9px}.ai-v131-plan-grid small{display:block;color:#64748b;font-size:.62rem;margin-bottom:3px}.ai-v131-plan-grid strong{font-size:.78rem}.ai-v131-plan p{margin:0 0 5px;font-weight:800;color:#0f172a}.ai-v131-plan>small{color:#64748b}@media(max-width:640px){.ai-v131-plan-grid{grid-template-columns:1fr}}
'''

def main():
    text = TPL.read_text(encoding='utf-8')
    if 'ai-v131-plan' not in text:
        if MARK not in text:
            raise SystemExit('template marker bulunamadı')
        text = text.replace(MARK, BLOCK + MARK, 1)
    if CSS.strip() not in text:
        pos = text.rfind('</style>')
        if pos != -1:
            text = text[:pos] + CSS + text[pos:]
        else:
            text += '<style>' + CSS + '</style>'
    TPL.write_text(text, encoding='utf-8')
    print('OK  v13.1 karar planı ürün detay sayfasına eklendi')

if __name__ == '__main__':
    main()
