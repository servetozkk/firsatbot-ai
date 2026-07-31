from pathlib import Path

file_path = Path(
    r"C:\Users\Tekno\Desktop\firsatbot-ai\app\services\browser_engine.py"
)

text = file_path.read_text(encoding="utf-8")

start = text.index("    def _get_or_create_page(")
end = text.index(
    "    @staticmethod\n"
    "    def _get_live_pages(",
    start,
)

new_get_or_create_page = '''    def _get_or_create_page(
        self,
        context: BrowserContext,
        target_url: str,
    ) -> Page:
        pages = self._get_live_pages(context)

        matching_pages = [
            page
            for page in pages
            if self._page_matches_target(
                page=page,
                target_url=target_url,
            )
        ]

        if matching_pages:
            return matching_pages[-1]

        try:
            return context.new_page()
        except PlaywrightError as error:
            raise RuntimeError(
                "Chrome tarayıcı bağlamı kapandı. "
                "Tarayıcı penceresini test bitmeden kapatmayın."
            ) from error

'''

text = (
    text[:start]
    + new_get_or_create_page
    + text[end:]
)

start = text.index("    def _page_matches_target(")
end = text.index(
    "    @staticmethod\n"
    "    def _same_domain(",
    start,
)

new_page_matches_target = '''    def _page_matches_target(
        self,
        page: Page,
        target_url: str,
    ) -> bool:
        page_url = self._read_url(page)

        if not page_url:
            return False

        page_parts = urlsplit(page_url)
        target_parts = urlsplit(target_url)

        page_host = (page_parts.hostname or "").lower()
        target_host = (target_parts.hostname or "").lower()

        if page_host != target_host:
            return False

        page_path = page_parts.path.rstrip("/").lower()
        target_path = target_parts.path.rstrip("/").lower()

        return page_path == target_path

'''

text = (
    text[:start]
    + new_page_matches_target
    + text[end:]
)

file_path.write_text(
    text,
    encoding="utf-8",
)

print("browser_engine.py başarıyla düzeltildi.")
