from Oneforall import app
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from collections import defaultdict
import random
import asyncio

games = {}
leaderboards = defaultdict(lambda: defaultdict(int))

MAX_PLAYERS = 6
START_HP = 5

MODES = ["Battle Royale", "Shootout", "Zombie Survival", "Tank War", "Space Shooter", "Battle Cards"]
PREFIXES = ["/", "!", "."]


# ---------------- START MENU ----------------
@app.on_message(filters.command("warzone", prefixes=PREFIXES) & filters.group)
async def start_warzone(client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"⚔️ {mode}", callback_data=f"wz_mode:{mode}")] for mode in MODES]
    )

    await message.reply_text(
        "🔥 𝖶𝖠𝖱𝖹𝖮𝖭𝖤 𝖬𝖨𝖭𝖨-𝖠𝖱𝖢𝖠𝖣𝖤 🔥\n\nSelect your battlefield:",
        reply_markup=keyboard
    )


# ---------------- CALLBACK HANDLER ----------------
@app.on_callback_query()
async def warzone_cb(client, cq: CallbackQuery):
    user = cq.from_user
    chat_id = cq.message.chat.id
    data = cq.data

    # ---------- MODE SELECT ----------
    if data.startswith("wz_mode:"):
        mode = data.split(":")[1]

        if chat_id in games and mode in games[chat_id]:
            return await cq.answer("Already running!", show_alert=True)

        games.setdefault(chat_id, {})
        games[chat_id][mode] = {
            "players": {},
            "started": False,
            "round": 0,
            "actions": {}
        }

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🚀 Join Warzone", callback_data=f"wz_join:{mode}")]]
        )

        await cq.message.edit_text(
            f"⚔️ {mode} READY\n\nClick join to enter battlefield (max {MAX_PLAYERS})",
            reply_markup=keyboard
        )

        return await cq.answer()


    # ---------- JOIN GAME ----------
    if data.startswith("wz_join:"):
        mode = data.split(":")[1]
        game = games.get(chat_id, {}).get(mode)

        if not game:
            return await cq.answer("No game found!", show_alert=True)

        if user.id in game["players"]:
            return await cq.answer("Already in battle!", show_alert=True)

        if len(game["players"]) >= MAX_PLAYERS:
            return await cq.answer("Warzone full!", show_alert=True)

        game["players"][user.id] = START_HP

        await cq.answer("Joined battlefield ⚔️")

        if len(game["players"]) < 2:
            await cq.message.edit_text(
                f"{mode}\nWaiting for warriors...\n\n👥 {len(game['players'])}/{MAX_PLAYERS}"
            )
            return

        await start_round(client, cq.message, chat_id, mode)
        return


    # ---------- ACTION ----------
    if data.startswith("wz_act:"):
        _, mode, action = data.split(":")
        game = games.get(chat_id, {}).get(mode)

        if not game or not game["started"]:
            return await cq.answer("Game not active", show_alert=True)

        if user.id not in game["players"]:
            return await cq.answer("Not in warzone!", show_alert=True)

        if user.id in game["actions"]:
            return await cq.answer("Already acted!", show_alert=True)

        game["actions"][user.id] = action
        await cq.answer(f"{action} locked")

        if len(game["actions"]) == len(game["players"]):
            await process_round(client, cq.message, chat_id, mode)


# ---------------- START ROUND ----------------
async def start_round(client, message, chat_id, mode):
    game = games[chat_id][mode]
    game["started"] = True
    game["round"] += 1
    game["actions"] = {}

    hp_text = "\n".join(
        [f"👤 <a href='tg://user?id={uid}'>{uid}</a> ❤️ {hp}"
         for uid, hp in game["players"].items()]
    )

    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("⚔️ Attack", callback_data=f"wz_act:{mode}:Attack"),
            InlineKeyboardButton("🛡 Defend", callback_data=f"wz_act:{mode}:Defend"),
            InlineKeyboardButton("💚 Heal", callback_data=f"wz_act:{mode}:Heal")
        ]]
    )

    await message.edit_text(
        f"🔥 ROUND {game['round']} STARTED\n\n{hp_text}\n\nChoose action:",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


# ---------------- PROCESS ROUND ----------------
async def process_round(client, message, chat_id, mode):
    game = games[chat_id][mode]
    results = []

    players = list(game["players"].keys())
    random.shuffle(players)

    for uid in players:
        action = game["actions"].get(uid)

        if not action:
            continue

        if action == "Attack":
            targets = [t for t in players if t != uid and game["players"][t] > 0]
            if targets:
                target = random.choice(targets)
                if random.random() < 0.7:
                    game["players"][target] -= 1
                    results.append(f"⚔️ {uid} hit {target}")
                else:
                    results.append(f"💥 {uid} missed")

        elif action == "Defend":
            results.append(f"🛡 {uid} defended")

        elif action == "Heal":
            game["players"][uid] += 1
            results.append(f"💚 {uid} healed")

    # remove dead
    alive = {u: hp for u, hp in game["players"].items() if hp > 0}
    game["players"] = alive

    # WIN CONDITION
    if len(alive) <= 1:
        text = "\n".join(results) + "\n\n"

        if alive:
            winner = list(alive.keys())[0]
            leaderboards[chat_id][mode][winner] += 1
            text += f"🏆 WINNER: {winner}"
        else:
            text += "💀 NO SURVIVORS"

        await message.edit_text(text)
        del games[chat_id][mode]
        return

    await start_round(client, message, chat_id, mode)


# ---------------- LEADERBOARD ----------------
@app.on_message(filters.command("warlead", prefixes=PREFIXES) & filters.group)
async def warzone_leaderboard(client, message: Message):
    chat_id = message.chat.id

    if chat_id not in leaderboards:
        return await message.reply_text("No warzone data found")

    text = "🏆 𝖶𝖠𝖱𝖹𝖮𝖭𝖤 𝖫𝖤𝖠𝖣𝖤𝖱𝖡𝖮𝖠𝖱𝖣 🏆\n\n"

    for mode in MODES:
        data = leaderboards[chat_id].get(mode, {})
        if not data:
            continue

        text += f"⚔️ {mode}\n"

        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)

        for i, (uid, wins) in enumerate(sorted_data[:10], 1):
            text += f"{i}. <a href='tg://user?id={uid}'>Player</a> - {wins} wins\n"

        text += "\n"

    await message.reply_text(text, disable_web_page_preview=True)
