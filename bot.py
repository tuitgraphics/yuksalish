import telebot
from telebot import types
import os

TOKEN = os.getenv("8424805856:AAEmua5bh0Cj5YwmJBYMxHAVkrPDTOKUImY")  # Render env
bot = telebot.TeleBot(TOKEN)

# Твои каналы
CHANNELS = ["@Sabohiyya"]

# Локальная база
users = {}  # { user_id: { "points": 0, "invited": [], "ref": id } }


# ======= УТИЛИТЫ =======

def ensure_user(uid, ref=None):
    if uid not in users:
        users[uid] = {"points": 0, "invited": [], "ref": ref}


def is_member(channel, user_id):
    try:
        member = bot.get_chat_member(channel, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


def check_all(user_id):
    for ch in CHANNELS:
        if not is_member(ch, user_id):
            return False
    return True


# ======= КРАСИВЫЕ КНОПКИ =======

def menu_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📨 My Referral Link", callback_data="ref"))
    kb.add(types.InlineKeyboardButton("📊 My Points", callback_data="points"))
    return kb


def channels_keyboard():
    kb = types.InlineKeyboardMarkup()
    for ch in CHANNELS:
        kb.add(types.InlineKeyboardButton(f"📡 Join {ch}", url=f"https://t.me/{ch[1:]}"))
    kb.add(types.InlineKeyboardButton("✅ I joined", callback_data="check"))
    return kb


# ======= СТАРТ =======

@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    args = msg.text.split()

    ref = None
    if len(args) > 1 and args[1].isdigit():
        ref = int(args[1])
        if ref == uid:
            ref = None

    ensure_user(uid, ref)

    bot.send_message(
        uid,
        "👋 Welcome!\nTo use the bot you must join all channels:",
        reply_markup=channels_keyboard()
    )


# ======= CALLBACK =======

@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    uid = call.from_user.id
    ensure_user(uid)

    # Проверка подписки
    if call.data == "check":
        if check_all(uid):
            bot.answer_callback_query(call.id, "You're in! 🎉")

            # начисление поинтов рефереру
            ref = users[uid]["ref"]
            if ref and uid not in users[ref]["invited"]:
                users[ref]["invited"].append(uid)
                users[ref]["points"] += 1

            bot.send_message(uid, "🎉 Access granted!", reply_markup=menu_keyboard())
        else:
            bot.answer_callback_query(call.id, "❗ Not all channels joined")
            bot.send_message(uid, "❗ You must join ALL channels:", reply_markup=channels_keyboard())

    # Реферальная ссылка
    elif call.data == "ref":
        bot.send_message(
            uid,
            f"🔗 Your personal link:\nhttps://t.me/{bot.get_me().username}?start={uid}"
        )

    # Поинты
    elif call.data == "points":
        bot.send_message(
            uid,
            f"📊 Your Points: {users[uid]['points']}\n"
            f"👥 Invited: {len(users[uid]['invited'])}"
        )


# ===== RUN =====

bot.infinity_polling(skip_pending=True)
