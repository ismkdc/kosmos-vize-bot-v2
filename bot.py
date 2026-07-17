import time
import json
import os
import base64
from datetime import datetime, timedelta
from enum import Enum
from curl_cffi import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# ── AES decryption ────────────────────────────────────────────────────────────
_KEY_RAW = "aRöÜ@9/*½&7&$£]_?/ç".encode('utf-8')
_KEY = _KEY_RAW + b'\x00' * (-len(_KEY_RAW) % 4)  # 23 → 24 byte (AES-192)
_IV  = b'0' * 16

def decrypt(b64_text):
    cipher = AES.new(_KEY, AES.MODE_CBC, _IV)
    return unpad(cipher.decrypt(base64.b64decode(b64_text)), 16).decode('utf-8')

# ── Enums ──────────────────────────────────────────────────────────────────────
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
CHECK_DAYS = 60       # how many days ahead to check
POLL_INTERVAL = 600   # check interval in seconds (10 min)
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


# ── Token management ──────────────────────────────────────────────────────────
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
    """First request to main site for CF clearance."""
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


# ── Telegram ───────────────────────────────────────────────────────────────────
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
    /token JWT  → get token directly (no SMS required)
    /sms CODE   → get SMS code, obtain token from backend
    """
    send_telegram(
        "Token has expired.\n\n"
        "Option 1 - Without SMS (recommended):\n"
        "1. Log in at basvuru.kosmosvize.com.tr\n"
        "2. F12 → Console: localStorage.getItem('Yh71OoPMuBY8T50ocWvJFw')\n"
        "3. Send to bot: /token YOUR_JWT_HERE\n\n"
        "Option 2 - With SMS:\n"
        "SMS being sent... Once received: /sms YOUR_CODE"
    )
    # Send SMS in background
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
    print("[auth] Token invalid, waiting for renewal...")
    kind, value = wait_for_auth_input()

    if kind == 'token':
        if is_token_valid(value):
            save_token(value)
            send_telegram("Token saved, bot is running.")
            return value
        else:
            send_telegram("Invalid/expired token. Try again.")
            return None

    # kind == 'sms'
    token = validate_sms(value)
    if token:
        save_token(token)
        send_telegram("Login successful, bot is running.")
    else:
        send_telegram("Wrong code, trying again...")
    return token


# ── Main query: GetClosedDate (single request, full date range) ──────────────
def get_closed_dates(token, apt_type):
    """
    Returns closed dates. Dates outside the returned list = available.
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
            print(f"[rate limit] waiting {wait}s...")
            time.sleep(wait + 2)
            continue
        if r.status_code == 200 and r.text.strip():
            try:
                raw = json.loads(decrypt(r.text.strip()))
                # API returns ISO 8601: "2026-06-23T00:00:00+03:00" → "2026-06-23"
                dates = {d[:10] for d in raw}
                return dates, False
            except Exception as e:
                print(f"[decrypt] {e} | raw: {r.text[:80]}")
        return set(), False


def token_expiry(token):
    """JWT exp timestamp, 0 on error."""
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        return json.loads(base64.b64decode(payload)).get('exp', 0)
    except Exception:
        return 0


# ── Main loop ─────────────────────────────────────────────────────────────────
send_telegram("Bot started, appointment tracking begins.")
token = load_token()
prev_closed = {apt.name: None for apt in APPOINTMENT_TYPES}
warned_expiry = False  # send 24h warning only once

while True:
    if not is_token_valid(token):
        token = reauth()
        warned_expiry = False
        if not token:
            time.sleep(60)
            continue

    # warn 24 hours before expiry
    exp = token_expiry(token)
    if not warned_expiry and 0 < exp - time.time() < 86400:
        send_telegram(
            f"Token will expire in approximately {int((exp - time.time()) / 3600)}h.\n"
            "You can renew it with /token or /sms when ready."
        )
        warned_expiry = True

    token_expired = False

    for apt_type in APPOINTMENT_TYPES:
        closed, expired = get_closed_dates(token, apt_type)

        if expired:
            print("[auth] 401 - token expired")
            token = None
            token_expired = True
            break

        if closed is None:
            continue

        today    = datetime.now().strftime('%Y-%m-%d')
        end_date = min(datetime.now() + timedelta(days=CHECK_DAYS), datetime(2026, 8, 1))
        all_days = set()
        d = datetime.now() + timedelta(days=1)  # skip today
        while d <= end_date:
            all_days.add(d.strftime('%Y-%m-%d'))
            d += timedelta(days=1)
        available = sorted(all_days - closed)

        prev = prev_closed[apt_type.name]
        if prev is None:
            # First run - set baseline, don't notify
            prev_closed[apt_type.name] = closed
            print(f"[{apt_type.name}] Baseline: {len(closed)} closed, {len(available)} available")
        else:
            # Newly available dates (previously closed, now open)
            newly_available = sorted((prev - closed) & all_days)
            if newly_available:
                msg = f"Appointment opened! ({apt_type.name})\n" + "\n".join(newly_available)
                send_telegram(msg)
                print(f"[{apt_type.name}] NEWLY AVAILABLE: {newly_available}")
            prev_closed[apt_type.name] = closed

        if available:
            print(f"[{apt_type.name}] Currently available: {available}")

        time.sleep(2)  # short delay between types

    if not token_expired:
        print(f"[loop] {datetime.now().strftime('%H:%M:%S')} - waiting {POLL_INTERVAL}s")
        time.sleep(POLL_INTERVAL)
