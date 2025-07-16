import telebot
from telebot import types
import sqlite3
import os
import requests

# توکن و کلید نقشه از محیط اجرا (Render یا GitHub)
TOKEN = os.getenv("TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
bot = telebot.TeleBot(TOKEN)

# زبان انتخاب‌شده برای هر کاربر
user_lang = {}

# پیام‌ها به زبان‌های فارسی و انگلیسی
MESSAGES = {
    "fa": {
        "welcome": "سلام! به ربات فروشنده «ازاینجا» خوش آمدی.",
        "choose_lang": "زبان خود را انتخاب کنید:",
        "register_product": "📦 ثبت کالا",
        "register_location": "🗺 ثبت موقعیت فروشگاه",
        "view_store": "👀 مشاهده فروشگاه من",
        "help": "ℹ️ راهنما",
        "language": "🌐 تغییر زبان",
        "fa_selected": "✅ زبان فارسی انتخاب شد.",
        "en_selected": "✅ English language selected.",
        "send_photo": "📷 لطفاً یک عکس از محصول ارسال کن.",
        "send_video": "🎥 لطفاً یک ویدیو از محصول ارسال کن یا رد کن.",
        "ask_links": "لینک سایت، پیج اینستاگرام و آیدی تلگرام را بنویس (با فاصله یا خط جدا کن):"
    },
    "en": {
        "welcome": "Hi! Welcome to the AZINJA seller bot.",
        "choose_lang": "Please choose your language:",
        "register_product": "📦 Register product",
        "register_location": "🗺 Set store location",
        "view_store": "👀 View my store",
        "help": "ℹ️ Help",
        "language": "🌐 Change language",
        "fa_selected": "✅ زبان فارسی انتخاب شد.",
        "en_selected": "✅ English language selected.",
        "send_photo": "📷 Please send a product photo.",
        "send_video": "🎥 Send product video or skip.",
        "ask_links": "Enter website, Instagram, and Telegram links (space or dash separated):"
    }
}

# 📦 ساخت دیتابیس
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            name TEXT,
            code TEXT,
            category TEXT,
            original INTEGER,
            photo TEXT,
            video TEXT,
            links TEXT
        )""")
    c.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            name TEXT,
            map_url TEXT,
            lat REAL,
            lon REAL
        )""")
    conn.commit()
    conn.close()

init_db()

# 🌐 دریافت تصویر نقشه
def get_map_image(lat, lon):
    if GOOGLE_API_KEY:
        url = "https://maps.googleapis.com/maps/api/staticmap"
        params = {
            "center": f"{lat},{lon}",
            "zoom": "15",
            "size": "600x400",
            "markers": f"{lat},{lon}",
            "key": GOOGLE_API_KEY
        }
        response = requests.get(url, params=params)
        with open("map.png", "wb") as f:
            f.write(response.content)
        return "map.png"
    return None

# 🎛 منو اصلی با زبان
@bot.message_handler(commands=['start'])
def start(message):
    user_lang[message.chat.id] = "fa"
    lang = user_lang[message.chat.id]
    msg = MESSAGES[lang]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(msg["register_product"], msg["register_location"])
    markup.row(msg["view_store"], msg["help"])
    markup.row(msg["language"])
    bot.send_message(message.chat.id, msg["welcome"], reply_markup=markup)

