import time
import json
import os
import base64
from datetime import datetime, timedelta
from enum import Enum
from curl_cffi import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# ── AES decrypt ───────────────────────────────────────────────────────────────
_KEY_RAW = "aRöÜ@9/*½&7&$£]_?/ç".encode('utf-8')
_KEY = _KEY_RAW + b'\x00' * (-len(_KEY_RAW) % 4)  # 23 → 24 byte (AES-192)
_IV  = b'0' * 16

def decrypt(b64_text):
    cipher = AES.new(_KEY, AES.MODE_CBC, _IV)
    return unpad(cipher.decrypt(base64.b64decode(b64_text)), 16).decode('utf-8')

# ── Enums ─────────────────────────────────────────────────────────────────────
class ApplicationType(Enum):
    INDIVIDUAL = 1
    FAMILY = 2

class AppointmentTypeId(Enum):
    STANDARD = 16
    VIP = 18

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_IDS = ["YOUR_CHAT_ID"]

PEOPLE = [
    {"tckn": "xxxxxxxxxxx", "passport": "xxxxxxxxxxx"},
]

DEALER_ID = 1
APPLICATION_TYPE = ApplicationType.FAMILY
APPOINTMENT_TYPES = [AppointmentTypeId.STANDARD, AppointmentTypeId.VIP]
CHECK_DAYS = 60       # kaç gün ileriye bakılsın
POLL_INTERVAL = 600   # kaç saniyede bir kontrol (10 dk)
TOKEN_FILE = os.environ.get("TOKEN_FILE", "token.txt")
# ──────────────────────────────────────────────────────────────────────────────

HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'tr,en-US;q=0.9,en;q=0.8',
    'content-type': 'application/json',
    'origin': 'https://basvuru.kosmosvize.com.tr',
    'referer': 'https://basvuru.kosmosvize.com.tr/',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
}


# ── Token yönetimi ────────────────────────────────────────────────────────────
def save_token(token):
    with open(TOKEN_FILE, 'w') as f:
        f.write(token)

def load_token():
    if os.path.exists(TOKEN_FILE):
        t = open(TOKEN_FILE).read().strip()
        return t or None
    return None

def is_token_valid(token):
    if not token:
        return False
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        exp = json.loads(base64.b64decode(payload)).get('exp', 0)
        return exp > time.time() + 300
    except Exception:
        return False


# ── Auth ──────────────────────────────────────────────────────────────────────
def _cf_session():
    """CF clearance için önce ana siteye istek at."""
    s = requests.Session()
    s.get('https://basvuru.kosmosvize.com.tr/', impersonate='chrome')
    return s

def send_sms():
    s = _cf_session()
    r = s.post(
        "https://api.kosmosvize.com.tr/api/Verification/SendSmsVerificationCode",
        headers=HEADERS, json={"people": PEOPLE}, impersonate='chrome'
    )
    print(f"[sms] {r.status_code} {r.text[:100]}")
    return r.status_code == 200

def validate_sms(code):
    s = _cf_session()
    r = s.post(
        "https://api.kosmosvize.com.tr/api/Verification/ValidateSmsCode",
        headers=HEADERS, json={"code": code, "people": PEOPLE}, impersonate='chrome'
    )
    print(f"[validate] {r.status_code} {r.text[:100]}")
    if r.status_code == 200:
        return r.json().get('token')
    return None


# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(message):
    for cid in CHAT_IDS:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": cid, "text": message}, impersonate='chrome'
            )
        except Exception as e:
            print(f"[telegram] {e}")

def get_updates(offset=None):
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
            params={"timeout": 20, "offset": offset}, impersonate='chrome', timeout=25
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[updates] {e}")
    return None

def wait_for_auth_input():
    """
    /token JWT  → direkt token al (SMS gerektirmez)
    /sms KOD    → SMS kodu al, backend'den token al
    """
    send_telegram(
        "Token süresi doldu.\n\n"
        "Seçenek 1 — SMS'siz (önerilen):\n"
        "1. basvuru.kosmosvize.com.tr adresinden giriş yap\n"
        "2. F12 → Console: localStorage.getItem('Yh71OoPMuBY8T50ocWvJFw')\n"
        "3. Bota gönder: /token JWT_BURAYA\n\n"
        "Seçenek 2 — SMS ile:\n"
        "SMS gönderiliyor... Gelince: /sms KODUNUZ"
    )
    # SMS'i arka planda gönder
    send_sms()

    offset = None
    while True:
        updates = get_updates(offset)
        if updates and updates.get('ok'):
            for u in updates['result']:
                offset = u['update_id'] + 1
                text = (u.get('message', {}).get('text', '') or '').strip()
                chat = str(u.get('message', {}).get('chat', {}).get('id', ''))
                if chat not in [str(c) for c in CHAT_IDS]:
                    continue
                if text.lower().startswith('/token '):
                    return ('token', text[7:].strip())
                if text.lower().startswith('/sms '):
                    return ('sms', text[5:].strip())
        time.sleep(2)

