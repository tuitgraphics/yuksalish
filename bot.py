import telebot
from telebot import types
import os
from dotenv import load_dotenv
import pyrebase
import logging

# Set up basic logging (helpful for debugging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =========================================================
# 1. INITIALIZATION: LOAD SECRETS, CONNECT TO FIREBASE
# =========================================================

# --- CRITICAL: Load environment variables from .env file ---
load_dotenv('myenv.env')

TOKEN = os.getenv("TOKEN") 
FIREBASE_URL = os.getenv("FIREBASE_URL")
SERVICE_ACCOUNT_FILE = os.getenv("FIREBASE_SERVICE_ACCOUNT")

# --- Initialize Firebase ---
try:
    config = {
        "databaseURL": FIREBASE_URL,
        "serviceAccount": SERVICE_ACCOUNT_FILE
    }
    firebase = pyrebase.initialize_app(config)
    db = firebase.database()
    logging.info("Firebase connection established successfully.")
except Exception as e:
    # If the connection fails (e.g., bad URL or missing JSON file), stop here
    logging.error(f"FATAL ERROR: Could not connect to Firebase: {e}")
    exit(1) # Stop the script immediately

# --- Initialize Bot ---
if not TOKEN:
    logging.error("FATAL ERROR: Telegram TOKEN is missing. Check your .env file.")
    exit(1)
    
bot = telebot.TeleBot(TOKEN)
CHANNELS = ["@yuksalishuz"]


# =========================================================
# 2. DATABASE UTILITIES
# =========================================================

def get_user_data(uid):
    """Fetches user data from Firebase."""
    # Use str(uid) because Firebase keys must be strings
    user_data = db.child("users").child(str(uid)).get().val()
    
    if user_data is None:
        return None
    
    # Ensure all keys exist, even if not explicitly stored
    user_data["points"] = user_data.get("points", 0)
    user_data["invited"] = user_data.get("invited", [])
    user_data["ref"] = user_data.get("ref", None)
    return user_data


def ensure_user(uid, ref=None):
    """Creates user data in Firebase if they don't exist."""
    user_data = get_user_data(uid)
    if user_data is None:
        new_user = {
            "points": 0,
            "invited": [],
            "ref": ref
        }
        db.child("users").child(str(uid)).set(new_user)
        logging.info(f"New user created: {uid}")
        return new_user
    return user_data


def reward_referrer(uid, ref):
    """Increments referrer's points and adds the user to their invited list."""
    
    # Check if the referrer exists
    ref_data = get_user_data(ref)
    if not ref_data:
        logging.warning(f"Referrer ID {ref} not found in database. Cannot reward.")
        return
        
    # Check if user has already been rewarded for this invite (prevents double counting)
    if str(uid) not in ref_data.get("invited", []):
        
        # 1. Update list and points locally
        ref_data["invited"].append(str(uid))
        ref_data["points"] += 1
        
        # 2. Write the whole updated object back to Firebase
        db.child("users").child(str(ref)).set(ref_data)
        logging.info(f"Rewarded user {ref}. New points: {ref_data['points']}")

        # Notify the referrer
        try:
            bot.send_message(ref, "🥳 You earned 1 point! A new user joined from your link.")
        except telebot.apihelper.ApiTelegramException:
            # This happens if the referrer has blocked the bot
            logging.warning(f"Could not notify referrer {ref}. Bot likely blocked.")
        except Exception as e:
             logging.error(f"Error sending reward notification: {e}")


# =========================================================
# 3. OTHER UTILITIES (UNCHANGED)
# =========================================================

def is_member(channel, user_id):
    try:
        # Use str(user_id) for robustness, though integer usually works here
        member = bot.get_chat_member(channel, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        # Log the error if the bot isn't an admin or channel name is wrong
        logging.error(f"Error checking membership in {channel} for {user_id}: {e}")
        return False

def check_all(user_id):
    for ch in CHANNELS:
        if not is_member(ch, user_id):
            return False
    return True

def menu_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📨 My Referral Link", callback_data="ref"))
    kb.add(types.InlineKeyboardButton("📊 My Points", callback_data="points"))
    return kb

def channels_keyboard():
    kb = types.InlineKeyboardMarkup()
    for ch in CHANNELS:
        # Note: Telegram link format is t.me/channelname without the @
        kb.add(types.InlineKeyboardButton(f"📡 Join {ch}", url=f"https://t.me/{ch[1:]}"))
    kb.add(types.InlineKeyboardButton("✅ I joined", callback_data="check"))
    return kb


# =========================================================
# 4. HANDLERS: START and CALLBACKS
# =========================================================

@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    args = msg.text.split()

    ref = None
    if len(args) > 1 and args[1].isdigit():
        ref = int(args[1])
        if ref == uid:
            ref = None

    # This ensures the user (and referrer, if applicable) exists in Firebase
    ensure_user(uid, ref)

    bot.send_message(
        uid,
        "👋 Welcome!\nTo use the bot you must join all channels:",
        reply_markup=channels_keyboard()
    )


@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    uid = call.from_user.id
    
    # Always fetch the latest data for the current user
    user = get_user_data(uid)
    if not user:
         user = ensure_user(uid) # Safety check

    # Check subscription
    if call.data == "check":
        if check_all(uid):
            
            # --- Reward Logic ---
            ref = user.get("ref")
            
            if ref:
                # Get the referrer's data to check the invited list
                referrer_data = get_user_data(ref) 

                # Reward only if referrer exists AND user is NOT already in the referrer's invited list
                if referrer_data and str(uid) not in referrer_data.get("invited", []):
                     reward_referrer(uid, ref)

            bot.answer_callback_query(call.id, "You're in! 🎉")
            bot.send_message(uid, "🎉 Access granted!", reply_markup=menu_keyboard())
        else:
            bot.answer_callback_query(call.id, "❗ Not all channels joined", show_alert=True)
            bot.send_message(uid, "❗ You must join ALL channels:", reply_markup=channels_keyboard())

    # Referral Link
    elif call.data == "ref":
        bot_info = bot.get_me()
        bot.send_message(
            uid,
            f"🔗 Your personal link:\nhttps://t.me/{bot_info.username}?start={uid}"
        )

    # Points
    elif call.data == "points":
        # Re-fetch data for the absolute latest points
        current_user = get_user_data(uid) 
        
        invited_count = len(current_user.get("invited", []))

        bot.send_message(
            uid,
            f"📊 Your Points: {current_user['points']}\n"
            f"👥 Invited: {invited_count}"
        )
        
    # Always finish with an acknowledgement for the callback query
    else:
        bot.answer_callback_query(call.id, "Processing...")

# =========================================================
# 5. RUN
# =========================================================

if __name__ == '__main__':
    logging.info("Starting bot polling...")
    # Setting skip_pending=True ignores messages sent while the bot was offline
    bot.infinity_polling(skip_pending=True)