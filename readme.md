# Kosmos Vize Bot v2

Kosmos Vize randevu sisteminde müsait randevu tarihlerini otomatik takip eden ve Telegram üzerinden bildirim gönderen Python botu.

## Özellikler

- **AES şifreli API desteği** - Kosmos'un şifreli yanıtlarını otomatik çözer
- **SMS doğrulama ile giriş** - Telefon numaranıza gelen SMS kodu ile oturum açma
- **JWT Token yönetimi** - Token süresini takip eder, süresi dolunca Telegram'dan yenileme ister
- **Token ile direkt giriş** - Browser'dan localStorage token'ını alıp `/token` komutuyla gönderebilirsiniz
- **60 günlük takvim** - Randevu kontrolünü 60 gün ileriye kadar yapar
- **Standart + VIP randevu** - Her iki randevu tipini aynı anda takip eder
- **Yeni müsait tarih tespiti** - İlk çalışmada baseline alır, sonraki kontrollerde sadece **yeni açılan** tarihleri bildirir
- **Rate-limit koruması** - 429 hatası alınca otomatik bekler
- **Apple Shortcut entegrasyonu** - iOS kısayolu ile SMS kodlarını Telegram'a yönlendirme
- **Docker desteği** - Docker ile kolay çalıştırma

## Gereksinimler

- Python 3.12+
- `curl_cffi` ve `pycryptodome` kütüphaneleri

```bash
pip install curl_cffi pycryptodome
```

## Kullanım

### 1. Konfigürasyon

`bot.py` içindeki şu değerleri kendinize göre ayarlayın:

| Değişken | Açıklama |
|----------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (BotFather'dan alın) |
| `CHAT_IDS` | Bildirim gönderilecek Telegram chat ID'leri |
| `PEOPLE` | TCKN ve pasaport numaraları |
| `DEALER_ID` | Bayi ID'si |
| `APPLICATION_TYPE` | `INDIVIDUAL` veya `FAMILY` |
| `APPOINTMENT_TYPES` | `[STANDARD, VIP]` - hangi tipler takip edilsin |
| `CHECK_DAYS` | Kaç gün ileriye bakılacak (varsayılan: 60) |
| `POLL_INTERVAL` | Kontrol aralığı saniye (varsayılan: 600 = 10 dk) |

### 2. Çalıştırma

**Direkt Python ile:**
```bash
python bot.py
```

**Docker ile:**
```bash
docker compose up -d
```

### 3. Kimlik Doğrulama

İlk çalıştırmada bot size Telegram'dan iki seçenek sunar:

**Seçenek 1 - Token ile (önerilen):**
1. `basvuru.kosmosvize.com.tr` adresinden giriş yapın
2. F12 → Console: `localStorage.getItem('Yh71OoPMuBY8T50ocWvJFw')`
3. Çıkan JWT token'ı bota gönderin: `/token JWT_BURAYA`

**Seçenek 2 - SMS ile:**
Bot size SMS gönderir, gelen kodu `/sms KODUNUZ` şeklinde yanıtlayın.

## Lisans

MIT
