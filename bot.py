import telebot
import sqlite3
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8424805856:AAEmua5bh0Cj5YwmJBYMxHAVkrPDTOKUImY"

# Multiple channels support
CHANNELS = [
    "@Sabohiyya",
    "@qoldan_kegancha"
]

bot = telebot.TeleBot(BOT_TOKEN)

# Database
db = sqlite3.connect("data.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals(
    new_user INTEGER PRIMARY KEY,
    referrer INTEGER,
    rewarded INTEGER DEFAULT 0
)
""")

db.commit()


# ==========================================================
# Helpers
# ==========================================================

def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users(user_id, points) VALUES(?, 0)", (user_id,))
    db.commit()


def joined_all_channels(user_id):
    """Check if user joined ALL channels"""
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True


def reward_referrer(user_id):
    """Give point to referrer if new user joined all channels"""
    cursor.execute("SELECT referrer, rewarded FROM referrals WHERE new_user=?", (user_id,))
    row = cursor.fetchone()

    if row is None:
        return

    referrer, rewarded = row

    if rewarded == 1:
        return

    if joined_all_channels(user_id):
        cursor.execute("UPDATE referrals SET rewarded = 1 WHERE new_user=?", (user_id,))
        cursor.execute("UPDATE users SET points = points + 1 WHERE user_id=?", (referrer,))
        db.commit()


def get_points(user_id):
    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0


# ==========================================================
# Buttons
# ==========================================================

def menu_buttons(user_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📥 Проверить подписку", callback_data="check"))
    kb.add(InlineKeyboardButton("🔗 Моя реферальная ссылка", callback_data="link"))
    kb.add(InlineKeyboardButton("⭐ Мои баллы", callback_data="stats"))
    return kb


def channels_buttons():
    kb = InlineKeyboardMarkup()
    for ch in CHANNELS:
        kb.add(InlineKeyboardButton(f"➡️ Перейти: {ch}", url=f"https://t.me/{ch[1:]}"))
    kb.add(InlineKeyboardButton("📥 Проверить подписку", callback_data="check"))
    return kb


# ==========================================================
# Start command
# ==========================================================

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    add_user(user_id)

    args = message.text.split()

    if len(args) > 1:
        referrer = args[1]
        if referrer != str(user_id):  # can't refer self
            cursor.execute("SELECT * FROM referrals WHERE new_user=?", (user_id,))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO referrals(new_user, referrer) VALUES(?, ?)",
                               (user_id, referrer))
                db.commit()

    reward_referrer(user_id)

    text = (
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Чтобы получать баллы:\n"
        "1️⃣ Вступай в каналы\n"
        "2️⃣ Проверь подписку\n"
        "3️⃣ Получи свою ссылку и приглашай друзей\n"
    )

    bot.send_message(user_id, text, parse_mode="HTML", reply_markup=menu_buttons(user_id))


# ==========================================================
# Callbacks
# ==========================================================

@bot.callback_query_handler(func=lambda call: call.data == "check")
def check_join(call):
    user_id = call.from_user.id

    if joined_all_channels(user_id):
        reward_referrer(user_id)
        bot.answer_callback_query(call.id, "🎉 Вы вступили во все каналы!")
        bot.edit_message_text("🎉 Отлично! Теперь можно приглашать друзей!", 
                              chat_id=user_id, 
                              message_id=call.message.message_id,
                              reply_markup=menu_buttons(user_id))
    else:
        bot.answer_callback_query(call.id, "❌ Вы не вступили во все каналы")
        bot.edit_message_text("❗ Вступи в каналы, чтобы продолжить:", 
                              chat_id=user_id,
                              message_id=call.message.message_id,
                              reply_markup=channels_buttons())


@bot.callback_query_handler(func=lambda call: call.data == "link")
def give_link(call):
    user_id = call.from_user.id
    username = bot.get_me().username
    link = f"https://t.me/{username}?start={user_id}"

    text = (
        "🔗 <b>Твоя реферальная ссылка:</b>\n"
        f"{link}\n\n"
        "Приглашай друзей и получай баллы!"
    )
    bot.edit_message_text(text, chat_id=user_id, message_id=call.message.message_id,
                          parse_mode="HTML", reply_markup=menu_buttons(user_id))


@bot.callback_query_handler(func=lambda call: call.data == "stats")
def stats(call):
    user_id = call.from_user.id
    pts = get_points(user_id)

    bot.edit_message_text(f"⭐ <b>Твои баллы:</b> {pts}",
                          chat_id=user_id,
                          message_id=call.message.message_id,
                          parse_mode="HTML",
                          reply_markup=menu_buttons(user_id))


bot.infinity_polling()
