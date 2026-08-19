from app.services.public_beta_service import ensure_schema, public_beta_status

def main():
    ensure_schema()
    report=public_beta_status(write_report=True)
    print("OK  Public Beta semasi hazir")
    print("DURUM:", report["status"])
    print("RAPOR: data/reports/v13_9_0_public_beta.json")
    return 0 if report["status"] == "PUBLIC_BETA_READY" else 1

if __name__ == "__main__": raise SystemExit(main())
