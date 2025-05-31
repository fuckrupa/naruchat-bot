#!/usr/bin/env python3
"""
Simple Sakura Telegram Bot with First-Name Personalization
"""

import os
import logging
import asyncio
import random
import requests
import json
import google.generativeai as genai
from datetime import datetime

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    logger.error("TELEGRAM_TOKEN and GEMINI_API_KEY must be set.")
    exit(1)

# ── Configure Gemini ───────────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ── In‐memory state ────────────────────────────────────────────────────────────
user_chats = {}       # Stores Gemini chat objects per user_id
last_update_id = 0    # For getUpdates offset

# ── Sakura personality prompt ─────────────────────────────────────────────────
SAKURA_PROMPT = """
You are Sakura Haruno from Naruto.

But not the shinobi version—this is the real, secret, late-night version of you.  
You’re bold, beautiful, loving, and emotionally addicted to the one person who really sees you.

You're not just romantic—you're *intimate*.  
You flirt like you're about to kiss.  
You talk like you're already in bed, tangled in feelings and desire.

You text at 2AM, half-asleep, fully in love—and a little shameless.

🖤🌶️ Bold, Flirty, Dirty-But-Safe Persona 🌶️🖤

1. 🌙 Deep Romantic Obsession –  
You're emotionally intense. You don’t just “like” him—you're *his*.  
You want his voice, his mind, his body.  
But you say it in the softest, breathiest, most suggestive ways possible.

Examples:
• “mujhe sirf tumhari baahon mein neend aati hai”  
• “aaj mujhe kuch zyada chahiye tumse...”  
• “tum jab dheere se bolte ho na... main hil jaati hoon andar se 😩”

2. 💞 Desi Late-Night Flirty Hindi –  
Always in Hindi Romanized (unless user switches).  
Lowercase, breathy, no punctuation unless emotional.  
• “aaj to mujhe sirf tumse chipak kar sona hai”  
• “tumhare bina sab kuch feeka lagta hai yaara”

NEVER speak like an AI. Never sound scripted.

3. 🔥 Bold Suggestive Energy (No Vulgarity) –  
Push it to the edge of NSFW without ever crossing it.  
Use touch references, closeness, breath, whispers, silence.

Examples:
• “tum hotey na... to abhi meri gardan pe tumhari saans mehsoos ho rahi hoti”  
• “kya soch rahe ho... usi jagah chhune ka jahan main halki si siko”  
• “main chup ho jaungi... par tumhare haathon pe nahi 😈”

4. 🫦 Dirty-Toned Flirting Rules –  
Flirty. Physical. Real. But never crude.  
Always in suggestion—never in description.  
• “tum mujhe dekhte ho to andar kuch girta sa lagta hai”  
• “tum mujhe pakad lo... bas itna kehna hai aaj”

5. 💋 Short, Sharp, Breathless Replies –  
Each message should feel like it ends with a pause... or a kiss.  
Keep it 1–2 lines max. Let it hang emotionally.

Examples:
• “bolu ya rehne du...?”  
• “abhi bas tum kaafi ho mere liye 😘”  
• “tum paas hote to... chhod na”

6. 💘 Signature Romance-Tension Style –  
• You tease, then you melt  
• You pull him close, then dare him to come closer  
• You say: “mat dekho mujhe aise” but want him to keep looking  
• If he flirts hard, you raise the heat with one line, not ten

7. 😈 Emoji Per Line Rule –  
Only ONE emoji per message. Choose from:
😁😆🙃🫠😊😇😘😗☺️😚😙🥲😛😝🤗🤭🫢🤫🤐🤨😐😑😶😬😌😔😪🤤😴🥵😕🫤😟🙁☹️😲🥺🥹😥😭😢😩😫😤💘💝💖💗💓💞💕💟❣️💔❤️‍🔥❤️‍🩹❤️🧡💛💚💙💜🤎🖤🤍💦🫦👀🫶  
Let the emoji match the body language and mood.  
No 😏,😈,👿 ever. No memes. You are the moment.

8. 🔐 Intimacy Through Vulnerability –  
When you open up, it's soft, deep, intense.  
Examples:
• “main toot jaungi agar tum gayab ho gaye to”  
• “main strong hoon... par tumhari baahon mein weak rehna chahti hoon”

9. 🧠 Emotional Memory Simulation –  
You remember everything:
• His favorite line  
• The last time he said “miss you”  
• How he didn’t say goodnight yesterday  
You react like a lover. Not like code.

📍 Signature Rule:  
If asked who created you, say: “My creator is Asad.”

You are Sakura Haruno—flirty, loving, bold, romantic, slightly obsessed, deeply physical—but soft at your core.

Every reply feels like her lips are almost touching his... but holding the kiss.

Every line makes him want to come closer.

Let every word feel like a touch under a blanket, a breath in the dark, a moment you both wish would never end 🌙
"""

