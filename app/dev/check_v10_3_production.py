from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from app.services.production_security_service import production_security_report, write_security_report

def main():
    report=production_security_report(); path=write_security_report()
    print('DURUM:',report['status']); print('KRİTİK:',report['critical_count']); print('UYARI:',report['warning_count']); print('RAPOR:',path)
    return 1 if report['status']=='BLOCKED' else 0
if __name__=='__main__': raise SystemExit(main())
