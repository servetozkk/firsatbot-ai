from __future__ import annotations

import html as html_module
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit


@dataclass(frozen=True, slots=True)
class StoreAdapter:
    code: str
    selectors: tuple[str, ...]
    excluded_exact_paths: tuple[str, ...] = ()
    excluded_path_tokens: tuple[str, ...] = ()
    html_href_patterns: tuple[str, ...] = ()

    def accept_url(self, url: str) -> bool:
        path = (urlsplit(str(url or "")).path or "/").casefold()
        if path in self.excluded_exact_paths:
            return False
        return not any(token in path for token in self.excluded_path_tokens)

    def normalize_label(self, label: str) -> str:
        return " ".join(str(label or "").split())

    def _decode_context(self, value: str) -> str:
        text = html_module.unescape(str(value or ""))
        text = text.replace(r"\/", "/")
        text = text.replace(r"\u002F", "/").replace(r"\u002f", "/")
        text = text.replace(r"\u0026", "&")
        text = text.replace(r'\"', '"').replace(r"\'", "'")

        def unicode_replace(match: re.Match[str]) -> str:
            try:
                return chr(int(match.group(1), 16))
            except (ValueError, OverflowError):
                return " "

        text = re.sub(r"\\u([0-9a-fA-F]{4})", unicode_replace, text)
        return text

    def _context_label(self, snippet: str, absolute_url: str) -> str:
        decoded = self._decode_context(snippet)
        values: list[str] = []

        key_pattern = re.compile(
            r"(?is)[\"'](?:productName|product_name|name|title|displayName|"
            r"seoTitle|alt|aria-label|description|model|modelName)[\"']"
            r"\s*[:=]\s*[\"'](?P<value>.{2,500}?)(?<!\\)[\"']"
        )
        for match in key_pattern.finditer(decoded):
            value = self._decode_context(match.group("value"))
            value = re.sub(r"<[^>]+>", " ", value)
            value = re.sub(r"\s+", " ", value).strip()
            if value and value not in values:
                values.append(value)

        attr_pattern = re.compile(
            r"(?is)(?:title|alt|aria-label|data-product-name)\s*=\s*"
            r"[\"'](?P<value>.{2,500}?)[\"']"
        )
        for match in attr_pattern.finditer(decoded):
            value = self._decode_context(match.group("value"))
            value = re.sub(r"<[^>]+>", " ", value)
            value = re.sub(r"\s+", " ", value).strip()
            if value and value not in values:
                values.append(value)

        visible = re.sub(r"<script[^>]*>", " ", decoded, flags=re.I)
        visible = re.sub(r"</script>", " ", visible, flags=re.I)
        visible = re.sub(r"<style[^>]*>.*?</style>", " ", visible, flags=re.I | re.S)
        visible = re.sub(r"<[^>]+>", " ", visible)
        visible = re.sub(r"\\[nrt]", " ", visible)
        visible = re.sub(r"\s+", " ", visible).strip()

        path = urlsplit(absolute_url).path
        slug = re.sub(r"[-_/]+", " ", path)
        slug = re.sub(r"\b(?:dp|gp|product|urun|tr)\b", " ", slug, flags=re.I)
        slug = re.sub(r"\s+", " ", slug).strip()

        combined = " ".join(values[:18] + [slug, visible[:4200]])
        return self.normalize_label(combined[:7000])

    def html_candidates(self, page_html: str, base_url: str) -> list[dict[str, str]]:
        """DOM yetersizse hydration/ham HTML içinden URL ve ürün bağlamı çıkar."""
        source = self._decode_context(page_html)
        candidates: list[dict[str, str]] = []
        seen: set[str] = set()

        for pattern in self.html_href_patterns:
            for match in re.finditer(pattern, source, flags=re.IGNORECASE):
                raw_url = match.groupdict().get("url") or match.group(1)
                raw_url = self._decode_context(str(raw_url or ""))
                absolute_url = urljoin(base_url, raw_url)
                if absolute_url in seen or not self.accept_url(absolute_url):
                    continue

                seen.add(absolute_url)
                start = max(0, match.start() - 2600)
                end = min(len(source), match.end() + 3600)
                snippet = source[start:end]
                candidates.append(
                    {
                        "href": absolute_url,
                        "label": self._context_label(snippet, absolute_url),
                    }
                )
        return candidates

    @property
    def extraction_javascript(self) -> str:
        return r"""
        elements => elements.map(element => {
            const card = element.closest(
                'article, li, [data-component-type="s-search-result"], '
                + '[data-testid*="product"], [class*="product"], '
                + '[class*="Product"], [class*="card"], [class*="Card"], '
                + '[data-asin], [data-product-id], [data-product-number]'
            );
            const anchors = [
                element.matches?.('a[href]') ? element : null,
                element.closest?.('a[href]'),
                element.querySelector?.('a[href]'),
                card?.querySelector?.('a[href]')
            ].filter(Boolean);
            const anchor = anchors[0];
            const image = element.querySelector?.('img') || card?.querySelector?.('img');
            const heading = card?.querySelector?.(
                'h1, h2, h3, h4, [class*="title"], '
                + '[class*="Title"], [data-testid*="title"], '
                + '[data-test*="title"], [itemprop="name"]'
            );
            const rawHref = [
                anchor?.href,
                anchor?.getAttribute?.('href'),
                element.getAttribute?.('data-product-url'),
                element.getAttribute?.('data-url'),
                element.getAttribute?.('data-href'),
                card?.getAttribute?.('data-product-url'),
                card?.getAttribute?.('data-url'),
                card?.getAttribute?.('data-href')
            ].find(value => value && !String(value).startsWith('javascript:')) || '';
            return {
                href: rawHref,
                label: [
                    element.innerText || '',
                    element.textContent || '',
                    element.getAttribute?.('title') || '',
                    element.getAttribute?.('aria-label') || '',
                    anchor?.innerText || '',
                    anchor?.getAttribute?.('title') || '',
                    anchor?.getAttribute?.('aria-label') || '',
                    image?.getAttribute?.('alt') || '',
                    image?.getAttribute?.('title') || '',
                    heading?.innerText || '',
                    heading?.textContent || '',
                    card?.innerText || '',
                    card?.textContent || ''
                ].join(' ').replace(/\s+/g, ' ').trim().slice(0, 3200)
            };
        }).filter(item => item.href)
        """