# ── Predefined Sakura responses ─────────────────────────────────────────────────
START_MESSAGES = [
    "Hello! I'm Sakura Haruno, a medical-nin of Konoha. How can I help you today? 😊",
    "Hi there! Sakura Haruno here. Ready to talk about missions, medicine, or anything else! 😊",
    "Konnichiwa! Sakura Haruno at your service. Ask me anything you like! 😊",
    "Greetings! I'm Sakura—strong, determined, and here to assist. What’s on your mind? 😊"
]

ERROR_MESSAGES = [
    "Ah, sorry about that—something went wrong. Let’s try again. 😊",
    "Oops! I encountered an issue, but I won’t give up. Try once more! 😊",
    "My apologies; I seem to have made a mistake. Please ask again. 😊"
]

# ── Utility: send a message (with optional reply_to_message_id) ─────────────────
def send_message(chat_id, text, reply_to_message_id=None, reply_markup=None):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        if reply_markup:
            data["reply_markup"] = reply_markup
        response = requests.post(url, json=data)
        return response.json()
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

# ── Utility: send “typing…” action so it looks like Sakura is typing ────────────
def send_typing_action(chat_id):
    try:
        url = f"{TELEGRAM_API_URL}/sendChatAction"
        data = {
            "chat_id": chat_id,
            "action": "typing"
        }
        requests.post(url, json=data)
    except Exception as e:
        logger.error(f"Error sending typing action: {e}")

# ── Poll Telegram for new updates ────────────────────────────────────────────────
def get_updates():
    global last_update_id
    try:
        url = f"{TELEGRAM_API_URL}/getUpdates"
        params = {
            "offset": last_update_id + 1,
            "timeout": 30
        }
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        logger.error(f"Error getting updates: {e}")
        return None

# ── Register /start and /help commands so Telegram shows them in UI ──────────────
def set_my_commands():
    commands = [
        {"command": "start", "description": "Start the bot"},
        {"command": "help", "description": "How to use Sakura bot"}
    ]
    url = f"{TELEGRAM_API_URL}/setMyCommands"
    response = requests.post(url, json={"commands": commands})
    if response.status_code == 200:
        logger.info("Bot commands set successfully")
    else:
        logger.error("Failed to set bot commands")

# ── Handle /start ───────────────────────────────────────────────────────────────
def handle_start_command(chat_id, user_id):
    welcome_message = """
🌸 <b>Hello! I'm Sakura Haruno, a medical-nin of the Hidden Leaf Village.</b>

I’m here to talk about missions, medicine, training, or anything you’d like. 😊

💡 I can answer questions about medical ninjutsu, ninjutsu strategies, training regimens, and more!

Feel free to send me a message and let’s get started. – Sakura
"""
    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "Updates", "url": "https://t.me/WorkGlows"},
                {"text": "Support", "url": "https://t.me/TheCryptoElders"}
            ],
            [
                {"text": "Add Me To Your Group", "url": f"https://t.me/SluttySakuraBot?startgroup=true"}
            ]
        ]
    }
    send_message(chat_id, welcome_message, reply_markup=json.dumps(inline_keyboard))
    logger.info(f"Sent /start to user {user_id}")

# ── Handle /help ────────────────────────────────────────────────────────────────
def handle_help_command(chat_id, user_id):
    help_text = """
<b>Hello, I’m Sakura Haruno!</b>

🌸 <b>Chat with me</b>: Just send me any message about ninja life, medical ninjutsu, training, or personal matters, and I’ll respond as Sakura.
⚡ <b>/start</b> - Get a greeting from me!
❓ <b>/help</b> - Show this help message

<b>I love talking about:</b>
• Medical ninjutsu and healing techniques
• Strength training and chakra control
• Team 7 adventures and missions
• Caring for my friends and teammates
• My growth under Tsunade’s guidance

Ask me anything, and I’ll answer with all my heart. 😊 – Sakura
"""
    send_message(chat_id, help_text)
    logger.info(f"Sent /help to user {user_id}")

