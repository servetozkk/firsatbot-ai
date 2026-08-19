# V23.63.02

V23.63.01 Turkcell Pasaj discovery and scraper were present in the primary scraper registry, but the runtime binding path uses `app.services.scraper_registry`. That duplicate registry did not include Turkcell Pasaj and raised `UnsupportedStoreError`.

V23.63.02 converges the runtime registry only. Discovery, canonical identity, color/network/storage gates, price integrity, Amazon, N11 and Idefix behavior are preserved.
