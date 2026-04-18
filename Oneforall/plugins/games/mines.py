# ================== MINES + DAILY SYSTEM ==================

import random
import time
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pymongo import MongoClient

from Oneforall import app
from config import MONGO_DB_URI

# ================== DB ==================
mongo = MongoClient(MONGO_DB_URI)
db = mongo["musicbot"]
users_db = db["users"]

# ================== CONFIG ==================
GRID = 4
MINES = 4
COOLDOWN = 86400

REWARDS = [500, 1000, 2000, 3200]
MULTIPLIER = [1.0, 1.2, 1.5, 2.0, 3.0, 5.0]

# ================== MEMORY ==================
games = {}

# ================== USER ==================
def get_user(user_id):
    user = users_db.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "coins": 1000,
            "last_daily": 0
        }
        users_db.insert_one(user)
    return user

def update_user(user_id, coins=None, last_daily=None):
    update = {}
    if coins is not None:
        update["coins"] = coins
    if last_daily is not None:
        update["last_daily"] = last_daily

    users_db.update_one(
        {"user_id": user_id},
        {"$set": update},
        upsert=True
    )

# ================== TIME ==================
def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}h {m}m"

# ================== BOARD ==================
def gen_board():
    board = ["💎"] * (GRID * GRID)
    for i in random.sample(range(len(board)), MINES):
        board[i] = "💣"
    return board

# ================== UI ==================
def board_ui(game_id, revealed={}, show_all=False):
    game = games[game_id]

    buttons = []
    for i in range(GRID * GRID):
        if show_all:
            text = game["board"][i]
        elif i in revealed:
            text = revealed[i]
        else:
            text = "▫️"

        buttons.append(
            InlineKeyboardButton(text, callback_data=f"mine_{game_id}_{i}")
        )

    grid = [buttons[i:i+GRID] for i in range(0, len(buttons), GRID)]

    if not game["over"] and game["safe"] > 0:
        grid.append([
            InlineKeyboardButton("💰 ᴄᴀsʜᴏᴜᴛ", callback_data=f"cashout_{game_id}")
        ])

    grid.append([
        InlineKeyboardButton("🔄 ʀᴇsᴛᴀʀᴛ", callback_data=f"restart_{game_id}")
    ])

    return InlineKeyboardMarkup(grid)

# ================== BALANCE ==================
@app.on_message(filters.command("balance"))
async def balance(_, message: Message):
    user = get_user(message.from_user.id)
    await message.reply(f"💰 ʙᴀʟᴀɴᴄᴇ: {user['coins']}")

# ================== DAILY ==================
@app.on_message(filters.command("daily"))
async def daily(_, message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    now = int(time.time())
    last = user.get("last_daily", 0)

    if now - last < COOLDOWN:
        remaining = COOLDOWN - (now - last)
        return await message.reply(
            f"⏳ ᴀʟʀᴇᴀᴅʏ ᴄʟᴀɪᴍᴇᴅ\nᴛʀʏ ᴀɢᴀɪɴ ɪɴ {format_time(remaining)}"
        )

    reward = random.choice(REWARDS)
    new_balance = user["coins"] + reward

    update_user(user_id, coins=new_balance, last_daily=now)

    await message.reply(
        f"🎁 ᴅᴀɪʟʏ ᴄʟᴀɪᴍᴇᴅ\n💰 +{reward}\n🏦 ʙᴀʟᴀɴᴄᴇ: {new_balance}"
    )

# ================== START ==================
@app.on_message(filters.command("mines") & filters.group)
async def start_mines(_, message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2:
        return await message.reply("ᴜsᴀɢᴇ: /mines <bet>")

    try:
        bet = int(args[1])
    except:
        return await message.reply("ɪɴᴠᴀʟɪᴅ ʙᴇᴛ")

    user = get_user(user_id)

    if bet <= 0:
        return await message.reply("ʙᴇᴛ ᴍᴜsᴛ ʙᴇ > 0")

    if user["coins"] < bet:
        return await message.reply("ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴄᴏɪɴs")

    update_user(user_id, coins=user["coins"] - bet)

    game_id = f"{message.chat.id}_{message.id}"

    games[game_id] = {
        "user": user_id,
        "board": gen_board(),
        "revealed": {},
        "safe": 0,
        "bet": bet,
        "over": False
    }

    await message.reply_photo(
        photo="https://files.catbox.moe/0n0qrm.jpg",
        caption=f"💣 ᴍɪɴᴇs\nʙᴇᴛ: {bet}",
        reply_markup=board_ui(game_id)
    )

# ================== CLICK ==================
@app.on_callback_query(filters.regex("^mine_"))
async def click(_, query: CallbackQuery):
    _, game_id, idx = query.data.split("_")
    idx = int(idx)

    if game_id not in games:
        return await query.answer("ᴇxᴘɪʀᴇᴅ", True)

    game = games[game_id]

    if query.from_user.id != game["user"]:
        return await query.answer("ɴᴏᴛ ʏᴏᴜʀ ɢᴀᴍᴇ", True)

    if game["over"]:
        return await query.answer("ɢᴀᴍᴇ ᴏᴠᴇʀ", True)

    if idx in game["revealed"]:
        return await query.answer()

    value = game["board"][idx]
    game["revealed"][idx] = value

    if value == "💣":
        game["over"] = True
        await query.message.edit_caption(
            "💣 ʏᴏᴜ ʟᴏsᴛ!",
            reply_markup=board_ui(game_id, show_all=True)
        )
        return

    game["safe"] += 1
    multi = MULTIPLIER[min(game["safe"] - 1, len(MULTIPLIER)-1)]
    potential = int(game["bet"] * multi)

    await query.message.edit_caption(
        f"✅ sᴀғᴇ\nx{multi}\n💰 {potential}",
        reply_markup=board_ui(game_id, game["revealed"])
    )

# ================== CASHOUT ==================
@app.on_callback_query(filters.regex("^cashout_"))
async def cashout(_, query: CallbackQuery):
    _, game_id = query.data.split("_")

    if game_id not in games:
        return await query.answer("ᴇxᴘɪʀᴇᴅ", True)

    game = games[game_id]

    if query.from_user.id != game["user"]:
        return await query.answer("ɴᴏᴛ ʏᴏᴜʀ", True)

    if game["safe"] == 0:
        return await query.answer("ɴᴏ ʀᴇᴡᴀʀᴅ", True)

    multi = MULTIPLIER[min(game["safe"] - 1, len(MULTIPLIER)-1)]
    reward = int(game["bet"] * multi)

    user = get_user(game["user"])
    update_user(game["user"], coins=user["coins"] + reward)

    game["over"] = True

    await query.message.edit_caption(
        f"💰 ᴄᴀsʜᴏᴜᴛ\n+{reward}",
        reply_markup=board_ui(game_id, show_all=True)
    )

# ================== RESTART ==================
@app.on_callback_query(filters.regex("^restart_"))
async def restart(_, query: CallbackQuery):
    _, game_id = query.data.split("_")

    if game_id not in games:
        return await query.answer()

    game = games[game_id]

    games[game_id] = {
        "user": game["user"],
        "board": gen_board(),
        "revealed": {},
        "safe": 0,
        "bet": game["bet"],
        "over": False
    }

    await query.message.edit_caption(
        f"🔄 ʀᴇsᴛᴀʀᴛ\nʙᴇᴛ: {game['bet']}",
        reply_markup=board_ui(game_id)
            )
