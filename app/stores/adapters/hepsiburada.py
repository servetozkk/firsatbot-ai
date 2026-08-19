from __future__ import annotations

from app.stores.adapters.base import StoreAdapter


class HepsiburadaAdapter(StoreAdapter):
    @property
    def extraction_javascript(self) -> str:
        return r"""
        elements => elements.map(element => {
            const card = element.matches?.(
                '[data-test-id="product-card"], [data-testid="product-card"], '
                + '[data-test-id*="product-card"], [data-testid*="product-card"], '
                + '[class*="productCard"], [class*="ProductCard"], '
                + 'li[class*="product"], article[class*="product"]'
            ) ? element : (
                element.closest?.(
                    '[data-test-id="product-card"], [data-testid="product-card"], '
                    + '[data-test-id*="product-card"], [data-testid*="product-card"], '
                    + '[class*="productCard"], [class*="ProductCard"], '
                    + 'li[class*="product"], article[class*="product"]'
                ) || element.closest?.('li, article, div')
            );

            const anchors = [
                element.matches?.('a[href*="-p-"], a[href*="-pm-"]') ? element : null,
                element.querySelector?.('a[href*="-p-"], a[href*="-pm-"]'),
                card?.querySelector?.('a[href*="-p-"], a[href*="-pm-"]'),
                element.closest?.('a[href*="-p-"], a[href*="-pm-"]')
            ].filter(Boolean);
            const anchor = anchors[0];
            if (!anchor) return {href: '', label: ''};

            const titleNode =
                card?.querySelector?.(
                    '[data-test-id*="product-name"], [data-testid*="product-name"], '
                    + '[class*="productName"], [class*="ProductName"], '
                    + 'h2, h3, h4'
                );
            const image = card?.querySelector?.('img');

            const exactCurrentSelectors = [
                '[data-test-id="price-current-price"]',
                '[data-testid="price-current-price"]',
                '[data-test-id*="current-price"]',
                '[data-testid*="current-price"]',
                '[class*="currentPrice"]',
                '[class*="CurrentPrice"]'
            ];
            let priceNodes = [];
            let matchedCurrentPriceSelector = '';
            for (const selector of exactCurrentSelectors) {
                const nodes = [...(card?.querySelectorAll?.(selector) || [])];
                if (nodes.length) {
                    priceNodes = nodes;
                    matchedCurrentPriceSelector = selector;
                    break;
                }
            }
            if (!priceNodes.length) {
                priceNodes = [
                    ...(card?.querySelectorAll?.(
                        '[data-test-id*="price"], [data-testid*="price"], '
                        + '[class*="price"], [class*="Price"]'
                    ) || [])
                ].slice(0, 12);
            }

            const semanticPrices = [];
            const priceProvenance = [];
            const rejectRole = /(indirim|kazanç|kazanc|kupon|puan|taksit|ayda|sepette|kampanya|avantaj|%|rating|review|yorum)/i;
            const oldRole = /(old|original|strike|cross|list-price|before-discount)/i;
            const trustedRole = /(current|sale|selling|final)/i;

            // V23.25: every structured value carries provenance.
            // Generic "data-price"/"price" is NOT trusted unless its DOM role
            // explicitly says current/sale/selling/final.
            const structuredCandidates = [];
            const structuredSelectors = [
                '[data-current-price]',
                '[data-sale-price]',
                '[data-selling-price]',
                '[data-final-price]',
                '[itemprop="price"]',
                'meta[itemprop="price"]',
                '[data-price]'
            ];

            const normalizeStructuredPrice = raw => {
                const text = String(raw ?? '').trim();
                if (!text) return null;
                const cleaned = text.replace(/[^\d.,]/g, '');
                if (!cleaned) return null;
                let normalized = cleaned;
                if (normalized.includes(',')) {
                    normalized = normalized.replace(/\./g, '').replace(',', '.');
                } else {
                    const dotCount = (normalized.match(/\./g) || []).length;
                    // V23.62.76: Turkish visible prices use a dot as thousands
                    // separator even when there is only one group (21.499 TL).
                    // Treat exactly three trailing digits as thousands, while
                    // preserving decimal-like values such as 21.49.
                    if (dotCount > 1 || (
                        dotCount === 1
                        && normalized.split('.').pop().length === 3
                    )) {
                        normalized = normalized.replace(/\./g, '');
                    }
                }
                const num = Number(normalized);
                if (!Number.isFinite(num) || num < 20 || num > 2000000) return null;
                return num;
            };

            const pushCandidate = (value, source, role, trusted) => {
                if (value === null) return;
                const record = {
                    value,
                    source: String(source || ''),
                    role: String(role || ''),
                    trusted: Boolean(trusted)
                };
                const key = `${record.value}|${record.source}|${record.role}|${record.trusted}`;
                if (!structuredCandidates.some(item =>
                    `${item.value}|${item.source}|${item.role}|${item.trusted}` === key
                )) structuredCandidates.push(record);
            };

            for (const selector of structuredSelectors) {
                for (const node of (card?.querySelectorAll?.(selector) || [])) {
                    const roleContext = [
                        node.getAttribute?.('data-test-id') || '',
                        node.getAttribute?.('data-testid') || '',
                        node.getAttribute?.('class') || '',
                        node.getAttribute?.('aria-label') || '',
                        node.parentElement?.getAttribute?.('data-test-id') || '',
                        node.parentElement?.getAttribute?.('data-testid') || '',
                        node.parentElement?.getAttribute?.('class') || '',
                        node.parentElement?.getAttribute?.('aria-label') || ''
                    ].join(' ');

                    if (rejectRole.test(roleContext) || oldRole.test(roleContext)) continue;

                    const attrMap = [
                        ['data-current-price', true],
                        ['data-sale-price', true],
                        ['data-selling-price', true],
                        ['data-final-price', true],
                        ['content', node.getAttribute?.('itemprop') === 'price'],
                        ['value', node.getAttribute?.('itemprop') === 'price'],
                        ['data-price', trustedRole.test(roleContext)]
                    ];

                    for (const [attr, intrinsicallyTrusted] of attrMap) {
                        const raw = node.getAttribute?.(attr);
                        const value = normalizeStructuredPrice(raw);
                        if (value === null) continue;
                        const role = `${selector}|${attr}|${roleContext}`.slice(0, 600);
                        pushCandidate(
                            value,
                            `dom-attribute:${attr}`,
                            role,
                            Boolean(intrinsicallyTrusted)
                        );
                    }
                }
            }

            // Same-card JSON/data state. Only explicit semantic CURRENT price keys
            // are trusted. Generic "price" is diagnostic only.
            const cardAttrs = [...(card?.attributes || [])];
            for (const attr of cardAttrs) {
                const attrName = String(attr.name || '');
                const attrValue = String(attr.value || '');
                if (!/^data-/i.test(attrName) || !attrValue || attrValue.length > 12000) continue;
                if (!/(price|sale|selling|offer|current|final)/i.test(attrName + ' ' + attrValue)) continue;
                try {
                    const parsed = JSON.parse(attrValue);
                    const stack = [{value: parsed, path: attrName}];
                    while (stack.length) {
                        const entry = stack.pop();
                        const item = entry.value;
                        if (!item || typeof item !== 'object') continue;
                        for (const [key, val] of Object.entries(item)) {
                            const path = `${entry.path}.${key}`;
                            if (/(old|original|list|discount|coupon|installment|rating|review)/i.test(key)) continue;

                            if (/^(currentPrice|salePrice|sellingPrice|finalPrice)$/i.test(key)) {
                                pushCandidate(
                                    normalizeStructuredPrice(val),
                                    `card-json:${path}`,
                                    key,
                                    true
                                );
                            } else if (/^price$/i.test(key)) {
                                pushCandidate(
                                    normalizeStructuredPrice(val),
                                    `card-json:${path}`,
                                    key,
                                    false
                                );
                            } else if (val && typeof val === 'object') {
                                stack.push({value: val, path});
                            }
                        }
                    }
                } catch (_) {}
            }

            // V23.28: fallback ONLY from an exact semantic current-price DOM role.
            // Generic price containers remain diagnostic and are never trusted.
            const explicitCurrencyPrice = raw => {
                const text = String(raw || '').replace(/\s+/g, ' ').trim();
                const matches = text.match(
                    /(?:₺\s*)?\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?\s*(?:TL|₺)|(?:₺\s*)?\d{2,7}(?:[.,]\d{1,2})?\s*(?:TL|₺)/gi
                ) || [];
                const values = [];
                for (const match of matches) {
                    const value = normalizeStructuredPrice(match);
                    if (value !== null && !values.includes(value)) values.push(value);
                }
                return values;
            };

            if (matchedCurrentPriceSelector && priceNodes.length) {
                for (const node of priceNodes) {
                    const nodeText = String(node.innerText || node.textContent || '')
                        .replace(/\s+/g, ' ')
                        .trim();
                    const roleContext = [
                        matchedCurrentPriceSelector,
                        node.getAttribute?.('data-test-id') || '',
                        node.getAttribute?.('data-testid') || '',
                        node.getAttribute?.('class') || '',
                        node.getAttribute?.('aria-label') || '',
                        node.parentElement?.getAttribute?.('data-test-id') || '',
                        node.parentElement?.getAttribute?.('data-testid') || '',
                        node.parentElement?.getAttribute?.('class') || ''
                    ].join(' ');

                    if (rejectRole.test(roleContext) || oldRole.test(roleContext)) continue;

                    // Prefer the smallest descendants with an explicit currency token.
                    const currencyLeaves = [
                        ...(node.querySelectorAll?.('*') || [])
                    ].filter(child => {
                        const text = String(child.innerText || child.textContent || '')
                            .replace(/\s+/g, ' ')
                            .trim();
                        if (!/(?:TL|₺)/i.test(text)) return false;
                        return ![...(child.children || [])].some(grand =>
                            /(?:TL|₺)/i.test(
                                String(grand.innerText || grand.textContent || '')
                            )
                        );
                    });

                    const sources = currencyLeaves.length ? currencyLeaves : [node];
                    for (const sourceNode of sources) {
                        const sourceText = String(
                            sourceNode.innerText || sourceNode.textContent || ''
                        ).replace(/\s+/g, ' ').trim();

                        const sourceRole = [
                            sourceNode.getAttribute?.('data-test-id') || '',
                            sourceNode.getAttribute?.('data-testid') || '',
                            sourceNode.getAttribute?.('class') || '',
                            sourceNode.getAttribute?.('aria-label') || '',
                            roleContext
                        ].join(' ');

                        if (rejectRole.test(sourceRole) || oldRole.test(sourceRole)) continue;

                        const values = explicitCurrencyPrice(sourceText);
                        // One semantic current-price leaf must express exactly one price.
                        if (values.length === 1) {
                            pushCandidate(
                                values[0],
                                'dom-semantic-current-text',
                                `${matchedCurrentPriceSelector}|${sourceRole}|text=${sourceText}`.slice(0, 900),
                                true
                            );
                        } else if (values.length > 1) {
                            for (const value of values) {
                                pushCandidate(
                                    value,
                                    'dom-semantic-current-text-ambiguous',
                                    `${matchedCurrentPriceSelector}|${sourceRole}|text=${sourceText}`.slice(0, 900),
                                    false
                                );
                            }
                        }
                    }
                }
            }

            // V23.29: capture exact DOM provenance for every numeric/currency-looking
            // price candidate in the SAME product card. Diagnostic only; does not alter trust.
            const priceNodeDiagnostics = [];
            const diagnosticNodes = [
                ...(card?.querySelectorAll?.(
                    '[data-test-id*="price"], [data-testid*="price"], '
                    + '[class*="price"], [class*="Price"], '
                    + '[data-price], [data-current-price], [data-sale-price], '
                    + '[data-selling-price], [data-final-price], [itemprop="price"]'
                ) || [])
            ].slice(0, 80);

            for (const node of diagnosticNodes) {
                const text = String(node.innerText || node.textContent || '')
                    .replace(/\s+/g, ' ')
                    .trim();
                if (!text || !/\d/.test(text)) continue;

                const values = [];
                const explicit = explicitCurrencyPrice(text);
                for (const value of explicit) {
                    if (!values.includes(value)) values.push(value);
                }

                const attrsToProbe = [
                    'data-price','data-current-price','data-sale-price',
                    'data-selling-price','data-final-price','content','value'
                ];
                for (const attr of attrsToProbe) {
                    const parsed = normalizeStructuredPrice(node.getAttribute?.(attr));
                    if (parsed !== null && !values.includes(parsed)) values.push(parsed);
                }

                if (!values.length) continue;

                for (const value of values) {
                    priceNodeDiagnostics.push({
                        value,
                        tag: String(node.tagName || ''),
                        class_name: String(node.getAttribute?.('class') || '').slice(0, 500),
                        data_test_id: String(
                            node.getAttribute?.('data-test-id')
                            || node.getAttribute?.('data-testid')
                            || ''
                        ).slice(0, 500),
                        aria_label: String(node.getAttribute?.('aria-label') || '').slice(0, 500),
                        text: text.slice(0, 900),
                        parent_tag: String(node.parentElement?.tagName || ''),
                        parent_class: String(node.parentElement?.getAttribute?.('class') || '').slice(0, 500),
                        parent_data_test_id: String(
                            node.parentElement?.getAttribute?.('data-test-id')
                            || node.parentElement?.getAttribute?.('data-testid')
                            || ''
                        ).slice(0, 500),
                        parent_text: String(
                            node.parentElement?.innerText
                            || node.parentElement?.textContent
                            || ''
                        ).replace(/\s+/g, ' ').trim().slice(0, 1200)
                    });
                }
            }

            // V23.30: production trust for Hepsiburada final-price node confirmed by v23.29 diagnostics.
            // Accept ONLY full-price nodes, never coupon text or fraction-only children.
            const finalPriceNodes = [
                ...(card?.querySelectorAll?.(
                    '[data-test-id^="final-price"], [data-testid^="final-price"], '
                    + '[class*="finalPrice"], [class*="FinalPrice"]'
                ) || [])
            ];

            for (const node of finalPriceNodes) {
                const nodeText = String(node.innerText || node.textContent || '')
                    .replace(/\s+/g, ' ')
                    .trim();

                const className = String(node.getAttribute?.('class') || '');
                const testId = String(
                    node.getAttribute?.('data-test-id')
                    || node.getAttribute?.('data-testid')
                    || ''
                );

                // Fraction nodes such as ",90 TL" are never full prices.
                if (/fraction/i.test(className) || /fraction/i.test(testId)) continue;

                // Require the complete visible price with integer part and currency.
                if (!/(?:TL|₺)/i.test(nodeText)) continue;
                if (!/\d{1,7}(?:[.,]\d{1,2})?\s*(?:TL|₺)/i.test(nodeText)) continue;
                if (/^[,\.]\d{1,2}\s*(?:TL|₺)$/i.test(nodeText)) continue;

                const values = explicitCurrencyPrice(nodeText);
                if (values.length !== 1) continue;

                const roleContext = [
                    className,
                    testId,
                    String(node.parentElement?.getAttribute?.('class') || ''),
                    String(
                        node.parentElement?.getAttribute?.('data-test-id')
                        || node.parentElement?.getAttribute?.('data-testid')
                        || ''
                    )
                ].join(' ');

                // Kupon/indirim/puan/taksit bağlamında final-price güveni verme.
                if (rejectRole.test(roleContext) || rejectRole.test(nodeText)) continue;
                if (oldRole.test(roleContext)) continue;

                pushCandidate(
                    values[0],
                    'dom-hepsiburada-final-price',
                    `final-price|${testId}|${className}|text=${nodeText}`.slice(0, 900),
                    true
                );
            }

            const trustedCandidates = structuredCandidates.filter(item => item.trusted);
            const trustedValues = [...new Set(trustedCandidates.map(item => item.value))];

            // Keep provenance visible in logs without making generic card text a price source.
            for (const item of structuredCandidates.slice(0, 12)) {
                priceProvenance.push(
                    `V23.25_PROV value=${item.value} trusted=${item.trusted ? 1 : 0} source=${item.source} role=${item.role}`
                );
            }

            const acceptedPrice = trustedValues.length === 1 ? trustedValues[0] : null;
            if (acceptedPrice !== null) {
                semanticPrices.push(`V23.25_ACCEPTED_PRICE=${acceptedPrice}`);
            } else {
                semanticPrices.push(`V23.25_ACCEPTED_PRICE=NONE`);
            }
            const rawHref = anchor.href || anchor.getAttribute?.('href') || '';
            return {
                href: rawHref,
                accepted_price: acceptedPrice,
                price_provenance: structuredCandidates.slice(0, 12),
                price_node_diagnostics: priceNodeDiagnostics.slice(0, 40),
                direct_evidence: acceptedPrice !== null,
                label: [
                    // V23.26: machine-readable evidence MUST precede verbose card text
                    // so slice(0, 4200) can never remove provenance/accepted-price markers.
                    'V23.30_FINAL_PRICE_DIRECT_TRUST',
                    'V23.30_FINAL_PRICE_PROVENANCE',
                    ...priceProvenance,
                    ...semanticPrices,
                    titleNode?.innerText || '',
                    titleNode?.textContent || '',
                    anchor?.innerText || '',
                    anchor?.getAttribute?.('title') || '',
                    anchor?.getAttribute?.('aria-label') || '',
                    image?.getAttribute?.('alt') || '',
                    card?.innerText || ''
                ].join(' ').replace(/\s+/g, ' ').trim().slice(0, 4200)
            };
        }).filter(item => item.href)
        """


HEPSIBURADA_ADAPTER = HepsiburadaAdapter(
    code="hepsiburada",
    selectors=(
        '[data-test-id="product-card"]',
        '[data-testid="product-card"]',
        '[data-test-id*="product-card"]',
        '[data-testid*="product-card"]',
        '[class*="productCard"]',
        '[class*="ProductCard"]',
        'a[href*="-pm-"]',
        'a[href*="-p-"]',
    ),
    excluded_path_tokens=(
        "/ara", "/kategori/", "/magaza/", "/kampanya", "/uyelik",
    ),
    html_href_patterns=(
        r'''["'](?P<url>https?://(?:www\.)?hepsiburada\.com/[^"'<>\s]+-(?:p|pm)-[^"'<>\s]+)["']''',
        r'''["'](?P<url>/[^"'<>\s]+-(?:p|pm)-[^"'<>\s]+)["']''',
    ),
)
