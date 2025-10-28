# send_tenders.py
import os
import sys
import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

# ===========================
# تنظیمات محیطی
# ===========================
TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("GROUP_ID")  # برای گروه‌ها معمولاً چیزی شبیه -100xxxxxxxxxx

if not TOKEN or not CHAT_ID:
    print("❌ BOT_TOKEN یا GROUP_ID در محیط تنظیم نشده‌اند.", file=sys.stderr)
    sys.exit(1)

API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
TELEGRAM_MAX_LEN = 4096  # محدودیت پیام تلگرام

# ===========================
# منطق داده‌ها (نمونه)
# در عمل این تابع را با خروجی پرپلکسیتی جایگزین کن
# ===========================
def get_tenders():
    # TODO: اینجا داده‌های واقعی را از پرپلکسیتی/منبع‌ات بساز
    return [
        {
            "title": "نمونه مناقصه تستی",
            "company": "شرکت نمونه",
            "deadline": "۶ آبان",
            "short_link": "https://b2n.ir/test",
        },
        {
            "title": "مناقصه دوم",
            "company": "شرکت دوم",
            "deadline": "۷ آبان",
            "short_link": "https://yun.ir/test2",
        },
    ]

# ===========================
# ساخت متن گزارش
# ===========================
def make_report(tender_list):
    header = "🚩 اطلاعیه ویژه مناقصات عمرانی و ژئوتکنیک 🚩\n\n"
    body_parts = []
    for i, t in enumerate(tender_list, 1):
        body_parts.append(
            textwrap.dedent(
                f"""\
                🔹 {i}. {t.get('title','-')}
                🏢 {t.get('company','-')}
                📆 مهلت ثبت‌نام: {t.get('deadline','-')}
                🔗 لینک: {t.get('short_link','-')}
                """
            ).strip()
        )
    body = "\n\n".join(body_parts) + "\n\n"
    footer = f"💬 جهت دریافت روزانه: {CHAT_ID}\n🌐 پلتفرم ارجاع تخصصی پروژه‌های مهندسی: rastaworks.ir"
    return header + body + footer

# ===========================
# ارسال پیام (با تکه‌تکه‌سازی در صورت بلند بودن)
# ===========================
def send_text(text: str) -> None:
    # disable_web_page_preview برای جلوگیری از پریویو لینک‌ها
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(API_URL, data=payload, timeout=30)
        if resp.status_code != 200:
            print(f"❌ خطای HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
            # اگر Bad Request باشد، معمولاً متن شامل «chat not found» یا «bot was kicked» است.
    except requests.RequestException as e:
        print(f"❌ خطای شبکه هنگام ارسال: {e}", file=sys.stderr)

def send_long_message(text: str) -> None:
    if len(text) <= TELEGRAM_MAX_LEN:
        send_text(text)
        return
    # اگر متن بلندتر از 4096 بود، تکه‌تکه بفرست
    start = 0
    while start < len(text):
        end = min(start + TELEGRAM_MAX_LEN, len(text))
        chunk = text[start:end]
        send_text(chunk)
        start = end

# ===========================
# گارد ساعت پاریس = ۹ صبح
# (برای اجراهای ساعتی/تست دستی: اگر الآن ۹ نیست، اسکیپ کن)
# اگر نمی‌خوای این گارد فعال باشه، این دو خط را کامنت کن.
# ===========================
def should_run_now_paris_9am() -> bool:
    now_paris = datetime.now(ZoneInfo("Europe/Paris"))
    print(f"ℹ️ اکنون پاریس: {now_paris.strftime('%Y-%m-%d %H:%M')}")
    return now_paris.hour == 9  # دقیقاً ساعت ۹

# ===========================
# اجرای اصلی
# ===========================
def main():
    # اگر از کرانِ ساعتی استفاده می‌کنی، این گارد مهمه
    if not should_run_now_paris_9am():
        print("⏭️ Skip: خارج از بازهٔ ۹ صبح Europe/Paris")
        return

    tenders = get_tenders()

    if not tenders:
        report = "امروز هیچ مناقصهٔ معتبری ثبت نشده است."
    else:
        report = make_report(tenders)

    print("🛰️ در حال ارسال به تلگرام...")
    send_long_message(report)
    print("✅ تمام.")

if __name__ == "__main__":
    main()
