import telebot
import sqlite3
from telebot.types import Message

BOT_TOKEN = "8424805856:AAEmua5bh0Cj5YwmJBYMxHAVkrPDTOKUImY"
CHANNEL_ID = "@Sabohiyya"  # Example: "@my_ref_channel"

bot = telebot.TeleBot(BOT_TOKEN)

# DB
db = sqlite3.connect("data.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS referrals(
    new_user INTEGER,
    referrer INTEGER
)""")
db.commit()

def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users(user_id, points) VALUES(?, 0)", (user_id,))
    db.commit()

def get_points(user_id):
    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

@bot.message_handler(commands=['start'])
def start(message: Message):
    user_id = message.from_user.id
    add_user(user_id)

    args = message.text.split()
    if len(args) > 1:
        referrer = args[1]

        if referrer != str(user_id):
            cursor.execute("SELECT * FROM referrals WHERE new_user=?", (user_id,))
            exists = cursor.fetchone()

            if not exists:
                cursor.execute("INSERT INTO referrals(new_user, referrer) VALUES(?, ?)", (user_id, referrer))
                cursor.execute("UPDATE users SET points = points + 1 WHERE user_id=?", (referrer,))
                db.commit()

    ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"

    bot.send_message(
        user_id,
        f"👋 Welcome!\n\n"
        f"Your referral link:\n{ref_link}\n\n"
        f"You have {get_points(user_id)} points."
    )

@bot.message_handler(commands=["stats"])
def stats(message: Message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, f"⭐ You have {get_points(user_id)} points.")

bot.infinity_polling()
