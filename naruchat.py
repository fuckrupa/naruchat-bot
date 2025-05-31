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

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    logger.error("TELEGRAM_TOKEN and GEMINI_API_KEY must be set.")
    exit(1)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Store chat sessions
user_chats = {}
last_update_id = 0

# Sakura personality
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

# Random responses (Sakura-themed)
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

def send_message(chat_id, text, reply_markup=None):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            data["reply_markup"] = reply_markup
        response = requests.post(url, json=data)
        return response.json()
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

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

def set_my_commands():
    """Register bot commands with Telegram"""
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
    send_message(chat_id, welcome_message, json.dumps(inline_keyboard))
    logger.info(f"Sent start message to user {user_id}")

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
    logger.info(f"Sent help message to user {user_id}")

def handle_text_message(chat_id, user_id, text):
    try:
        send_typing_action(chat_id)

        if user_id not in user_chats:
            user_chats[user_id] = model.start_chat(history=[])

        chat = user_chats[user_id]

        # Construct a new “conversation prompt” that forces the model
        # to stay in Sakura’s character
        enhanced_prompt = f"{SAKURA_PROMPT}\n\nUser: {text}\n\nRespond as Sakura Haruno:"
        response = chat.send_message(enhanced_prompt)
        reply = response.text

        if len(reply) > 4000:
            reply = reply[:3900] + "... (message too long, sorry!) 😊"

        send_message(chat_id, reply)
        logger.info(f"Replied to user {user_id}: {text[:50]}...")

    except Exception as e:
        logger.error(f"Error handling message: {e}")
        error_msg = random.choice(ERROR_MESSAGES)
        send_message(chat_id, error_msg)

def process_update(update):
    try:
        if "message" not in update:
            return

        message = update["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]

        if "text" not in message:
            return

        text = message["text"]

        if text.startswith("/start"):
            handle_start_command(chat_id, user_id)
        elif text.startswith("/help"):
            handle_help_command(chat_id, user_id)
        else:
            handle_text_message(chat_id, user_id, text)

    except Exception as e:
        logger.error(f"Error processing update: {e}")

async def main():
    global last_update_id

    logger.info("🌸 Sakura Bot is starting up!")
    logger.info("Send /start to your bot on Telegram to begin chatting!")

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