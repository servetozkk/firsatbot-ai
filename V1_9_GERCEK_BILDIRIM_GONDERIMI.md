# v1.9 Gerçek Bildirim Gönderimi

## Özellikler
- Kalıcı e-posta ve tarayıcı bildirim kuyruğu
- Kanal başına tekrar gönderim engeli
- Sessiz saatlere göre erteleme
- SMTP ile e-posta gönderimi
- Tarayıcı Notification API ile masaüstü bildirimi
- Başarılı, tekrar denenecek ve başarısız gönderim geçmişi

## SMTP ortam değişkenleri
```
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_FROM_EMAIL=...
SMTP_FROM_NAME=Fırsat AI
SMTP_USE_TLS=1
PUBLIC_BASE_URL=http://127.0.0.1:8000
```

Kuyruğu elle işlemek için:
```powershell
python -m app.process_notification_queue
```
