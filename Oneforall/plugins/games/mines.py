# ================== MINES + DAILY + PAY ==================

import random
import time
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pymongo import MongoClient

from Oneforall import app
from config import MONGO_DB_URI

# ================== CONFIG ==================
GRID = 4
MINES = 4
COOLDOWN = 86400

REWARDS = [500, 1000, 2000, 3200]
MULTIPLIER = [1.0, 1.2, 1.5, 2.0, 3.0, 5.0]

NO_BALANCE_VIDEO = "https://graph.org/file/384f9cbde98284c4ef320-d03d1daec0a682bc50.mp4"  # ← replace

# ================== DB ==================
mongo = MongoClient(MONGO_DB_URI)
db = mongo["musicbot"]
users_db = db["users"]

# ================== MEMORY ==================
games = {}

# ================== USER ==================
def get_user(user_id):
    user = users_db.find_one({"user_id": user_id})
    if not user:
        user = {"user_id": user_id, "coins": 1000, "last_daily": 0}
        users_db.insert_one(user)
    return user

def update_user(user_id, coins=None, last_daily=None):
    update = {}
    if coins is not None:
        update["coins"] = coins
    if last_daily is not None:
        update["last_daily"] = last_daily

    users_db.update_one({"user_id": user_id}, {"$set": update}, upsert=True)

# ================== TIME ==================
def format_time(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
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
    user = get_user(message.from_user.id)

    now = int(time.time())
    if now - user["last_daily"] < COOLDOWN:
        return await message.reply(
            f"⏳ ᴛʀʏ ᴀɢᴀɪɴ ɪɴ {format_time(COOLDOWN - (now - user['last_daily']))}"
        )

    reward = random.choice(REWARDS)
    update_user(
        message.from_user.id,
        coins=user["coins"] + reward,
        last_daily=now
    )

    await message.reply(f"🎁 +{reward} ᴄᴏɪɴs")

# ================== PAY ==================
@app.on_message(filters.command("pay") & filters.group)
async def pay(_, message: Message):
    if not message.reply_to_message:
        return await message.reply("ʀᴇᴘʟʏ ᴛᴏ ᴜsᴇʀ")

    try:
        amount = int(message.command[1])
    except:
        return await message.reply("ᴜsᴀɢᴇ: /pay 100")

    sender = get_user(message.from_user.id)

    if sender["coins"] < amount:
        return await message.reply_video(
            NO_BALANCE_VIDEO,
            caption="ᴀᴀʜᴇ sʜᴜᴛ ᴜᴘ ʙᴀᴋᴀ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴇɴᴏᴜɢʜ ʙᴀʟᴀɴᴄᴇ"
        )

    receiver_id = message.reply_to_message.from_user.id

    update_user(message.from_user.id, coins=sender["coins"] - amount)

    receiver = get_user(receiver_id)
    update_user(receiver_id, coins=receiver["coins"] + amount)

    await message.reply(f"💸 ᴛʀᴀɴsғᴇʀʀᴇᴅ {amount}")

# ================== MINES START ==================
@app.on_message(filters.command("mines"))
async def start_mines(_, message: Message):

    args = message.command

    if len(args) < 2:
        return await message.reply("ᴜsᴀɢᴇ: /mines 100")

    try:
        bet = int(args[1])
    except:
        return await message.reply("ɪɴᴠᴀʟɪᴅ ʙᴇᴛ")

    user = get_user(message.from_user.id)

    if user["coins"] < bet:
        return await message.reply_video(
            NO_BALANCE_VIDEO,
            caption="ᴀᴀʜᴇ sʜᴜᴛ ᴜᴘ ʙᴀᴋᴀ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴇɴᴏᴜɢʜ ʙᴀʟᴀɴᴄᴇ"
        )

    update_user(message.from_user.id, coins=user["coins"] - bet)

    game_id = f"{message.chat.id}_{message.id}"

    games[game_id] = {
        "user": message.from_user.id,
        "board": gen_board(),
        "revealed": {},
        "safe": 0,
        "bet": bet,
        "over": False
    }

    await message.reply(
        f"💣 ᴍɪɴᴇs\nʙᴇᴛ: {bet}",
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
        return await query.answer("ɴᴏᴛ ʏᴏᴜʀ", True)

    if game["over"]:
        return

    if idx in game["revealed"]:
        return

    val = game["board"][idx]
    game["revealed"][idx] = val

    if val == "💣":
        game["over"] = True
        return await query.message.edit_text(
            "💣 ʟᴏsᴛ",
            reply_markup=board_ui(game_id, show_all=True)
        )

    game["safe"] += 1
    multi = MULTIPLIER[min(game["safe"]-1, len(MULTIPLIER)-1)]
    reward = int(game["bet"] * multi)

    await query.message.edit_text(
        f"✅ sᴀғᴇ\nx{multi}\n💰 {reward}",
        reply_markup=board_ui(game_id, game["revealed"])
    )

# ================== CASHOUT ==================
@app.on_callback_query(filters.regex("^cashout_"))
async def cashout(_, query: CallbackQuery):
    _, game_id = query.data.split("_")

    game = games.get(game_id)
    if not game:
        return

    multi = MULTIPLIER[min(game["safe"]-1, len(MULTIPLIER)-1)]
    reward = int(game["bet"] * multi)

    user = get_user(game["user"])
    update_user(game["user"], coins=user["coins"] + reward)

    game["over"] = True

    await query.message.edit_text(
        f"💰 ᴄᴀsʜᴏᴜᴛ\n+{reward}",
        reply_markup=board_ui(game_id, show_all=True)
    )

# ================== RESTART ==================
@app.on_callback_query(filters.regex("^restart_"))
async def restart(_, query: CallbackQuery):
    _, game_id = query.data.split("_")

    game = games.get(game_id)
    if not game:
        return

    games[game_id] = {
        "user": game["user"],
        "board": gen_board(),
        "revealed": {},
        "safe": 0,
        "bet": game["bet"],
        "over": False
    }

    await query.message.edit_text(
        "🔄 ʀᴇsᴛᴀʀᴛᴇᴅ",
        reply_markup=board_ui(game_id)
        )
