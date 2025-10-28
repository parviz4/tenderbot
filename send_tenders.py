# pull_and_send_from_email.py
import os, sys, re, json, requests, imaplib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from email import policy
from email.parser import BytesParser

# ---- ENV ----
IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
IMAP_USER = os.environ.get("IMAP_USER")              # e.g. your@outlook.com
IMAP_PASS = os.environ.get("IMAP_PASS")              # password (یا App Password)
IMAP_FROM = os.environ.get("IMAP_FROM", "")          # اختیاری: فیلتر فرستنده
IMAP_SUBJECT_KEY = os.environ.get("IMAP_SUBJECT_KEY", "DAILY_TENDERS_JSON")

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("GROUP_ID")                 # عددی، معمولا -100...
TG_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
TG_MAX = 4096

RUN_AT_PARIS_HOUR = 9  # فقط ۹ صبح پاریس ارسال کند

def now_paris():
    return datetime.now(ZoneInfo("Europe/Paris"))

def should_run_now():
    n = now_paris()
    print(f"ℹ️ Paris now: {n.strftime('%Y-%m-%d %H:%M')}")
    return n.hour == RUN_AT_PARIS_HOUR

def send_telegram(text: str):
    r = requests.post(TG_URL, data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}, timeout=60)
    try:
        data = r.json()
    except Exception:
        data = {"ok": False, "error": r.text}
    ok = r.status_code == 200 and data.get("ok", False)
    print(("✅ Telegram ok" if ok else f"❌ Telegram FAILED: {data}"), file=sys.stderr if not ok else sys.stdout)

def send_long(text: str):
    if len(text) <= TG_MAX: send_telegram(text); return
    for i in range(0, len(text), TG_MAX): send_telegram(text[i:i+TG_MAX])

def _extract_plain_text(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_content().strip()
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html = part.get_content()
                return re.sub(r"<[^>]+>", "", html).strip()
    else:
        return msg.get_content().strip()
    return ""

JSON_BLOCK_RE = re.compile(r"```json\s*(\[.*?\]|\{.*?\})\s*```|(\[.*\]|\{.*\})", re.DOTALL)

def _parse_json(text: str):
    m = JSON_BLOCK_RE.search(text)
    candidate = (m.group(1) or m.group(2)) if m else text.strip()
    return json.loads(candidate.strip())

def make_report(items):
    header = "🚩 اطلاعیه ویژه مناقصات عمرانی و ژئوتکنیک 🚩\n\n"
    body = []
    for i, t in enumerate(items, 1):
        title = (t.get("title") or "-").strip()
        company = (t.get("company") or "-").strip()
        deadline = (t.get("deadline") or "-").strip()
        link = (t.get("short_link") or t.get("link") or "-").strip()
        body.append(f"🔹 {i}. {title}\n🏢 {company}\n📆 مهلت ثبت‌نام: {deadline}\n🔗 لینک: {link}")
    footer = f"\n\n💬 جهت دریافت روزانه: {CHAT_ID}\n🌐 پلتفرم ارجاع تخصصی پروژه‌های مهندسی: rastaworks.ir"
    return header + "\n\n".join(body) + footer

def fetch_latest_email_text():
    if not (IMAP_USER and IMAP_PASS):
        raise RuntimeError("IMAP_USER/IMAP_PASS تنظیم نشده‌اند.")
    with imaplib.IMAP4_SSL(IMAP_HOST) as M:
        M.login(IMAP_USER, IMAP_PASS)
        M.select("INBOX")
        since = (datetime.utcnow() - timedelta(days=2)).strftime("%d-%b-%Y")
        criteria = [f'(SINCE "{since}")', f'(SUBJECT "{IMAP_SUBJECT_KEY}")']
        if IMAP_FROM: criteria.append(f'(FROM "{IMAP_FROM}")')
        status, data = M.search(None, *criteria)
        if status != "OK": raise RuntimeError(f"IMAP search failed: {status} {data}")
        ids = data[0].split()
        if not ids: raise RuntimeError("هیچ ایمیلی مطابق معیار پیدا نشد.")
        status, msg_data = M.fetch(ids[-1], "(RFC822)")
        if status != "OK": raise RuntimeError(f"IMAP fetch failed: {status}")
        msg = BytesParser(policy=policy.default).parsebytes(msg_data[0][1])
        print(f"✉️ From: {msg.get('From')} | Subject: {msg.get('Subject')}")
        return _extract_plain_text(msg)

def main():
    # برای تست دستی، اگر می‌خوای همین الآن ارسال شود، خط زیر را موقتاً کامنت کن.
    if not should_run_now():
        print("⏭️ Skip (not 9AM Paris)")
        return

    raw = fetch_latest_email_text()
    try:
        items = _parse_json(raw)
        if not isinstance(items, list): raise ValueError("JSON آرایه نیست.")
    except Exception as e:
        print("⚠️ متن ایمیل (ابتدا):", (raw[:1200] + " ...") if len(raw) > 1200 else raw, file=sys.stderr)
        raise RuntimeError(f"خطا در parse JSON: {e}")

    report = make_report(items) if items else "امروز هیچ مناقصهٔ معتبری ثبت نشده است."
    print("🛰️ ارسال به تلگرام...")
    send_long(report)
    print("✅ Done.")

if __name__ == "__main__":
    missing = [k for k, v in {
        "BOT_TOKEN": BOT_TOKEN, "GROUP_ID": CHAT_ID, "IMAP_USER": IMAP_USER, "IMAP_PASS": IMAP_PASS
    }.items() if not v]
    if missing:
        print(f"❌ محیط ناقص: {', '.join(missing)}", file=sys.stderr); sys.exit(1)
    main()
