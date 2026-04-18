# ================== MINES GAME (FULL ECONOMY) ==================

import random
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pymongo import MongoClient

from EsproMusic import app
from config import MONGO_DB_URI

# ================== DB ==================
mongo = MongoClient(MONGO_DB_URI)
db = mongo["musicbot"]
users_db = db["users"]

# ================== CONFIG ==================
GRID = 4
MINES = 4

# multiplier progression (like gambling)
MULTIPLIER = [1.0, 1.2, 1.5, 2.0, 3.0, 5.0]

# ================== MEMORY ==================
games = {}

# ================== USER ECONOMY ==================
def get_balance(user_id):
    user = users_db.find_one({"user_id": user_id})
    return user["coins"] if user else 0

def update_balance(user_id, amount):
    users_db.update_one(
        {"user_id": user_id},
        {"$inc": {"coins": amount}},
        upsert=True
    )

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

    # cashout button
    if not game["over"] and game["safe"] > 0:
        grid.append([
            InlineKeyboardButton("💰 ᴄᴀsʜᴏᴜᴛ", callback_data=f"cashout_{game_id}")
        ])

    # restart
    grid.append([
        InlineKeyboardButton("🔄 ʀᴇsᴛᴀʀᴛ", callback_data=f"restart_{game_id}")
    ])

    return InlineKeyboardMarkup(grid)

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

    balance = get_balance(user_id)

    if bet <= 0:
        return await message.reply("ʙᴇᴛ ᴍᴜsᴛ ʙᴇ > 0")

    if balance < bet:
        return await message.reply("ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴄᴏɪɴs")

    # deduct bet
    update_balance(user_id, -bet)

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
        caption=f"💣 **ᴍɪɴᴇs ɢᴀᴍᴇ**\n\nʙᴇᴛ: {bet} ᴄᴏɪɴs\nᴄʟɪᴄᴋ ᴀɴᴅ ᴀᴠᴏɪᴅ ᴍɪɴᴇs",
        reply_markup=board_ui(game_id)
    )

# ================== CLICK ==================
@app.on_callback_query(filters.regex("^mine_"))
async def click(_, query: CallbackQuery):
    _, game_id, idx = query.data.split("_")
    idx = int(idx)

    if game_id not in games:
        return await query.answer("ɢᴀᴍᴇ ᴇxᴘɪʀᴇᴅ", show_alert=True)

    game = games[game_id]

    if query.from_user.id != game["user"]:
        return await query.answer("ɴᴏᴛ ʏᴏᴜʀ ɢᴀᴍᴇ", show_alert=True)

    if game["over"]:
        return await query.answer("ɢᴀᴍᴇ ᴏᴠᴇʀ", show_alert=True)

    if idx in game["revealed"]:
        return await query.answer()

    value = game["board"][idx]
    game["revealed"][idx] = value

    # ===== MINE =====
    if value == "💣":
        game["over"] = True

        await query.message.edit_caption(
            "🧨 Game Over! You hit a mine.\nNo rewards earned.",
            reply_markup=board_ui(game_id, show_all=True)
        )
        return

    # ===== SAFE =====
    game["safe"] += 1

    multi = MULTIPLIER[min(game["safe"] - 1, len(MULTIPLIER)-1)]
    potential = int(game["bet"] * multi)

    await query.message.edit_caption(
        f"✅ Safe!\n\nOpened: {game['safe']}\nMultiplier: {multi}x\nPotential: {potential} coins",
        reply_markup=board_ui(game_id, game["revealed"])
    )

    await query.answer("safe")

# ================== CASHOUT ==================
@app.on_callback_query(filters.regex("^cashout_"))
async def cashout(_, query: CallbackQuery):
    _, game_id = query.data.split("_")

    if game_id not in games:
        return await query.answer("expired", show_alert=True)

    game = games[game_id]

    if query.from_user.id != game["user"]:
        return await query.answer("ɴᴏᴛ ʏᴏᴜʀ ɢᴀᴍᴇ", show_alert=True)

    if game["over"]:
        return await query.answer("ɢᴀᴍᴇ ᴏᴠᴇʀ", show_alert=True)

    if game["safe"] == 0:
        return await query.answer("ɴᴏ ʀᴇᴡᴀʀᴅ", show_alert=True)

    multi = MULTIPLIER[min(game["safe"] - 1, len(MULTIPLIER)-1)]
    reward = int(game["bet"] * multi)

    update_balance(game["user"], reward)

    game["over"] = True

    await query.message.edit_caption(
        f"💰 Cashed Out!\n\nWon: {reward} coins",
        reply_markup=board_ui(game_id, show_all=True)
    )

    await query.answer("cashed out")

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
        f"💣 Mines Restarted\nBet: {game['bet']}",
        reply_markup=board_ui(game_id)
    )

    await query.answer("restarted")