# 🌐 انتخاب زبان
@bot.message_handler(func=lambda m: m.text in [MESSAGES["fa"]["language"], MESSAGES["en"]["language"]])
def choose_language(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("فارسی 🇮🇷", "English 🇬🇧")
    bot.send_message(message.chat.id, MESSAGES[user_lang.get(message.chat.id, "fa")]["choose_lang"], reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["فارسی 🇮🇷", "English 🇬🇧"])
def set_language(message):
    lang = "fa" if "فارسی" in message.text else "en"
    user_lang[message.chat.id] = lang
    bot.send_message(message.chat.id, MESSAGES[lang][f"{lang}_selected"])
    start(message)

# 📦 ثبت کالا
@bot.message_handler(func=lambda m: m.text == MESSAGES[user_lang.get(m.chat.id, "fa")]["register_product"])
def reg_product(message):
    lang = user_lang.get(message.chat.id, "fa")
    bot.send_message(message.chat.id, "نام کالا را وارد کن:")
    bot.register_next_step_handler(message, lambda msg: step_name(msg, lang))

def step_name(message, lang):
    bot.send_message(message.chat.id, "کد کالا را وارد کن:")
    bot.register_next_step_handler(message, lambda msg: step_code(msg, lang, message.text))

def step_code(message, lang, name):
    bot.send_message(message.chat.id, "دسته‌بندی را وارد کن:")
    bot.register_next_step_handler(message, lambda msg: step_category(msg, lang, name, message.text))

def step_category(message, lang, name, code):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("✅ اصل", "❌ تقلبی")
    bot.send_message(message.chat.id, "اصالت کالا را انتخاب کن:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda msg: step_original(msg, lang, name, code, message.text))

def step_original(message, lang, name, code, category):
    original = 1 if "✅" in message.text else 0
    bot.send_message(message.chat.id, MESSAGES[lang]["send_photo"])
    bot.register_next_step_handler(message, lambda msg: step_photo(msg, lang, name, code, category, original))

def step_photo(message, lang, name, code, category, original):
    photo = message.photo[-1].file_id if message.photo else ""
    bot.send_message(message.chat.id, MESSAGES[lang]["send_video"])
    bot.register_next_step_handler(message, lambda msg: step_video(msg, lang, name, code, category, original, photo))

def step_video(message, lang, name, code, category, original, photo):
    video = message.video.file_id if message.content_type == 'video' else ""
    bot.send_message(message.chat.id, MESSAGES[lang]["ask_links"])
    bot.register_next_step_handler(message, lambda msg: finalize_product(msg, name, code, category, original, photo, video))

def finalize_product(message, name, code, category, original, photo, video):
    links = message.text
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (message.chat.id, name, code, category, original, photo, video, links))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ کالا با موفقیت ثبت شد.")

# 🗺 ثبت موقعیت فروشگاه
@bot.message_handler(func=lambda m: m.text == MESSAGES[user_lang.get(m.chat.id, "fa")]["register_location"])
def reg_location(message):
    bot.send_message(message.chat.id, "نام فروشگاه را وارد کن:")
    bot.register_next_step_handler(message, ask_store_name)

def ask_store_name(message):
    store_name = message.text
    bot.send_message(message.chat.id, "📍 لطفاً موقعیت فروشگاه را ارسال کن:")
    bot.register_next_step_handler(message, lambda loc: save_location(loc, store_name))

@bot.message_handler(content_types=['location'])
def save_location(message, store_name=None):
    if store_name:
        lat = message.location.latitude
        lon = message.location.longitude
        map_url = f"https://maps.google.com/?q={lat},{lon}"
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO stores VALUES (NULL, ?, ?, ?, ?, ?)",
                       (message.chat.id, store_name, map_url, lat, lon))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ موقعیت فروشگاه «{store_name}» ثبت شد.")
    else:
        bot.send_message(message.chat.id, ")

if store:
    name, map_url, lat, lon = store
    bot.send_message(message.chat.id, f"🏬 فروشگاه: {name}\n📍 موقعیت روی نقشه:\n{map_url}")
    image_path = get_map_image(lat, lon)
    if image_path:
        with open(image_path, "rb") as img:
            bot.send_photo(message.chat.id, img)
else:
    bot.send_message(message.chat.id, "⛔ هنوز فروشگاهی ثبت نکردی.")

if products:
    for item in products:
        pname, cat, orig, photo_id, video_id, links = item
        status = "✅ اصل" if orig else "❌ تقلبی"
        caption = f"📦 کالا: {pname}\n🏷 دسته: {cat}\n🔍 وضعیت: {status}\n🔗 اطلاعات بیشتر: {links}"
        if photo_id:
            bot.send_photo(message.chat.id, photo_id, caption=caption)
        elif video_id:
            bot.send_video(message.chat.id, video_id, caption=caption)
        else:
            bot.send_message(message.chat.id, caption)
else:
    bot.send_message(message.chat.id, "⛔ هنوز کالایی ثبت نکردی.")

@bot.message_handler(func=lambda m: m.text == MESSAGES[user_lang.get(m.chat.id, "fa")]["help"])
def help_msg(message):
    lang = user_lang.get(message.chat.id, "fa")
    
    if lang == "fa":
        bot.send_message(message.chat.id,
            "📌 راهنمای استفاده از بات:\n\n"
            "🛒 اگر فروشنده هستی:\n"
            "– از گزینه «📦 ثبت کالا» برای معرفی محصولت استفاده کن\n"
            "– می‌تونی عکس، ویدیو، لینک پیج و سایت رو هم ارسال کنی\n"
            "– با «🗺 ثبت موقعیت فروشگاه» مکان کسب‌و‌کارت رو مشخص کن\n"
            "– از «👀 مشاهده فروشگاه من» برای دیدن محصولاتت استفاده کن\n\n"
            "🛍 اگر خریدار هستی:\n"
            "– از طریق ربات می‌تونی محصولات فروشنده‌ها رو ببینی\n"
            "– مشخصات، اصالت، عکس و لینک‌های ارتباطی محصول رو دریافت کنی\n"
            "– و با اطمینان خرید کنی 😇"
        )
        from flask import Flask, request

app = Flask(name)

@app.route('/', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot is running!", 200

bot.remove_webhook()
bot.set_webhook(url='https://azinja-service.onrender.com/')

from flask import Flask, request

app = Flask(name)

@app.route('/', methods=['POST'])
def receive_update():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "Update received", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot is running with webhook. Polling is disabled.", 200

# حذف Webhook قبلی، در صورت وجود
bot.remove_webhook()

# فعال‌سازی Webhook جدید مطابق دامنه سرویس در Render
bot.set_webhook(url='https://azinja-service.onrender.com/')

bot.remove_webhook()
bot.set_webhook(url='http://azinja-service.onrender.com/')
   
else:
        bot.send_message(message.chat.id,
           "📌 Bot usage guide:\n\n"
            "🛒 If you're a seller:\n"
            "– Use '📦 Register product' to showcase your item\n"
            "– Send photo, video, website & Instagram links\n"
            "– Set your store location with '🗺 Set store location'\n"
            "– View your uploaded products with '👀 View my store'\n\n"
            "🛍 If you're a buyer:\n"
            "– Browse products from local sellers\n"
            "– Check authenticity, view media, and contact info\n"
            "– Shop safely with confidence 😇"
        )
