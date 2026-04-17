from Oneforall import app
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from collections import defaultdict
import asyncio

games = {}
leaderboards = defaultdict(lambda: defaultdict(int))

PREFIXES = ["/", ".", "!"]
OPTIONS = ["rock", "paper", "scissors"]

RPS_VID = "https://graph.org/file/67cbd06e1fbe457ef213d-476182eec039c155bb.mp4"

def sc(text):
    normal = "abcdefghijklmnopqrstuvwxyz"
    small = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    result = ""
    for ch in text:
        if ch.lower() in normal:
            result += small[normal.index(ch.lower())]
        else:
            result += ch
    return result

@app.on_message(filters.command("rps2", prefixes=PREFIXES) & filters.group)
async def rps_panel(client, message):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎊 join game", callback_data="rps_join")]]
    )
    msg = await message.reply_text(sc("rps game panel\nclick to join"), reply_markup=keyboard)

    games[msg.id] = {
        "players": [],
        "choices": {},
        "message": msg,
        "started": False
    }

@app.on_callback_query(filters.regex("^rps_join$"))
async def join_game(client, cq):
    game = games.get(cq.message.id)
    user = cq.from_user

    if not game:
        return await cq.answer("expired", show_alert=True)

    if user.id in game["players"]:
        return await cq.answer("already joined", show_alert=True)

    if len(game["players"]) >= 2:
        return await cq.answer("game full", show_alert=True)

    game["players"].append(user.id)

    if len(game["players"]) == 1:
        await cq.message.edit_text(sc("waiting for player 2"))
    elif len(game["players"]) == 2:
        game["started"] = True
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("🪨", callback_data="rps2:rock"),
                InlineKeyboardButton("📄", callback_data="rps2:paper"),
                InlineKeyboardButton("✂️", callback_data="rps2:scissors")
            ]]
        )
        await cq.message.edit_text(sc("both players joined\nchoose within 10s"), reply_markup=keyboard)
        asyncio.create_task(timeout_game(cq.message.id))

    await cq.answer()

async def timeout_game(msg_id):
    await asyncio.sleep(10)
    game = games.get(msg_id)

    if not game or not game["started"]:
        return

    if len(game["choices"]) < 2:
        await game["message"].edit_text(sc("time up\nmatch cancelled"))
        games.pop(msg_id, None)

@app.on_callback_query(filters.regex("^rps2:"))
async def play_game(client, cq):
    game = games.get(cq.message.id)
    user = cq.from_user

    if not game or not game["started"]:
        return await cq.answer("invalid", show_alert=True)

    if user.id not in game["players"]:
        return await cq.answer("not your game", show_alert=True)

    if user.id in game["choices"]:
        return await cq.answer("already chosen", show_alert=True)

    choice = cq.data.split(":")[1]
    game["choices"][user.id] = choice

    if len(game["choices"]) < 2:
        return await cq.answer("choice locked")

    p1, p2 = game["players"]
    c1 = game["choices"][p1]
    c2 = game["choices"][p2]

    if c1 == c2:
        result = sc("draw")
    elif (c1 == "rock" and c2 == "scissors") or \
         (c1 == "paper" and c2 == "rock") or \
         (c1 == "scissors" and c2 == "paper"):
        result = sc("player 1 wins")
        leaderboards[cq.message.chat.id][p1] += 1
    else:
        result = sc("player 2 wins")
        leaderboards[cq.message.chat.id][p2] += 1

    text = (
        f"{sc('player 1')} : {c1}\n"
        f"{sc('player 2')} : {c2}\n\n"
        f"{result}"
    )

    await cq.message.edit_text(text)
    games.pop(cq.message.id, None)
    await cq.answer()

@app.on_message(filters.command("rpslead", prefixes=PREFIXES) & filters.group)
async def leaderboard(client, message):
    chat_id = message.chat.id

    if chat_id not in leaderboards or not leaderboards[chat_id]:
        return await message.reply_text(sc("no games played"))

    sorted_users = sorted(
        leaderboards[chat_id].items(),
        key=lambda x: x[1],
        reverse=True
    )

    text = sc("rps leaderboard") + "\n\n"

    for i, (user_id, wins) in enumerate(sorted_users[:10], 1):
        text += f"{i}. [user](tg://user?id={user_id}) - {wins}\n"

    await message.reply_video(
        video=RPS_VID,
        caption=text,
        has_spoiler=True,
        parse_mode="markdown"
                                    )
