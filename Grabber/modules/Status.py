from pyrogram import Client, filters
import asyncio
from Grabber import Grabberu as Grabber, user_collection, group_user_totals_collection, collection

# Define rarity categories
RARITIES = {
    '⚪ Common': '🔵',
    '🟢 Medium': '🔴',
    '🟠 Rare': '🟠',
    '🟡 Legendary': '🟡',
    '💠 Cosmic': '💎',
    '💮 Exclusive': '🌟',
    '🔮 Limited Edition': '🪄'
}

async def get_user_rarity_counts(user_id):
    """Fetches the count of each rarity type for a user."""
    rarity_counts = {rarity: 0 for rarity in RARITIES}

    user = await user_collection.find_one({'id': user_id})  
    if isinstance(user, dict):  
        for char in user.get('characters', []):  
            rarity = char.get('rarity', '⚪ Common')  
            if rarity in rarity_counts:
                rarity_counts[rarity] += 1  

    return rarity_counts

async def get_progress_bar(user_waifus_count, total_waifus_count):
    """Creates a progress bar and percentage display."""
    bar_width = 10
    if total_waifus_count == 0:
        return "▱" * bar_width, 0  

    progress = min(user_waifus_count / total_waifus_count, 1)
    progress_percent = round(progress * 100, 2)

    filled_width = int(progress * bar_width)
    empty_width = bar_width - filled_width

    progress_bar = "▰" * filled_width + "▱" * empty_width
    return progress_bar, progress_percent

def get_rank(progress_percent):
    """Determines rank based on progress percentage."""
    ranks = [
        (5, "🥉 Bronze I"), (10, "🥉 Bronze II"), (15, "🥉 Bronze III"),
        (20, "🥈 Silver I"), (25, "🥈 Silver II"), (30, "🥈 Silver III"),
        (35, "🥇 Gold I"), (40, "🥇 Gold II"), (45, "🥇 Gold III"),
        (50, "🏅 Platinum I"), (55, "🏅 Platinum II"), (60, "🏅 Platinum III"),
        (65, "💎 Diamond I"), (70, "💎 Diamond II"), (75, "💎 Diamond III"),
        (80, "🔥 Heroic I"), (85, "🔥 Heroic II"), (90, "🔥 Heroic III"),
        (95, "👑 Master"), (100, "⚔️ Grandmaster"),
        (110, "🔱 Conqueror")
    ]

    for percent, rank in ranks:
        if progress_percent <= percent:
            return rank

    return "🔱 Conqueror"

async def get_chat_top(chat_id, user_id):
    """Finds a user's rank in the group leaderboard."""
    try:
        pipeline = [
            {"$match": {"group_id": chat_id}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        cursor = group_user_totals_collection.aggregate(pipeline)
        leaderboard_data = await cursor.to_list(length=None)

        for i, user in enumerate(leaderboard_data, start=1):
            if user.get('user_id') == user_id:
                return i

        return 'N/A'
    except Exception as e:
        print(f"Error getting chat top: {e}")
        return 'N/A'

async def get_global_top(user_id):
    """Finds a user's global leaderboard rank."""
    try:
        pipeline = [
            {"$project": {"id": 1, "characters_count": {"$size": {"$ifNull": ["$characters", []]}}}},
            {"$sort": {"characters_count": -1}}
        ]
        cursor = user_collection.aggregate(pipeline)
        leaderboard_data = await cursor.to_list(length=None)

        for i, user in enumerate(leaderboard_data, start=1):
            if user.get('id') == user_id:
                return i

        return 'N/A'
    except Exception as e:
        print(f"Error getting global top: {e}")
        return 'N/A'

@Grabber.on_message(filters.command(["status", "mystatus"]))
async def send_grabber_status(client, message):
    try:
        loading_message = await message.reply("🔄 Fetching Profile Status...")

        # Animated loading effect
        for i in range(1, 4):
            await asyncio.sleep(1)
            await loading_message.edit_text("🔄 Fetching Profile Status" + "." * i)

        user_id = message.from_user.id
        user = await user_collection.find_one({'id': user_id})

        if not isinstance(user, dict):
            return await message.reply_text("🚨 You don't have a profile yet! Try claiming a waifu first.")

        user_characters = user.get('characters', [])
        total_count = len(user_characters)

        # Fetch total waifus count
        total_waifus_count = await collection.count_documents({})
        if total_waifus_count == 0:
            total_waifus_count = 1  # Prevent division by zero

        # Progress and ranking
        progress_bar, progress_percent = await get_progress_bar(total_count, total_waifus_count)
        rank = get_rank(progress_percent)

        # Leaderboards
        chat_top = await get_chat_top(message.chat.id, user_id)
        global_top = await get_global_top(user_id)

        # Rarity counts
        rarity_counts = await get_user_rarity_counts(user_id)

        profile_image_url = user.get('profile_image_url', None)

        # Final status message
        rarity_message = (
            f"╔════════ • ✧ • ════════╗\n"
            f"          ⛩ **User Profile** ⛩\n"
            f"══════════════════════\n"
            f"➣ ❄️ **Name:** {message.from_user.first_name} {message.from_user.last_name or ''}\n"
            f"➣ 🍀 **User ID:** {user_id}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 👾 **Characters Collected:** {total_count}/{total_waifus_count} (**{progress_percent:.2f}%**)\n"
        )

        for rarity, emoji in RARITIES.items():
            rarity_message += f"├─➩ {emoji} **{rarity.split()[1]}:** {rarity_counts[rarity]}\n"

        rarity_message += (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 💠 **Rank:** {rank}\n"
            f"➣ 🏆 **Chat Top:** {chat_top if chat_top != 'N/A' else '❌ Not Ranked'}\n"
            f"➣ 🌍 **Global Top:** {global_top if global_top != 'N/A' else '❌ Not Ranked'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 📈 **Progress:** {progress_bar} **{progress_percent:.2f}%**\n"
            f"╚════════ • ✧ • ════════╝"
        )

        if profile_image_url:
            await message.reply_photo(photo=profile_image_url, caption=rarity_message)
        else:
            await message.reply_text(rarity_message)

        await loading_message.delete()

    except Exception as e:
        print(f"Error: {e}")
        
