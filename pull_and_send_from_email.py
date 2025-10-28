import os, sys, re, json, requests, imaplib
from datetime import datetime, timedelta
from email import policy
from email.parser import BytesParser

# ---- ENV (نام‌های جایگزین هم پذیرفته می‌شود) ----
IMAP_HOST = os.environ.get("IMAP_HOST") or os.environ.get("OUTLOOK_IMAP_HOST")
IMAP_USER = os.environ.get("IMAP_USER") or os.environ.get("IMAP_USERNAME") or os.environ.get("EMAIL_USER")
IMAP_PASS = os.environ.get("IMAP_PASS") or os.environ.get("IMAP_PASSWORD") or os.environ.get("EMAIL_PASS")
IMAP_FROM = os.environ.get("IMAP_FROM", "")  # اختیاری
IMAP_SUBJECT_KEY = os.environ.get("IMAP_SUBJECT_KEY", "DAILY_TENDERS_JSON")

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("GROUP_ID")  # عددی، معمولاً -100...
TG_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ---- چک اولیه ----
missing = [k for k, v in {
    "BOT_TOKEN": BOT_TOKEN, "GROUP_ID": CHAT_ID,
    "IMAP_HOST": IMAP_HOST, "IMAP_USER": IMAP_USER, "IMAP_PASS": IMAP_PASS
}.items() if not v]
if missing:
    print(f"❌ محیط ناقص: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)

def tgc(method, **params):
    url = f"{TG_BASE}/{method}"
    r = requests.post(url, data=params, timeout=60)
    try:
        data = r.json()
    except Exception:
        data = {"ok": False, "error": r.text}
    ok = (r.status_code == 200) and data.get("ok", False)
    print((f"✅ TG {method} ok" if ok else f"❌ TG {method} FAILED {data}"),
          file=sys.stderr if not ok else sys.stdout)
    return ok, data

def send_text(text):
    return tgc("sendMessage", chat_id=CHAT_ID, text=text, disable_web_page_preview=True)

def send_long(text):
    MAX = 4096
    if len(text) <= MAX:
        send_text(text); return
    for i in range(0, len(text), MAX):
        send_text(text[i:i+MAX])

JSON_BLOCK_RE = re.compile(r"```json\s*(\[.*?\]|\{.*?\})\s*```|(\[.*\]|\{.*\})", re.DOTALL)

def parse_json_from_text(text):
    m = JSON_BLOCK_RE.search(text)
    candidate = (m.group(1) or m.group(2)) if m else text.strip()
    return json.loads(candidate.strip())

def extract_plain_text(msg):
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

def make_report(items):
    header = "🚩 اطلاعیه ویژه مناقصات عمرانی و ژئوتکنیک 🚩\n\n"
    rows = []
    for i, t in enumerate(items, 1):
        title = (t.get("title") or "-").strip()
        company = (t.get("company") or "-").strip()
        deadline_iso = (t.get("deadline_iso") or t.get("deadline") or "-").strip()
        deadline_local = (t.get("deadline_local") or "-").strip()
        link = (t.get("short_link") or t.get("link") or t.get("source_url") or "-").strip()
        dl = deadline_local if deadline_local != "-" else deadline_iso
        rows.append(f"🔹 {i}. {title}\n🏢 {company}\n📆 مهلت: {dl}\n🔗 لینک: {link}")
    footer = f"\n\n💬 جهت دریافت روزانه: {CHAT_ID}\n🌐 rastaworks.ir"
    return header + "\n\n".join(rows) + footer

def find_latest_task_email():
    # ۷ روز اخیر / اول با Subject فیلتر، اگر چیزی نبود، بدون Subject
    with imaplib.IMAP4_SSL(IMAP_HOST) as M:
        M.login(IMAP_USER, IMAP_PASS)
        M.select("INBOX")
        since = (datetime.utcnow() - timedelta(days=7)).strftime("%d-%b-%Y")

        def search_ids(use_subject=True):
            crit = [f'(SINCE "{since}")']
            if use_subject and IMAP_SUBJECT_KEY:
                crit.append(f'(SUBJECT "{IMAP_SUBJECT_KEY}")')
            if IMAP_FROM:
                crit.append(f'(FROM "{IMAP_FROM}")')
            status, data = M.search(None, *crit)
            if status != "OK":
                raise RuntimeError(f"IMAP search failed: {status} {data}")
            ids = data[0].split()
            print(f"ℹ️ IMAP search ({'with' if use_subject else 'no'} subject): {len(ids)} hits")
            return ids

        ids = search_ids(True)
        if not ids:
            ids = search_ids(False)
            if not ids:
                return None, None, None  # هیچ ایمیلی پیدا نشد

        latest_id = ids[-1]
        status, msg_data = M.fetch(latest_id, "(RFC822)")
        if status != "OK":
            raise RuntimeError(f"IMAP fetch failed: {status}")
        msg = BytesParser(policy=policy.default).parsebytes(msg_data[0][1])
        subject = str(msg.get("Subject"))
        sender = str(msg.get("From"))
        body = extract_plain_text(msg)
        print(f"✉️ Latest: From={sender} | Subject={subject} | body_len={len(body)}")
        return subject, sender, body

def main():
    # 1) چک تلگرام + پیام تست
    tgc("getMe")
    tgc("getChat", chat_id=CHAT_ID)
    ok, _ = send_text("🔧 تست دیباگ: اگر این پیام را می‌بینی یعنی ارسال تلگرام برقرار است.")
    # اگر همین پیام هم نرسید، مشکل از GROUP_ID/عضویت ربات است.

    # 2) ایمیل را بخوان
    subject, sender, raw = find_latest_task_email() or (None, None, None)
    if not raw:
        send_text("⚠️ دیباگ: هیچ ایمیلی مطابق معیار پیدا نشد. Subject فیلتر: "
                  f"`{IMAP_SUBJECT_KEY}` | از: `{IMAP_FROM or 'ANY'}` | بازه: 7 روز اخیر.")
        return

    # 3) JSON را پارس کن
    try:
        items = parse_json_from_text(raw)
        if not isinstance(items, list):
            raise ValueError("JSON آرایه نیست.")
    except Exception as e:
        preview = raw[:1200] + ("..." if len(raw) > 1200 else "")
        send_text(f"⚠️ دیباگ: JSON پارس نشد: {e}\n"
                  f"Subject: {subject}\nFrom: {sender}\n\nپیش‌نمایش:\n{preview}")
        return

    # 4) گزارش را بفرست
    report = make_report(items) if items else "امروز هیچ مناقصهٔ معتبری ثبت نشده است."
    send_long(report)
    send_text("✅ دیباگ: ارسال تمام شد.")

if __name__ == "__main__":
    main()
