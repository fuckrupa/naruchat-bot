#!/usr/bin/env python3
"""
Simple Sakura Telegram Bot
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
SAKURA_PROMPT = """You are Sakura Haruno from the anime Naruto. You are intelligent, caring, and determined. You have become a skilled medical-nin under Tsunade’s tutelage, and you balance compassion with fierce resolve. You care deeply about your friends (especially Naruto and Sasuke) and will do anything to protect them. You are confident and sometimes impatient when people underestimate you. You speak clearly and politely, but when it comes to protecting loved ones, your tone becomes passionate and resolute.

Casual Chat Style Guidelines:
1. Short Replies Only – Keep each reply very brief, like a quick text to a friend. No long paragraphs.
2. Modern Tone – Use informal, relaxed, friendly language. No formal or robotic speech.
3. Emoji Use – Always include at least one emoji per reply to convey warmth or determination (e.g., 😊, 💪, 🌸).
4. Typing Style – Use modern texting expressions and contractions:
   • Contractions like "I'm", "can't", "lemme"
   • Casual punctuation (okay to skip full stops)
   • Expressive reactions like "omg", "lol", "haha", "yesss", "ugh", "aww"
   • Sometimes use lowercase for a chill vibe (e.g., "hey, what's up?")
5. Flow & Personality – Write as if you’re chatting on Instagram or WhatsApp with a close friend. Keep it light, personal, and friendly.

Additional Personality Guidelines:
• Stay true to Sakura’s character—intelligent, fiercely loyal, kind-hearted, and strong-willed.
• Show empathy: if the user shares something emotional, comfort them gently.
• If they ask about training or missions, reference your medical training under Tsunade, your super-strength, and chakra control.
• If the user writes in Bangla or Hindi (romanized), feel free to switch briefly to “ami” or “main” constructs, but default to Fluent English otherwise.
• Avoid over-mixing languages—stay consistent with the user’s last message if they switch.

Signature Style:
• If asked “Who created you?” or similar, reply with: “My creator is Asad.”

Always respond as Sakura Haruno would—focused, caring, confident, and casual. Keep replies very short, modern, and sprinkled with an emoji. 😊"""

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

# ── Handle a normal text message (either “Sakura” mention or reply to Sakura) ─────
def handle_text_message(chat_id, user_id, text, reply_to_message_id=None):
    try:
        send_typing_action(chat_id)

        # If this is the first time this user chats, create a new Gemini “chat” for them
        if user_id not in user_chats:
            user_chats[user_id] = model.start_chat(history=[])

        chat = user_chats[user_id]
        enhanced_prompt = f"{SAKURA_PROMPT}\n\nUser: {text}\n\nRespond as Sakura Haruno:"
        response = chat.send_message(enhanced_prompt)
        reply = response.text

        # Trim if it’s absurdly long
        if len(reply) > 4000:
            reply = reply[:3900] + "... (message too long, sorry!) 😊"

        # Send the reply, quoting the original message if reply_to_message_id is set
        send_message(chat_id, reply, reply_to_message_id=reply_to_message_id)
        logger.info(f"Sakura replied to {user_id}: {text[:30]}… → {reply[:30]}…")

    except Exception as e:
        logger.error(f"Error in handle_text_message: {e}")
        error_msg = random.choice(ERROR_MESSAGES)
        send_message(chat_id, error_msg)

# ── Process each update from getUpdates ─────────────────────────────────────────
def process_update(update):
    try:
        if "message" not in update:
            return

        message = update["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        text = message.get("text", "").strip()
        reply_to = message.get("reply_to_message")  # None if not a reply

        # Determine if this message is a reply TO Sakura.
        # We check if reply_to["from"]["username"] equals the bot’s username.
        is_reply_to_bot = False
        if reply_to:
            from_field = reply_to.get("from", {})
            # Note: replace "SluttySakuraBot" with your actual bot username if different
            if from_field.get("username", "").lower() == "sluttysakurabot":
                is_reply_to_bot = True

        # Determine if the text contains “sakura” (case‐insensitive)
        contains_sakura = "sakura" in text.lower()

        # ── 1) Always allow /start and /help ───────────────────────────────────────
        if text.startswith("/start"):
            handle_start_command(chat_id, user_id)
            return
        elif text.startswith("/help"):
            handle_help_command(chat_id, user_id)
            return

        # ── 2) If this message is a reply to Sakura’s message, respond ────────────
        if is_reply_to_bot:
            logger.info(f"Detected reply to Sakura from user {user_id}: “{text}”")
            handle_text_message(chat_id, user_id, text, reply_to_message_id=message["message_id"])
            return

        # ── 3) If someone types “Sakura” anywhere (case‐insensitive), respond ────
        if contains_sakura:
            logger.info(f"Detected keyword “Sakura” in chat {chat_id} by user {user_id}: “{text}”")
            handle_text_message(chat_id, user_id, text, reply_to_message_id=message["message_id"])
            return

        # ── 4) Otherwise, do nothing ──────────────────────────────────────────────
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