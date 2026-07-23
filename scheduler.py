import time
import schedule

from main import run


def job():
    print("\n🚀 Yeni tarama başladı...")
    
    run()
    
    print("✅ Tarama tamamlandı.")


# 30 dakikada bir çalıştır
schedule.every(30).minutes.do(job)


print("🤖 Scheduler çalışıyor...")


# İlk açılışta hemen çalıştır
job()


while True:
    schedule.run_pending()
    time.sleep(1)