from app.services.beta_readiness_service import build_beta_readiness, REPORT_PATH

def main():
    report=build_beta_readiness(write_report=True)
    for name,item in report['modules'].items():
        print(('OK  ' if item['status']=='ok' else 'HATA  ')+name)
    print(f"OK  SQLite integrity: {report['database']['integrity']}")
    print(f"OK  Foreign key ihlali: {report['database']['foreign_key_violations']}")
    print(f"BILGI  Route: {report['source_metrics']['routes']}")
    print(f"BILGI  API: {report['source_metrics']['api_routes']}")
    print(f"DURUM: {report['status']}")
    print(f"RAPOR: {REPORT_PATH}")
    return 0 if report['status']=='BETA_READY' else 1
if __name__=='__main__': raise SystemExit(main())
