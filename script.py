import os
import telebot
import time
from telebot import types

# ================= CONFIG =================
TOKEN = os.environ.get('TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
CHANNEL = "@chegaramsquare"

# --- NEW FEATURES ---
PAYMENT_REQUIRED = False  # Toggle this to False to disable payment
PAYMENT_ACCOUNT = "1000668647751"
PAYMENT_AMOUNT = "10 Birr"
MAX_POSTS_PER_DAY = 20 

bot = telebot.TeleBot(TOKEN)

# ================= STORAGE =================
user_data = {}
pending_approvals = {}
spam_tracker = {}

# ================= HELPERS =================

def is_spaming(user_id):
    now = time.time()
    if user_id not in spam_tracker:
        spam_tracker[user_id] = []

    # Filter only posts from the last 24 hours
    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if now - t < 86400]

    return len(spam_tracker[user_id]) >= MAX_POSTS_PER_DAY

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
        bot.send_message(
            uid,
            f"<b>⚠️ Daily Limit Reached</b>\n\nYou have already reached your limit of <b>{MAX_POSTS_PER_DAY}</b> post(s) per 24 hours. Please try again later!",
            parse_mode="HTML"
        )
        return

    user_data[uid] = {}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add("🏢 Service", "📦 Goods", "💼 Jobs")

    bot.send_message(
        uid,
        f"""
🌟 <b>Welcome to HU Chegaram Square</b> 🌟

Ready to reach thousands of students? 
Select a category below to start your post!

━━━━━━━━━━━━━━━━━━
✅ <b>Services</b> | ✅ <b>Goods</b> | ✅ <b>Jobs</b>
━━━━━━━━━━━━━━━━━━
""",
        parse_mode="HTML",
        reply_markup=markup
    )

# ================= TYPE SELECTION =================

@bot.message_handler(func=lambda m: m.text in ["🏢 Service", "📦 Goods", "💼 Jobs"])
def choose_type(message):
    uid = message.chat.id
    clean_text = message.text.split(" ")[1] # Get text without emoji
    user_data[uid] = {"type": clean_text.lower()}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    if clean_text == "Service":
        markup.add("Assignment", "Delivery", "Tutoring", "Other")
    elif clean_text == "Goods":
        markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup2.add("💰 Sell", "🔍 Wanted To Buy")
        bot.send_message(uid, "🏷 <b>Listing Type:</b>\nAre you selling or looking to buy?", parse_mode="HTML", reply_markup=markup2)
        bot.register_next_step_handler(message, set_goods_mode)
        return
    else:
        markup.add("Campus Work", "Coding", "Other")

    bot.send_message(uid, "✨ <b>Choose Sub-Category:</b>", parse_mode="HTML", reply_markup=markup)
    bot.register_next_step_handler(message, get_category)

def set_goods_mode(message):
    uid = message.chat.id
    user_data[uid]["goods_mode"] = "Wanted To Buy" if "Wanted" in message.text else "Sell"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Clothes", "Electronics", "Stationery", "Other")
    bot.send_message(uid, "✨ <b>Select Category:</b>", parse_mode="HTML", reply_markup=markup)
    bot.register_next_step_handler(message, get_category)

def get_category(message):
    uid = message.chat.id
    user_data[uid]["category"] = message.text
    bot.send_message(uid, "✏️ <b>Enter Title</b>\n(Max 60 chars, e.g., 'MacBook Pro 2020')", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, get_title)

# ================= DETAILS =================

def get_title(message):
    if len(message.text) > 60:
        bot.send_message(message.chat.id, "❌ <b>Title too long!</b> Please try a shorter title:", parse_mode="HTML")
        bot.register_next_step_handler(message, get_title)
        return
    user_data[message.chat.id]["title"] = message.text
    bot.send_message(message.chat.id, "💰 <b>Enter Price</b> (Numbers only):", parse_mode="HTML")
    bot.register_next_step_handler(message, get_price)