def reauth():
    print("[auth] Token geçersiz, yenileme bekleniyor...")
    kind, value = wait_for_auth_input()

    if kind == 'token':
        if is_token_valid(value):
            save_token(value)
            send_telegram("Token kaydedildi, bot çalışıyor.")
            return value
        else:
            send_telegram("Geçersiz/süresi dolmuş token. Tekrar dene.")
            return None

    # kind == 'sms'
    token = validate_sms(value)
    if token:
        save_token(token)
        send_telegram("Giriş başarılı, bot çalışıyor.")
    else:
        send_telegram("Kod yanlış, tekrar deniyor...")
    return token


# ── Ana sorgu: GetClosedDate (tek istek, tüm tarih aralığı) ───────────────────
def get_closed_dates(token, apt_type):
    """
    Kapalı tarihleri döner. Dönen liste dışındaki tarihler = müsait.
    Returns: (set of closed date strings, token_expired bool)
    """
    today    = datetime.now().strftime('%Y-%m-%d')
    check_end = min(datetime.now() + timedelta(days=CHECK_DAYS), datetime(2026, 8, 1))
    max_date  = check_end.strftime('%Y-%m-%d')
    headers  = {**HEADERS, 'authorization': f'Bearer {token}'}

    while True:
        r = requests.get(
            "https://api.kosmosvize.com.tr/api/AppointmentClosedDates/GetClosedDate",
            headers=headers,
            params={'dealerId': DEALER_ID, 'date': today, 'maxDate': max_date,
                    'appointmentTypeId': apt_type.value},
            impersonate='chrome'
        )

        print(f"[{apt_type.name}] GetClosedDate: {r.status_code}")

        if r.status_code == 401:
            return None, True
        if r.status_code == 429:
            try:
                wait = r.json().get('retryAfterSeconds', 60)
            except Exception:
                wait = 60
            print(f"[rate limit] {wait}s bekleniyor...")
            time.sleep(wait + 2)
            continue
        if r.status_code == 200 and r.text.strip():
            try:
                raw = json.loads(decrypt(r.text.strip()))
                # API ISO 8601 döndürür: "2026-06-23T00:00:00+03:00" → "2026-06-23"
                dates = {d[:10] for d in raw}
                return dates, False
            except Exception as e:
                print(f"[decrypt] {e} | raw: {r.text[:80]}")
        return set(), False


def token_expiry(token):
    """JWT exp timestamp, hata varsa 0."""
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        return json.loads(base64.b64decode(payload)).get('exp', 0)
    except Exception:
        return 0


# ── Ana döngü ─────────────────────────────────────────────────────────────────
send_telegram("Bot başladı, randevu takibi başlıyor.")
token = load_token()
prev_closed = {apt.name: None for apt in APPOINTMENT_TYPES}
warned_expiry = False  # 24h uyarısı bir kez gönderilsin

while True:
    if not is_token_valid(token):
        token = reauth()
        warned_expiry = False
        if not token:
            time.sleep(60)
            continue

    # 24 saat kala uyar
    exp = token_expiry(token)
    if not warned_expiry and 0 < exp - time.time() < 86400:
        send_telegram(
            f"Token yaklaşık {int((exp - time.time()) / 3600)}h içinde dolacak.\n"
            "Hazır olunca /token veya /sms ile yenileyebilirsin."
        )
        warned_expiry = True

    token_expired = False

    for apt_type in APPOINTMENT_TYPES:
        closed, expired = get_closed_dates(token, apt_type)

        if expired:
            print("[auth] 401 — token süresi doldu")
            token = None
            token_expired = True
            break

        if closed is None:
            continue

        today    = datetime.now().strftime('%Y-%m-%d')
        end_date = min(datetime.now() + timedelta(days=CHECK_DAYS), datetime(2026, 8, 1))
        all_days = set()
        d = datetime.now() + timedelta(days=1)  # bugünü atla
        while d <= end_date:
            all_days.add(d.strftime('%Y-%m-%d'))
            d += timedelta(days=1)
        available = sorted(all_days - closed)

        prev = prev_closed[apt_type.name]
        if prev is None:
            # İlk çalışma — baseline kur, bildirme
            prev_closed[apt_type.name] = closed
            print(f"[{apt_type.name}] Baseline: {len(closed)} kapalı, {len(available)} müsait")
        else:
            # Yeni müsait olan tarihler (önceki kapalıydı, şimdi açık)
            newly_available = sorted((prev - closed) & all_days)
            if newly_available:
                msg = f"Randevu açıldı! ({apt_type.name})\n" + "\n".join(newly_available)
                send_telegram(msg)
                print(f"[{apt_type.name}] YENİ MÜSAİT: {newly_available}")
            prev_closed[apt_type.name] = closed

        if available:
            print(f"[{apt_type.name}] Şu an müsait: {available}")

        time.sleep(2)  # iki tip arasında kısa bekleme

    if not token_expired:
        print(f"[loop] {datetime.now().strftime('%H:%M:%S')} — {POLL_INTERVAL}s bekleniyor")
        time.sleep(POLL_INTERVAL)
