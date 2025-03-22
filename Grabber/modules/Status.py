from pyrogram import Client, filters
import asyncio
from Grabber import Grabberu as Grabber, user_collection, group_user_totals_collection, db

characters_collection = db['anime_characters_lol']

# 🎭 Define Rarity Categories & Emojis
RARITIES = {
    '⚪ Common': '🔵',
    '🟢 Medium': '🔴',
    '🟠 Rare': '🟠',
    '🟡 Legendary': '🟡',
    '💠 Cosmic': '💎',
    '💮 Exclusive': '🌟',
    '🔮 Limited Edition': '🪄'
}

# 🏆 Rank System
RANKS = [
    (5, "🥉 Bronze I"), (10, "🥉 Bronze II"), (15, "🥉 Bronze III"),
    (20, "🥈 Silver I"), (25, "🥈 Silver II"), (30, "🥈 Silver III"),
    (35, "🥇 Gold I"), (40, "🥇 Gold II"), (45, "🥇 Gold III"),
    (50, "🏅 Gold IV"), (55, "💎 Platinum I"), (60, "💎 Platinum II"),
    (65, "💎 Platinum III"), (70, "💎 Platinum IV"), (75, "💠 Diamond I"),
    (80, "💠 Diamond II"), (85, "💠 Diamond III"), (90, "💠 Diamond IV"),
    (95, "🦸 Heroic I"), (100, "🦸 Heroic II"), (105, "🦸 Heroic III"),
    (110, "👑 Elite Heroic"), (115, "🎭 Master"), (120, "👑 Crown"),
    (130, "🔥 Grandmaster I"), (140, "🔥 Grandmaster II"),
    (150, "🔥 Grandmaster III"), (160, "🚀 Conqueror")
]

# 📊 Get User Rarity Counts
async def get_user_rarity_counts(user_id):
    rarity_counts = {rarity: 0 for rarity in RARITIES}

    user = await user_collection.find_one({'id': user_id}) or {}
    characters = user.get('characters', [])
    
    if isinstance(characters, list):
        for char in characters:
            if isinstance(char, dict):
                rarity = char.get('rarity', '⚪ Common')
                if rarity in rarity_counts:
                    rarity_counts[rarity] += 1
    
    return rarity_counts

# 📈 Progress Bar Generator
async def get_progress_bar(user_count, total_count):
    bar_width = 10
    progress = min(user_count / total_count, 1) if total_count else 0
    progress_percent = round(progress * 100, 2)
    
    filled_width = int(progress * bar_width)
    empty_width = bar_width - filled_width
    
    progress_bar = "▰" * filled_width + "▱" * empty_width
    return progress_bar, progress_percent

# 🎖 Determine Rank
def get_rank(progress_percent):
    for percent, rank in RANKS:
        if progress_percent <= percent:
            return rank
    return "🚀 Conqueror"

# 📊 Get Chat Top Rank
async def get_chat_top(chat_id, user_id):
    try:
        pipeline = [
            {"$match": {"group_id": chat_id}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        leaderboard_data = await group_user_totals_collection.aggregate(pipeline).to_list(None)
        
        for i, user in enumerate(leaderboard_data, start=1):
            if user.get('user_id') == user_id:
                return f"🏆 {i}"
        return "N/A"
    except Exception as e:
        print(f"Error getting chat top: {e}")
        return "N/A"

# 🌍 Get Global Top Rank
async def get_global_top(user_id):
    try:
        pipeline = [
            {"$project": {"id": 1, "characters_count": {"$size": {"$ifNull": ["$characters", []]}}}},
            {"$sort": {"characters_count": -1}}
        ]
        leaderboard_data = await user_collection.aggregate(pipeline).to_list(None)
        
        for i, user in enumerate(leaderboard_data, start=1):
            if user.get('id') == user_id:
                return f"🌐 {i}"
        return "N/A"
    except Exception as e:
        print(f"Error getting global top: {e}")
        return "N/A"

# 📜 Find Character Command
@Grabber.on_message(filters.command(["find"]))
async def find_character(client, message):
    try:
        character_id = " ".join(message.text.split()[1:]).strip()

        if not character_id:
            await message.reply("❌ Please provide a character ID.")
            return

        character = await characters_collection.find_one({"id": character_id})

        if not character:
            await message.reply("❌ No character found with that ID.")
            return

        response_message = (
            f"🔍 **Character Information**\n\n"
            f"🪭 **Name:** {character['name']}\n"
            f"⚕️ **Rarity:** {RARITIES.get(character['rarity'], '⚪')} {character['rarity']}\n"
            f"⚜️ **Anime:** {character['anime']}\n"
            f"🆔 **ID:** {character['id']}\n"
        )

        if 'image_url' in character:
            await message.reply_photo(photo=character['image_url'], caption=response_message)
        else:
            await message.reply_text(response_message)

    except Exception as e:
        print(f"Error: {e}")

# 🎭 Grabber Status Command
@Grabber.on_message(filters.command(["status", "mystatus"]))
async def send_grabber_status(client, message):
    try:
        loading_message = await message.reply("🔄 Fetching Grabber Status...")

        for i in range(1, 6):
            await asyncio.sleep(1)
            await loading_message.edit_text("🔄 Fetching Grabber Status" + "." * i)

        user_id = message.from_user.id
        user = await user_collection.find_one({'id': user_id}) or {}

        user_characters = user.get('characters', [])
        total_count = len(user_characters)
        total_waifus_count = await user_collection.count_documents({})

        chat_top = await get_chat_top(message.chat.id, user_id)
        global_top = await get_global_top(user_id)

        progress_bar, progress_percent = await get_progress_bar(total_count, total_waifus_count)
        rank = get_rank(progress_percent)

        rarity_counts = await get_user_rarity_counts(user_id)
        profile_image_url = user.get('profile_image_url')

        rarity_list = "\n".join([
            f"├─➩ {RARITIES[rarity]} **{rarity.split()[1]}:** {count}" 
            for rarity, count in rarity_counts.items() if count > 0
        ])

        status_message = (
            f"╔════════ • ✧ • ════════╗\n"
            f"          ⛩ **User Profile** ⛩\n"
            f"══════════════════════\n"
            f"➣ ❄️ **Name:** {message.from_user.first_name} {message.from_user.last_name or ''}\n"
            f"➣ 🍀 **User ID:** {user_id}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 👾 **Characters Collected:** {total_count}/{total_waifus_count} ({progress_percent}%)\n"
            f"{rarity_list}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 💠 **Rank:** {rank}\n"
            f"➣ 🎖 **Chat Top:** {chat_top}\n"
            f"➣ 🌍 **Global Top:** {global_top}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 📈 **Progress:** {progress_bar} {progress_percent}%\n"
            f"╚════════ • ✧ • ════════╝"
        )

        if profile_image_url:
            await message.reply_photo(photo=profile_image_url, caption=status_message)
        else:
            await message.reply_text(status_message)

    except Exception as e:
        print(f"Error: {e}")
    
