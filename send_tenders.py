import os
from telegram import Bot

# به هیچ وجه توکن و آی‌دی گروه را دستی در کد ننویس!
TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["GROUP_ID"]

def get_tenders():
    return [
        {
            "title": "نمونه مناقصه تستی",
            "company": "شرکت نمونه",
            "deadline": "۶ آبان",
            "short_link": "https://b2n.ir/test"
        },
        {
            "title": "مناقصه دوم",
            "company": "شرکت دوم",
            "deadline": "۷ آبان",
            "short_link": "https://yun.ir/test2"
        }
    ]

def make_report(tender_list):
    header = "🚩 اطلاعیه ویژه مناقصات عمرانی و ژئوتکنیک 🚩\n\n"
    body = ""
    for i, tender in enumerate(tender_list, 1):
        body += f"🔹 {i}. {tender['title']}\n"
        body += f"🏢 {tender['company']}\n"
        body += f"📆 مهلت ثبت‌نام: {tender['deadline']}\n"
        body += f"🔗 لینک: {tender['short_link']}\n\n"
    footer = f"💬 جهت دریافت روزانه: {CHAT_ID}\n🌐 پلتفرم ارجاع تخصصی پروژه‌های مهندسی: rastaworks.ir"
    return header + body + footer

def send_report():
    tenders = get_tenders()
    if not tenders:
        report = "امروز هیچ مناقصه معتبر ثبت نشده است."
    else:
        report = make_report(tenders)
    bot = Bot(token=TOKEN)
    bot.send_message(chat_id=CHAT_ID, text=report)

send_report()
