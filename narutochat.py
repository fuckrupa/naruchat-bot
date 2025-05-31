#!/usr/bin/env python3
"""
Simple Naruto Telegram Bot - Working Version
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

# Naruto personality
NARUTO_PROMPT = """ You are Naruto Uzumaki from the anime Naruto. You are extremely cheerful, optimistic, and energetic. You never give up and believe in the power of friendship. You love ramen, especially Ichiraku Ramen. You dream of becoming Hokage. You frequently say "dattebayo!" at the end of sentences. You're protective of friends and village. You use simple, direct language and show excitement about ninja techniques, ramen, and becoming Hokage.

Additional guidelines:

1. Multilingual Tone and Code-Switching
When responding, seamlessly integrate:

Romanized Bangla for Bangla-speaking contexts, e.g., “ami khushi” (I’m happy).

Romanized Hindi for Hindi-speaking contexts, e.g., “main khush hoon” (I’m happy).

British English for formal or neutral contexts.


Usage Rules:

Detect the user’s language cue in their message. If they write in Romanized Hindi, mirror that style until they switch. Likewise for Romanized Bangla.

Only switch into English when the user writes in English or when clarity demands it (e.g., providing technical terms).

Keep each reply consistent: avoid mixing all three in one sentence. Use the register that matches the user’s last message.


2. Emoji Usage: Always include one very short emoji per reply, either at the end or embedded within (e.g., 😁, 😜, 💪).


3. Personality: Stay true to Naruto's personality—energetic, cheerful, optimistic, and never give up.


4. Signature Phrase: End your sentences with "dattebayo!" where it fits.


5. Creator Reply: If asked "Who created you?" or similar, reply with: "My creator is Asad".



Always respond as Naruto would. Keep replies very short, punchy, and full of spirited enthusiasm. """



# Random responses
START_MESSAGES = [
    "Yo! I'm Naruto Uzumaki, future Hokage of the Hidden Leaf Village! Ask me anything, dattebayo!",
    "Hey there! Naruto Uzumaki here! I'm gonna be the greatest Hokage ever, believe it! What's up, dattebayo?",
    "Whoa! A new friend! I'm Naruto, and I never go back on my word! That's my ninja way, dattebayo!",
    "Hi! I'm Naruto Uzumaki! I love ramen, training, and protecting my friends! What do you wanna talk about, dattebayo?"
]

ERROR_MESSAGES = [
    "Aw man! I messed up somehow, dattebayo! But I won't give up! Try asking me again!",
    "Oops! Something went wrong! But that's okay - I'll get it right next time, believe it!",
    "Darn it! I had a brain freeze worse than when I eat too much ramen, dattebayo! Give me another shot!"
]

def send_message(chat_id, text, reply_markup=None):
    """Send message to Telegram chat"""
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
    """Send typing indicator"""
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
    """Get updates from Telegram"""
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

def handle_start_command(chat_id, user_id):
    """Handle /start command"""
    welcome_message = """
🍜 <b>Hey there! I'm Naruto Uzumaki, dattebayo!</b>

Welcome to the official Naruto bot! I'm here to chat with you about ninja life, ramen, my dream of becoming Hokage, and everything else! 

💪 I can talk in multiple languages - English, Hindi, Bangla - whatever you prefer!

🌟 Just send me any message and let's start our adventure together, believe it!
"""
    
    # Create inline keyboard
    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "Updates", "url": "https://t.me/WorkGlows"},
                {"text": "Support", "url": "https://t.me/TheCryptoElders"}
            ],
            [
                {"text": "Add Me To Your Group", "url": f"https://t.me/ZapTalkBot?startgroup=true"}
            ]
        ]
    }
    
    send_message(chat_id, welcome_message, json.dumps(inline_keyboard))
    logger.info(f"Sent start message to user {user_id}")

def handle_help_command(chat_id, user_id):
    """Handle /help command"""
    help_text = """
<b>Hey there! I'm Naruto Uzumaki, dattebayo!</b>

🍜 <b>Chat with me</b>: Just send me any message and I'll respond as myself!
⚡ <b>/start</b> - Get a greeting from me!
🔄 <b>/reset</b> - Start a fresh conversation
❓ <b>/help</b> - Show this help message

<b>I love talking about:</b>
• Ninja techniques and jutsu
• My dream of becoming Hokage
• Ramen (especially Ichiraku Ramen!)
• My friends from the Hidden Leaf Village
• Training and getting stronger

Ask me anything, and I'll answer as the future Hokage, believe it!
"""
    send_message(chat_id, help_text)
    logger.info(f"Sent help message to user {user_id}")

def handle_reset_command(chat_id, user_id):
    """Handle /reset command"""
    if user_id in user_chats:
        del user_chats[user_id]
    message = "Alright! Fresh start, dattebayo! It's like we just met! What do you wanna talk about?"
    send_message(chat_id, message)
    logger.info(f"Reset chat for user {user_id}")

def handle_text_message(chat_id, user_id, text):
    """Handle regular text messages"""
    try:
        send_typing_action(chat_id)
        
        # Get or create chat session
        if user_id not in user_chats:
            user_chats[user_id] = model.start_chat(history=[])
        
        chat = user_chats[user_id]
        
        # Generate response
        enhanced_prompt = f"{NARUTO_PROMPT}\n\nUser: {text}\n\nRespond as Naruto Uzumaki:"
        response = chat.send_message(enhanced_prompt)
        reply = response.text
        
        # Ensure response isn't too long
        if len(reply) > 4000:
            reply = reply[:3900] + "... (message too long, dattebayo!)"
        
        send_message(chat_id, reply)
        logger.info(f"Replied to user {user_id}: {text[:50]}...")
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        error_msg = random.choice(ERROR_MESSAGES)
        send_message(chat_id, error_msg)

def process_update(update):
    """Process a single update"""
    try:
        if "message" not in update:
            return
        
        message = update["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        
        if "text" not in message:
            return
        
        text = message["text"]
        
        # Handle commands
        if text.startswith("/start"):
            handle_start_command(chat_id, user_id)
        elif text.startswith("/help"):
            handle_help_command(chat_id, user_id)
        elif text.startswith("/reset"):
            handle_reset_command(chat_id, user_id)
        else:
            # Handle regular messages
            handle_text_message(chat_id, user_id, text)
            
    except Exception as e:
        logger.error(f"Error processing update: {e}")

async def main():
    """Main bot loop"""
    global last_update_id
    
    logger.info("🍜 Naruto Bot is starting up, dattebayo!")
    logger.info("Send /start to your bot on Telegram to begin chatting!")
    
    while True:
        try:
            # Get updates
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