def get_price(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ <b>Invalid Input!</b> Please send digits only (e.g. 500):", parse_mode="HTML")
        bot.register_next_step_handler(message, get_price)
        return
    user_data[message.chat.id]["temp_price"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Fixed Price", "Per Hour (/hr)")
    bot.send_message(message.chat.id, "📊 <b>Price Type:</b>", parse_mode="HTML", reply_markup=markup)
    bot.register_next_step_handler(message, set_price_type)

def set_price_type(message):
    uid = message.chat.id
    suffix = "/hr" if "/hr" in message.text else ""
    user_data[uid]["price"] = f"{user_data[uid]['temp_price']} Birr{suffix}"
    bot.send_message(uid, "📍 <b>Enter Location:</b>\n(e.g., Main Campus, Dorm 412)", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, get_location)

def get_location(message):
    user_data[message.chat.id]["location"] = message.text
    bot.send_message(message.chat.id, "📞 <b>Enter Phone Number:</b>\n(09... or 07...)", parse_mode="HTML")
    bot.register_next_step_handler(message, get_phone)

def get_phone(message):
    uid = message.chat.id
    phone = format_phone(message.text)
    if not phone:
        bot.send_message(uid, "❌ <b>Invalid Phone!</b> Please check the number and try again:", parse_mode="HTML")
        bot.register_next_step_handler(message, get_phone)
        return
    user_data[uid]["phone"] = phone
    user_data[uid]["username"] = f"@{message.from_user.username}" if message.from_user.username else "No Username"
    bot.send_message(uid, "📝 <b>Enter Description:</b>\nProvide details about your post.", parse_mode="HTML")
    bot.register_next_step_handler(message, get_description)

def get_description(message):
    uid = message.chat.id
    user_data[uid]["description"] = message.text
    if user_data[uid]["type"] == "goods":
        bot.send_message(uid, "📸 <b>Send One Photo of the item:</b>", parse_mode="HTML")
        bot.register_next_step_handler(message, get_photo)
    else:
        handle_payment_flow(uid)

def get_photo(message):
    if message.photo:
        user_data[message.chat.id]["photo"] = message.photo[-1].file_id
        handle_payment_flow(message.chat.id)
    else:
        bot.send_message(message.chat.id, "⚠️ Please upload an actual <b>photo</b>:", parse_mode="HTML")
        bot.register_next_step_handler(message, get_photo)

# ================= PAYMENT LOGIC =================

def handle_payment_flow(uid):
    if PAYMENT_REQUIRED:
        bot.send_message(
            uid,
            f"""
💳 <b>Payment Required</b>

To post, please pay <b>{PAYMENT_AMOUNT}</b>.
Bank: <b>CBE (Commercial Bank)</b>
Account: <code>{PAYMENT_ACCOUNT}</code>

After paying, <b>send the Transaction Link</b> (CBE Birr link) below to proceed:
""",
            parse_mode="HTML"
        )
        bot.register_next_step_handler_by_chat_id(uid, get_payment_link)
    else:
        preview_post(uid)

def get_payment_link(message):
    uid = message.chat.id
    if "http" not in message.text:
        bot.send_message(uid, "❌ <b>Invalid Link!</b> Please send the full CBE transaction link:", parse_mode="HTML")
        bot.register_next_step_handler(message, get_payment_link)
        return

    user_data[uid]["payment_link"] = message.text
    preview_post(uid)

# ================= PREVIEW & SUBMIT =================

def build_post_text(data):
    if data["type"] == "goods":
        header = "─── 🔎 WANTED TO BUY ───" if data.get("goods_mode") == "Wanted To Buy" else "─── 🏷️ FOR SALE ───"
    elif data["type"] == "service":
        header = "─── 🛠 SERVICE PROVIDER ───"
    else:
        header = "─── 💼 JOB OPPORTUNITY ───"

    pay_info = f"\n🔗 <b>Payment:</b> {data['payment_link']}" if "payment_link" in data else ""

    return f"""
<b>{header}</b>

<b>{data['title']}</b>

💰 <b>Price:</b> {data['price']}

📍 <b>Location:</b> {data['location']}

👤 <b>Contact:</b> {data['username']}

📞 <b>Phone:</b> {data['phone']}

📝 <b>Description:</b>
{data['description']}
{pay_info}

<b>🚀 Post your own for FREE:</b>
 👉 @chegarams_bot

#{data['type']} #{data['category'].replace(' ', '')}
"""

def preview_post(uid):
    data = user_data[uid]
    text = build_post_text(data)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("✅ Submit for Review", "🔁 Start Again")

    if "photo" in data:
        bot.send_photo(uid, data["photo"], caption="<b>Post Preview:</b>\n" + text, parse_mode="HTML", reply_markup=markup)
    else:
        bot.send_message(uid, "<b>Post Preview:</b>\n" + text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["✅ Submit for Review", "🔁 Start Again"])
def handle_final(message):
    uid = message.chat.id
    if message.text == "🔁 Start Again":
        start(message)
        return

    # Success - Mark spam tracker ONLY on submission
    spam_tracker[uid].append(time.time())

    post_id = str(int(time.time()))
    pending_approvals[post_id] = user_data[uid]
    data = user_data[uid]
    text = build_post_text(data)

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"app_{post_id}"),
        types.InlineKeyboardButton("❌ Decline", callback_data=f"dec_{post_id}")
    )

    if "photo" in data:
        bot.send_photo(ADMIN_ID, data["photo"], caption="<b>NEW REQUEST</b>\n" + text, parse_mode="HTML", reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, "<b>NEW REQUEST</b>\n" + text, parse_mode="HTML", reply_markup=markup)

    bot.send_message(uid, "🚀 <b>Success!</b> Your post has been sent to the Admin for review. You will see it in the channel once approved.", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())

# ================= ADMIN CALLBACK =================

@bot.callback_query_handler(func=lambda call: True)
def admin_callback(call):
    action, post_id = call.data.split("_")
    if action == "app":
        data = pending_approvals.get(post_id)
        if data:
            # Clean payment link from final post
            data.pop('payment_link', None) 
            text = build_post_text(data)
            if "photo" in data:
                bot.send_photo(CHANNEL, data["photo"], caption=text, parse_mode="HTML")
            else:
                bot.send_message(CHANNEL, text, parse_mode="HTML")
            del pending_approvals[post_id]

    bot.answer_callback_query(call.id, "Action Completed")
    bot.delete_message(call.message.chat.id, call.message.message_id)

bot.polling(none_stop=True)
