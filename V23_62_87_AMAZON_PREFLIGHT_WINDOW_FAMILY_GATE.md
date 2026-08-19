# FirsatAI v23.62.87

- Preserves v23.62.86 runtime/DB/security behavior.
- Amazon phone search now passes up to 8 ranked candidates into the cheap title preflight before the generic 3-detail cap.
- Title preflight rejects explicit family/generation mismatch (e.g. Redmi Note 14 vs Redmi Note 15), variant mismatch (Pro vs Pro+), and explicit storage mismatch before browser/scraper.
- Only the first preflight-compatible candidate may enter the expensive Amazon scraper path.
