import os
import telebot
import time
import sqlite3
import json
from telebot import types

# ================= CONFIG =================
# Replace these with your actual values
TOKEN = os.environ.get('TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
CHANNEL = "@chegaramsquare"

PAYMENT_REQUIRED = False
PAYMENT_ACCOUNT = "1000668647751"
PAYMENT_AMOUNT = "10 Birr"
MAX_POSTS_PER_DAY = 20

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE STORAGE =================
DB_PATH = "bot.db"

def get_db():
    # Fresh connection for every request to avoid "Recursive use" errors in multi-threading
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn, conn.cursor()

# Initial setup to ensure tables exist
conn, cursor = get_db()
cursor.execute("CREATE TABLE IF NOT EXISTS user_storage(user_id INTEGER PRIMARY KEY, data TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS pending_posts(post_id TEXT PRIMARY KEY, data TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS spam_storage(user_id INTEGER, timestamp REAL)")
conn.commit()
conn.close()

# ================= STORAGE HELPERS =================
def save_user_data(uid, data):
    conn, cursor = get_db()
    cursor.execute("REPLACE INTO user_storage VALUES (?,?)", (uid, json.dumps(data)))
    conn.commit()
    conn.close()

def load_user_data(uid):
    conn, cursor = get_db()
    cursor.execute("SELECT data FROM user_storage WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else {}

def save_pending_post(post_id, data):
    conn, cursor = get_db()
    cursor.execute("REPLACE INTO pending_posts VALUES (?,?)", (post_id, json.dumps(data)))
    conn.commit()
    conn.close()

def load_pending_post(post_id):
    conn, cursor = get_db()
    cursor.execute("SELECT data FROM pending_posts WHERE post_id=?", (post_id,))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

def add_spam_record(uid):
    conn, cursor = get_db()
    cursor.execute("INSERT INTO spam_storage VALUES (?,?)", (uid, time.time()))
    conn.commit()
    conn.close()

def get_spam_records(uid):
    now = time.time()
    conn, cursor = get_db()
    cursor.execute("SELECT timestamp FROM spam_storage WHERE user_id=?", (uid,))
    rows = cursor.fetchall()
    valid = [r[0] for r in rows if now - r[0] < 86400]
    
    cursor.execute("DELETE FROM spam_storage WHERE user_id=?", (uid,))
    for t in valid:
        cursor.execute("INSERT INTO spam_storage VALUES (?,?)", (uid, t))
    
    conn.commit()
    conn.close()
    return valid

# ================= HELPERS =================
def is_spaming(user_id):
    records = get_spam_records(user_id)
    return len(records) >= MAX_POSTS_PER_DAY

def format_phone(phone_text):
    clean = ''.join(filter(str.isdigit, phone_text))
    if (clean.startswith("09") or clean.startswith("07")) and len(clean) == 10:
        return "+251" + clean[1:]
    if (clean.startswith("9") or clean.startswith("7")) and len(clean) == 9:
        return "+251" + clean
    if phone_text.startswith("+251"):
        return phone_text
    return None

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    if is_spaming(uid):
        bot.send_message(uid, f"<b>⚠️ Daily Limit Reached</b>\n\nYou've hit your limit of <b>{MAX_POSTS_PER_DAY}</b> posts for today. Come back tomorrow!", parse_mode="HTML")
        return

    save_user_data(uid, {})
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add("🏢 Service", "📦 Items", "💼 Jobs")

    bot.send_message(
        uid,
        """
🌟 <b>Welcome to HU Chegaram Square</b> 🌟

Ready to reach the entire campus? 🚀
Select a category below to create your post:
""",
        parse_mode="HTML",
        reply_markup=markup
    )

# ================= TYPE SELECTION =================
@bot.message_handler(func=lambda m: m.text in ["🏢 Service", "📦 Items", "💼 Jobs"])
def choose_type(message):
    uid = message.chat.id
    
    if "Items" in message.text:
        clean_text = "Goods"
    elif "Service" in message.text:
        clean_text = "Service"
    else:
        clean_text = "Jobs"
    
    data = load_user_data(uid)
    data["type"] = clean_text.lower()
    save_user_data(uid, data)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if clean_text == "Service":
        markup.add("Doing Assignment(አሳይመንት መስራት)", "Delivery(መላላክ)", "Tutoring(ማስጠናት)", "Guitar Teaching(ጊታር ማስተማር)", "Other(ሌላ)")
    elif clean_text == "Goods":
        markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup2.add("💰 Selling(ለመሸጥ)", "🔍 Looking to Buy(ለመግዛት)")
        bot.send_message(uid, "✨ <b>What is your goal?</b>", parse_mode="HTML", reply_markup=markup2)
        bot.register_next_step_handler(message, set_goods_mode)
        return
    else:
        markup.add("Campus Work", "Coding", "Other")

    bot.send_message(uid, "📂 <b>Select a sub-category:</b>", parse_mode="HTML", reply_markup=markup)
    bot.register_next_step_handler(message, get_category)

def set_goods_mode(message):
    uid = message.chat.id
    data = load_user_data(uid)
    data["goods_mode"] = "Wanted To Buy" if "Buy" in message.text else "Sell"
    save_user_data(uid, data)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Clothes", "Electronics", "Plumpynut","Sandwitch", "Other" )
    bot.send_message(uid, "📦 <b>What kind of item is it?</b>", parse_mode="HTML", reply_markup=markup)
    bot.register_next_step_handler(message, get_category)

def get_category(message):
    uid = message.chat.id
    data = load_user_data(uid)
    data["category"] = message.text
    save_user_data(uid, data)

    bot.send_message(
        uid,
        "📝 <b>Give your post a Title</b>\nKeep it short and catchy (Max 60 characters).",
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(message, get_title)

# ================= DETAILS =================
def get_title(message):
    if len(message.text) > 60:
        bot.send_message(message.chat.id, f"❌ <b>Too long!</b> Your title is {len(message.text)} characters. Please keep it under 60:", parse_mode="HTML")
        bot.register_next_step_handler(message, get_title)
        return

    data = load_user_data(message.chat.id)
    data["title"] = message.text
    save_user_data(message.chat.id, data)

    bot.send_message(message.chat.id, "💰 <b>Set your Price:</b>\n(Numbers only, e.g., 500)", parse_mode="HTML")
    bot.register_next_step_handler(message, get_price)

def get_price(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ <b>Invalid format!</b> Please enter numbers only:", parse_mode="HTML")
        bot.register_next_step_handler(message, get_price)
        return

    data = load_user_data(message.chat.id)
    data["temp_price"] = message.text
    save_user_data(message.chat.id, data)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Total Price", "Per Hour (/hr)")
    bot.send_message(message.chat.id, "📊 <b>How is this priced?</b>", reply_markup=markup, parse_mode="HTML")
    bot.register_next_step_handler(message, set_price_type)

def set_price_type(message):
    uid = message.chat.id
    data = load_user_data(uid)
    suffix = " /hr" if "/hr" in message.text else ""
    data["price"] = f"{data['temp_price']} Birr{suffix}"
    save_user_data(uid, data)

    bot.send_message(uid, "📍 <b>Where can you be found?</b>\n(e.g., Main Campus, Tecno , አግሪ ካምፓስ)", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, get_location)

def get_location(message):
    data = load_user_data(message.chat.id)
    data["location"] = message.text
    save_user_data(message.chat.id, data)
    bot.send_message(message.chat.id, "📞 <b>Your Phone Number:</b>\n(09... or 07...)", parse_mode="HTML")
    bot.register_next_step_handler(message, get_phone)

def get_phone(message):
    uid = message.chat.id
    phone = format_phone(message.text)
    if not phone:
        bot.send_message(uid, "❌ <b>Invalid Number!</b> Please try again:", parse_mode="HTML")
        bot.register_next_step_handler(message, get_phone)
        return

    data = load_user_data(uid)
    data["phone"] = phone
    data["username"] = f"@{message.from_user.username}" if message.from_user.username else "No Username"
    save_user_data(uid, data)

    bot.send_message(uid, "📖 <b>Add a Description:</b>\nDescribe your item or service in detail.", parse_mode="HTML")
    bot.register_next_step_handler(message, get_description)

def get_description(message):
    uid = message.chat.id
    data = load_user_data(uid)
    data["description"] = message.text
    save_user_data(uid, data)

    if data["type"] == "goods":
        bot.send_message(uid, "📸 <b>Almost done!</b> Send one clear photo of your item:", parse_mode="HTML")
        bot.register_next_step_handler(message, get_photo)
    else:
        handle_payment_flow(uid)

def get_photo(message):
    if message.photo:
        data = load_user_data(message.chat.id)
        data["photo"] = message.photo[-1].file_id
        save_user_data(message.chat.id, data)
        handle_payment_flow(message.chat.id)
    else:
        bot.send_message(message.chat.id, "⚠️ <b>Please send an image file:</b>", parse_mode="HTML")
        bot.register_next_step_handler(message, get_photo)

# ================= PAYMENT =================
def handle_payment_flow(uid):
    if PAYMENT_REQUIRED:
        bot.send_message(uid, f"💳 <b>Payment Required</b>\n\nPay {PAYMENT_AMOUNT}\nAccount: <code>{PAYMENT_ACCOUNT}</code>\n\nSend the transaction link here after paying. \n Ex: https://cbe.com", parse_mode="HTML")
        bot.register_next_step_handler_by_chat_id(uid, get_payment_link)
    else:
        preview_post(uid)

def get_payment_link(message):
    uid = message.chat.id
    if "http" not in message.text:
        bot.send_message(uid, "❌ <b>Link invalid!</b> Paste the full transaction link:", parse_mode="HTML")
        bot.register_next_step_handler(message, get_payment_link)
        return
    data = load_user_data(uid)
    data["payment_link"] = message.text
    save_user_data(uid, data)
    preview_post(uid)

# ================= PREVIEW =================
def build_post_text(data):
    if data["type"] == "goods":
        header = "─── 🔎 WANTED TO BUY ───" if data.get("goods_mode") == "Wanted To Buy" else "─── 🏷️ FOR SALE ───"
    elif data["type"] == "service":
        header = "─── 🛠 SERVICE PROVIDER ───"
    else:
        header = "─── 💼 JOB OPPORTUNITY ───"

    pay_info = f"\n🔗 Payment: {data['payment_link']}" if "payment_link" in data else ""
    return f"<b>{header}</b>\n\n<b>{data['title']}</b>\n\n💰 Price: {data['price']}\n\n 📍 Location: {data['location']}\n\n👤 Contact: {data['username']} | 📞 Phone: {data['phone']}\n \n 📝 Description:\n \n {data['description']}\n{pay_info}\n\n<b>🚀 Post your own for FREE:</b>\n 👉 @chegarams_bot\n\n#{data['type']} #{data['category'].replace(' ', '')}"

def preview_post(uid):
    data = load_user_data(uid)
    text = build_post_text(data)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("✅ Submit for Review", "🔁 Start Again")

    bot.send_message(uid, "👀 <b>Here is a preview of your post:</b>", parse_mode="HTML")
    if "photo" in data:
        bot.send_photo(uid, data["photo"], caption=text, parse_mode="HTML", reply_markup=markup)
    else:
        bot.send_message(uid, text, parse_mode="HTML", reply_markup=markup)

# ================= FINAL SUBMIT =================
@bot.message_handler(func=lambda m: m.text in ["✅ Submit for Review", "🔁 Start Again"])
def handle_final(message):
    uid = message.chat.id
    if message.text == "🔁 Start Again":
        start(message)
        return

    add_spam_record(uid)
    post_id = str(int(time.time()))
    data = load_user_data(uid)
    data["user_id"] = uid  # Ensure we can notify user on approval/decline
    save_pending_post(post_id, data)

    text = build_post_text(data)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"app_{post_id}"),
        types.InlineKeyboardButton("❌ Decline", callback_data=f"dec_{post_id}")
    )

    if "photo" in data:
        bot.send_photo(ADMIN_ID, data["photo"], caption="🆕 <b>INCOMING POST REQUEST</b>\n"+text,
                       parse_mode="HTML", reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, "🆕 <b>INCOMING POST REQUEST</b>\n"+text,
                         parse_mode="HTML", reply_markup=markup)

    bot.send_message(uid, "🚀 <b>Success!</b> Your post is now with the admin team for review. Check the channel soon!", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())

# ================= ADMIN CALLBACK =================
@bot.callback_query_handler(func=lambda call: True)
def admin_callback(call):
    action, post_id = call.data.split("_")
    data = load_pending_post(post_id)

    if not data:
        bot.answer_callback_query(call.id, "Error: Data expired.")
        return

    user_id = data.get("user_id")

    if action == "app":
        data.pop("payment_link", None)
        text = build_post_text(data)
        if "photo" in data:
            bot.send_photo(CHANNEL, data["photo"], caption=text, parse_mode="HTML")
        else:
            bot.send_message(CHANNEL, text, parse_mode="HTML")
        
        try:
            bot.send_message(user_id, "🎉 <b>Good news!</b> Your post has been approved and is now live on @chegaramsquare!")
        except:
            pass

    elif action == "dec":
        try:
            bot.send_message(user_id, "❌ <b>Post Declined.</b> Your submission didn't meet our guidelines. Feel free to try again with updated info!")
        except:
            pass
    
    bot.answer_callback_query(call.id, "Action Completed")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ================= RUN =================
bot.polling(none_stop=True)
