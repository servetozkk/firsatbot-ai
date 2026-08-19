# FırsatAI v23.62.49 — Rolling Window Regression Alarm Correctness Hotfix

Scraping davranışı değiştirilmez. v23.62.48 soak telemetry korunur.

Düzeltme: stability_status artık sadece son koşul/son 5 koşula göre PASS olamaz. 50 koşuluk rolling pencerede herhangi bir koşul baseline kontratını ihlal ediyorsa ALERT kalır; ihlal ancak doğal olarak pencereden çıktığında temizlenir.

Yeni alanlar: contract_pass_run_count, contract_violation_run_count, contract_violation_runs.
