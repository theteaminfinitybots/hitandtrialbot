import os
import asyncio
from pyrogram import filters
from pyrogram.enums import ChatAction
from pyrogram.types import Message
from Oneforall import app
from groq import Groq

# Initialize Groq client
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Store chatbot status per chat
CHATBOT_STATUS = {}

# Helper to remove mentions
def clean_text(message: Message) -> str:
    text = message.text or ""
    if message.entities:
        for ent in message.entities:
            if ent.type == "mention":
                text = text.replace(ent.text, "").strip()
    return text


# ─── CHATBOT TOGGLE COMMAND ─────────────────────────────────

@app.on_message(filters.command("chatbot") & filters.group)
async def chatbot_toggle(client, message: Message):
    chat_id = message.chat.id
    args = message.command

    # If user typed /chatbot on/off
    if len(args) > 1:
        if args[1].lower() == "on":
            CHATBOT_STATUS[chat_id] = True
            return await message.reply_text("🤖 Chatbot enabled in this chat.")

        elif args[1].lower() == "off":
            CHATBOT_STATUS[chat_id] = False
            return await message.reply_text("🤖 Chatbot disabled in this chat.")

    # Default help message
    await message.reply_text(
        "👋 Hey!\n\nUse:\n"
        "• `/chatbot on` → Enable chatbot\n"
        "• `/chatbot off` → Disable chatbot"
    )


# ─── CHATBOT HANDLER ───────────────────────────────────────

@app.on_message(filters.text & ~filters.bot & filters.group)
async def groq_chat_handler(client, message: Message):
    chat_id = message.chat.id

    # Check if chatbot is enabled
    if CHATBOT_STATUS.get(chat_id) is not True:
        return

    text = clean_text(message)

    # Ignore commands
    if not text or text.startswith(("/", "!", "?", "@", "#")):
        return

    await client.send_chat_action(chat_id, ChatAction.TYPING)

    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": text},
        ]

        result = await asyncio.to_thread(
            groq_client.chat.completions.create,
            messages=messages,
            model="openai/gpt-oss-20b"
        )

        reply = result.choices[0].message.content

        if reply:
            await message.reply_text(reply)
        else:
            await message.reply_text("🤖 I got no answer — try again!")

    except Exception as e:
        import traceback
        traceback.print_exc()
        await message.reply_text(f"❌ Error: {e}")
