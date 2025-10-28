import requests
from telegram import Bot
import schedule
import time

# اطلاعات ربات و گروه
TOKEN = "8220240222:AAFgyAsiCwUooeWwxKDNwzCsohdCIE8SFx8"
CHAT_ID = "@rasta3_group"

# آدرس سرویسی که دیتا را برمی‌گرداند (خروجی من یا سرویس پایدار عمومی)
TENDERS_URL = "https://api.my-comet-ai.ir/daily-tenders"  # اگر api اختصاصی از من داشته باشی این قسمت قرار می‌گیرد

def get_tenders():
    # درخواست به سرویس دریافت دیتا
    resp = requests.get(TENDERS_URL)
    if resp.status_code == 200:
        try:
            tenders = resp.json()  # خروجی باید لیست دیکشنری باشد (مثل نمونه قبلی)
            return tenders
        except:
            return []
    return []

def make_report(tender_list):
    header = "🚩 اطلاعیه ویژه مناقصات عمرانی و ژئوتکنیک 🚩\n\n"
    body = ""
    for i, tender in enumerate(tender_list, 1):
        body += f"🔹 {i}. {tender['title']}\n"
        body += f"🏢 {tender['company']}\n"
        body += f"📆 مهلت ثبت‌نام: {tender['deadline']}\n"
        body += f"🔗 لینک: {tender['short_link']}\n\n"
    footer = f"💬 جهت دریافت روزانه: @rasta3_group\n🌐 پلتفرم ارجاع تخصصی پروژه‌های مهندسی: rastaworks.ir"
    return header + body + footer

def send_report():
    tenders = get_tenders()
    if not tenders:
        report = "امروز هیچ مناقصه معتبر ثبت نشده است."
    else:
        report = make_report(tenders)
    bot = Bot(token=TOKEN)
    bot.send_message(chat_id=CHAT_ID, text=report)

# ارسال یکبار الان
send_report()

# زمان‌بندی روزانه برای ارسال خودکار (هر روز ساعت ۹ صبح)
schedule.every().day.at("09:00").do(send_report)

# حلقه اجرا
while True:
    schedule.run_pending()
    time.sleep(60)
