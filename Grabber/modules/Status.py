from pyrogram import Client, filters
import asyncio
from Grabber import Grabberu as Grabber, user_collection, group_user_totals_collection, collection

# Rarity categories with unique emojis
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
    """Get count of each rarity type for a user."""
    rarity_counts = {rarity: 0 for rarity in RARITIES}

    user = await user_collection.find_one({'id': user_id})
    if user:
        characters = user.get('characters', [])
        for char in characters:
            rarity = char.get('rarity', '⚪ Common')
            rarity_counts[rarity] += 1

    return rarity_counts

async def get_progress_bar(user_waifus_count, total_waifus_count):
    """Generate a progress bar based on collection progress."""
    if total_waifus_count == 0:
        return "▱▱▱▱▱▱▱▱▱▱", 0  # Avoid division by zero

    bar_width = 10
    progress = min(user_waifus_count / total_waifus_count, 1)
    progress_percent = round(progress * 100, 2)

    filled_width = int(progress * bar_width)
    empty_width = bar_width - filled_width

    progress_bar = "▰" * filled_width + "▱" * empty_width
    return progress_bar, progress_percent

async def get_total_waifus():
    """Get the total waifu count from the database."""
    return await collection.count_documents({})

@Grabber.on_message(filters.command(["status", "mystatus"]))
async def send_grabber_status(client, message):
    """Send user status, including waifu collection progress."""
    try:
        loading_message = await message.reply("🔄 Fetching Profile Status...")

        for i in range(1, 6):
            await asyncio.sleep(1)
            await loading_message.edit_text("🔄 Fetching Profile Status" + "." * i)

        user_id = message.from_user.id
        user = await user_collection.find_one({'id': user_id})

        user_characters = user.get('characters', []) if user else []
        total_count = len(user_characters)

        total_waifus_count = await get_total_waifus()  # Fixed total count retrieval
        progress_bar, progress_percent = await get_progress_bar(total_count, total_waifus_count)
        
        rarity_counts = await get_user_rarity_counts(user_id)

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
            f"➣ 📈 **Progress:** {progress_bar} **{progress_percent:.2f}%**\n"
            f"╚════════ • ✧ • ════════╝"
        )

        await loading_message.edit_text(rarity_message)

    except Exception as e:
        print(f"Error: {e}")
        await message.reply_text("❌ An error occurred while fetching your status.")
        
