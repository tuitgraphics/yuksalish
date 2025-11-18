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
    new_user INTEGER PRIMARY KEY,
    referrer INTEGER,
    joined INTEGER DEFAULT 0
)""")  # joined = 0 not joined yet, 1 = joined
db.commit()


def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users(user_id, points) VALUES(?, 0)", (user_id,))
    db.commit()


def get_points(user_id):
    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0


def check_user_joined(user_id):
    """Returns True if user joined the channel"""
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


def process_join(user_id):
    """Check if user joined after referral. If yes → give point."""
    cursor.execute("SELECT referrer, joined FROM referrals WHERE new_user=?", (user_id,))
    row = cursor.fetchone()

    if not row:
        return  # not a referral

    referrer, joined_flag = row

    if joined_flag == 1:
        return  # already rewarded

    if check_user_joined(user_id):
        cursor.execute("UPDATE referrals SET joined = 1 WHERE new_user=?", (user_id,))
        cursor.execute("UPDATE users SET points = points + 1 WHERE user_id=?", (referrer,))
        db.commit()


@bot.message_handler(commands=['start'])
def start(message: Message):
    user_id = message.from_user.id
    add_user(user_id)

    args = message.text.split()

    # Referral parameter exists
    if len(args) > 1:
        referrer = args[1]

        if referrer != str(user_id):  # can't invite themselves
            cursor.execute("SELECT * FROM referrals WHERE new_user=?", (user_id,))
            exists = cursor.fetchone()

            if not exists:
                cursor.execute("INSERT INTO referrals(new_user, referrer) VALUES(?, ?)",
                               (user_id, referrer))
                db.commit()

    # Check if user joined channel → maybe give reward
    process_join(user_id)

    ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"

    text = (
        "👋 Welcome!\n\n"
        f"Your referral link:\n{ref_link}\n\n"
        f"⭐ Points: {get_points(user_id)}\n\n"
        f"To get points, make sure people *join the channel* after your link."
    )

    bot.send_message(user_id, text)


@bot.message_handler(commands=["stats"])
def stats(message: Message):
    user_id = message.from_user.id
    process_join(user_id)
    bot.send_message(message.chat.id, f"⭐ Your points: {get_points(user_id)}")


@bot.message_handler(commands=["check"])
def check_join(message: Message):
    user_id = message.from_user.id

    if check_user_joined(user_id):
        process_join(user_id)
        bot.send_message(user_id, "✅ You are in the channel!")
    else:
        bot.send_message(user_id, "❌ You are NOT in the channel.\nJoin to get points.")


bot.infinity_polling()
