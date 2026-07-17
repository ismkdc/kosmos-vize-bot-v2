# Kosmos Visa Bot v2

A Python bot that automatically tracks available appointment dates in the Kosmos Visa appointment system and sends notifications via Telegram.

## Features

- **AES encrypted API support** - Automatically decrypts Kosmos's encrypted responses
- **SMS verification login** - Log in using the SMS code sent to your phone number
- **JWT Token management** - Tracks token expiry, requests renewal via Telegram when expired
- **Direct token login** - Get the token from browser localStorage and send it with the `/token` command
- **60-day calendar** - Checks appointments up to 60 days ahead
- **Standard + VIP appointment** - Tracks both appointment types simultaneously
- **New available date detection** - Sets a baseline on first run, then only reports **newly opened** dates on subsequent checks
- **Rate-limit protection** - Automatically waits when a 429 error is received
- **Apple Shortcut integration** - iOS shortcut to forward SMS codes to Telegram
- **Docker support** - Easy deployment with Docker

## Requirements

- Python 3.12+
- `curl_cffi` and `pycryptodome` libraries

```bash
pip install curl_cffi pycryptodome
```

## Usage

### 1. Configuration

Edit the following values in `bot.py`:

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (get from BotFather) |
| `CHAT_IDS` | Telegram chat IDs to receive notifications |
| `PEOPLE` | TCKN and passport numbers |
| `DEALER_ID` | Dealer ID |
| `APPLICATION_TYPE` | `INDIVIDUAL` or `FAMILY` |
| `APPOINTMENT_TYPES` | `[STANDARD, VIP]` - which types to track |
| `CHECK_DAYS` | How many days ahead to check (default: 60) |
| `POLL_INTERVAL` | Check interval in seconds (default: 600 = 10 min) |

### 2. Running

**Directly with Python:**
```bash
python bot.py
```

**With Docker:**
```bash
docker compose up -d
```

### 3. Authentication

On first run, the bot will present you with two options via Telegram:

**Option 1 - With Token (recommended):**
1. Log in at `basvuru.kosmosvize.com.tr`
2. F12 → Console: `localStorage.getItem('Yh71OoPMuBY8T50ocWvJFw')`
3. Send the JWT token to the bot: `/token YOUR_JWT_HERE`

**Option 2 - With SMS:**
The bot will send you an SMS. Reply with the code using `/sms YOUR_CODE`.

## License

MIT
