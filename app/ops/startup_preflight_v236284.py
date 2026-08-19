from __future__ import annotations
import socket

def main() -> int:
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); s.settimeout(0.35)
    try:
        busy = s.connect_ex(("127.0.0.1",8000)) == 0
    finally:
        s.close()
    if busy:
        print("KRITIK: 127.0.0.1:8000 zaten kullaniliyor. Eski FirsatAI/Python sunucusunu kapatip tekrar deneyin.")
        return 2
    print("V23.62.87 STARTUP PREFLIGHT: port 8000 serbest.")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
