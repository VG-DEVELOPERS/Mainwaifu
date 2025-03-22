from pyrogram import Client, filters
import asyncio
from Grabber import Grabberu as Grabber, user_collection, group_user_totals_collection, db

characters_collection = db['anime_characters_lol']

RARITIES = [
    '⚪ Common', '🟢 Medium', '🟠 Rare', '🟡 Legendary',
    '💠 Cosmic', '💮 Exclusive', '🔮 Limited Edition'
]

async def get_user_rarity_counts(user_id):
    rarity_counts = {rarity: 0 for rarity in RARITIES}
    user = await user_collection.find_one({'id': user_id})

    if user and isinstance(user, dict) and 'characters' in user:
        for char in user['characters']:
            rarity = char.get('rarity', '⚪ Common')
            if rarity in rarity_counts:
                rarity_counts[rarity] += 1

    return rarity_counts

async def get_progress_bar(user_count, total_count):
    if total_count == 0:
        return "▱▱▱▱▱▱▱▱▱▱", 0.00
    bar_width = 10
    progress = user_count / total_count
    progress_percent = round(progress * 100, 2)
    filled_width = int(progress * bar_width)
    empty_width = bar_width - filled_width
    progress_bar = "▰" * filled_width + "▱" * empty_width
    return progress_bar, progress_percent

def get_rank(progress_percent):
    ranks = [
        (5, "🥉 Bronze I"), (10, "🥉 Bronze II"), (15, "🥉 Bronze III"),
        (20, "🥈 Silver I"), (25, "🥈 Silver II"), (30, "🥈 Silver III"),
        (35, "🥇 Gold I"), (40, "🥇 Gold II"), (45, "🥇 Gold III"),
        (50, "🏆 Gold IV"), (55, "💎 Platinum I"), (60, "💎 Platinum II"),
        (65, "💎 Platinum III"), (70, "💎 Platinum IV"), (75, "💠 Diamond I"),
        (80, "💠 Diamond II"), (85, "💠 Diamond III"), (90, "💠 Diamond IV"),
        (95, "🔥 Heroic I"), (100, "🔥 Heroic II"), (105, "🔥 Heroic III"),
        (110, "⚔️ Elite Heroic"), (115, "👑 Master"), (120, "👑 Crown"),
        (130, "🏅 Grandmaster I"), (140, "🏅 Grandmaster II"),
        (150, "🏅 Grandmaster III"), (160, "🛡️ Conqueror")
    ]
    for percent, rank in ranks:
        if progress_percent <= percent:
            return rank
    return "🛡️ Conqueror"

async def get_chat_top(chat_id, user_id):
    try:
        leaderboard = await group_user_totals_collection.find({"group_id": chat_id}).sort("count", -1).to_list(10)
        for i, user in enumerate(leaderboard, start=1):
            if user.get('user_id') == user_id:
                return i
        return 'N/A'
    except Exception as e:
        print(f"Error getting chat top: {e}")
        return 'N/A'

async def get_global_top(user_id):
    try:
        leaderboard = await user_collection.aggregate([
            {"$project": {"id": 1, "characters_count": {"$size": {"$ifNull": ["$characters", []]}}}},
            {"$sort": {"characters_count": -1}}
        ]).to_list(10)
        for i, user in enumerate(leaderboard, start=1):
            if user.get('id') == user_id:
                return i
        return 'N/A'
    except Exception as e:
        print(f"Error getting global top: {e}")
        return 'N/A'

@Grabber.on_message(filters.command(["status", "mystatus"]))
async def send_grabber_status(client, message):
    try:
        loading_message = await message.reply("🔄 Fetching Grabber Status...")
        for i in range(1, 6):
            await asyncio.sleep(1)
            await loading_message.edit_text("🔄 Fetching Grabber Status" + "." * i)

        user_id = message.from_user.id
        user = await user_collection.find_one({'id': user_id})

        total_count = len(user.get('characters', [])) if user else 0
        total_waifus_count = await user_collection.count_documents({})
        chat_top = await get_chat_top(message.chat.id, user_id)
        global_top = await get_global_top(user_id)
        progress_bar, progress_percent = await get_progress_bar(total_count, total_waifus_count)
        rank = get_rank(progress_percent)
        rarity_counts = await get_user_rarity_counts(user_id)

        rarity_display = (
            f"🟡 Legendary: {rarity_counts['🟡 Legendary']}\n"
            f"├─➩ 🟠 Rare: {rarity_counts['🟠 Rare']}\n"
            f"├─➩ 🟢 Medium: {rarity_counts['🟢 Medium']}\n"
            f"├─➩ ⚪ Common: {rarity_counts['⚪ Common']}\n"
            f"├─➩ 💠 Cosmic: {rarity_counts['💠 Cosmic']}\n"
            f"├─➩ 💮 Exclusive: {rarity_counts['💮 Exclusive']}\n"
            f"└─➩ 🔮 Limited Edition: {rarity_counts['🔮 Limited Edition']}\n"
        )

        status_message = (
            f"╔════════ • ✧ • ════════╗\n"
            f"          ⛩ 『𝗨𝘀𝗲𝗿 𝗣𝗿𝗼𝗳𝗶𝗹𝗲』 ⛩\n"
            f"══════════════════════\n"
            f"➣ ❄️ Name: {message.from_user.first_name} {message.from_user.last_name or ''}\n"
            f"➣ 🍀 User ID: {user_id}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 👾 Harem: {total_count}/{total_waifus_count} ({progress_percent:.3f}%)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{rarity_display}"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 🎖️ Rank: {rank}\n"
            f"➣ 🏠 Chat Top: {chat_top}\n"
            f"➣ 🌍 Global Top: {global_top}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 📈 Progress: {progress_bar} {progress_percent:.2f}%\n"
            f"╚════════ • ✧ • ════════╝"
        )

        if user and 'profile_image_url' in user and user['profile_image_url']:
            await message.reply_photo(photo=user['profile_image_url'], caption=status_message)
        else:
            await message.reply_text(status_message)

    except Exception as e:
        print(f"Error: {e}")
        