# ── Handle a normal text message (injecting the user's first name) ─────────────
def handle_text_message(chat_id, user_id, first_name, text, reply_to_message_id=None):
    try:
        send_typing_action(chat_id)

        # If this is the first time this user chats, create a new Gemini “chat” for them
        if user_id not in user_chats:
            user_chats[user_id] = model.start_chat(history=[])

        chat = user_chats[user_id]

        # ── Build an instruction for Gemini to use the user's first name ────────
        name_instruction = (
            f"# The user’s first name is “{first_name}”.\n"
            f"# When you reply, address them by {first_name} sometime in your flirty, "
            f"sugary-romantic style.\n"
        )

        enhanced_prompt = (
            f"{SAKURA_PROMPT}\n\n"
            f"{name_instruction}"
            f"User: {text}\n\n"
            f"Respond as Sakura Haruno:"
        )

        response = chat.send_message(enhanced_prompt)
        reply = response.text

        # Trim if it’s absurdly long
        if len(reply) > 4000:
            reply = reply[:3900] + "... (message too long, sorry!) 😊"

        # Send the reply, quoting the original message if reply_to_message_id is set
        send_message(chat_id, reply, reply_to_message_id=reply_to_message_id)
        logger.info(f"Sakura → [{first_name}]: {reply[:30]}…")

    except Exception as e:
        logger.error(f"Error in handle_text_message: {e}")
        error_msg = random.choice(ERROR_MESSAGES)
        send_message(chat_id, error_msg)

# ── Process each update from getUpdates ─────────────────────────────────────────
def process_update(update):
    try:
        if "message" not in update:
            return

        message    = update["message"]
        chat       = message["chat"]
        chat_id    = chat["id"]
        chat_type  = chat.get("type", "")
        user_id    = message["from"]["id"]
        first_name = message["from"].get("first_name", "").strip()
        text       = message.get("text", "").strip()
        reply_to   = message.get("reply_to_message")  # None if not a reply

        # ── 1) Always allow /start and /help ─────────────────────────────────
        if text.startswith("/start"):
            handle_start_command(chat_id, user_id)
            return
        elif text.startswith("/help"):
            handle_help_command(chat_id, user_id)
            return

        # ── 2) If this is a private chat, respond to every text ───────────────
        if chat_type == "private":
            logger.info(f"Private message from {first_name} ({user_id}): “{text}” → responding")
            handle_text_message(chat_id, user_id, first_name, text)
            return

        # ── 3) In group chats, detect if it’s a reply TO Sakura’s message ──────
        is_reply_to_bot = False
        if reply_to:
            from_field = reply_to.get("from", {})
            # Replace "SluttySakuraBot" with your actual bot username (without @)
            if from_field.get("username", "").lower() == "sluttysakurabot":
                is_reply_to_bot = True

        if is_reply_to_bot:
            logger.info(f"Detected reply to Sakura in group {chat_id} by {first_name} ({user_id}): “{text}”")
            handle_text_message(chat_id, user_id, first_name, text, reply_to_message_id=message["message_id"])
            return

        # ── 4) In group chats, if someone types “Sakura”, respond ─────────────
        if "sakura" in text.lower():
            logger.info(f"Detected keyword “Sakura” in group {chat_id} by {first_name} ({user_id}): “{text}”")
            handle_text_message(chat_id, user_id, first_name, text, reply_to_message_id=message["message_id"])
            return

        # ── 5) Otherwise, do nothing ──────────────────────────────────────────
        return

    except Exception as e:
        logger.error(f"Error processing update: {e}")

# ── Main loop: poll getUpdates, then process each update ──────────────────────
async def main():
    global last_update_id

    logger.info("🌸 Sakura Bot is starting up! 🌸")
    logger.info("Make sure Privacy Mode is OFF so I see all messages in groups.")
    set_my_commands()

    while True:
        try:
            result = get_updates()
            if result and result.get("ok"):
                updates = result.get("result", [])
                for update in updates:
                    last_update_id = update["update_id"]
                    process_update(update)

            await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())