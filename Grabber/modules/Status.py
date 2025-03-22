from pyrogram import Client, filters
import asyncio
from Grabber import Grabberu as Grabber, user_collection, group_user_totals_collection, collection

RARITIES = {
    '⚪ Common': '🔵', '🟢 Medium': '🔴', '🟠 Rare': '🟠',
    '🟡 Legendary': '🟡', '💠 Cosmic': '💎', '💮 Exclusive': '🌟',
    '🔮 Limited Edition': '🪄'
}

async def get_user_rarity_counts(user_id):
    rarity_counts = {rarity: 0 for rarity in RARITIES}
    user = await user_collection.find_one({'id': user_id})

    if isinstance(user, dict) and "characters" in user:  
        for char in user["characters"]:
            rarity = char.get('rarity', '⚪ Common')  
            if rarity in rarity_counts:
                rarity_counts[rarity] += 1

    return rarity_counts

async def get_progress_bar(user_waifus_count, total_waifus_count):
    if total_waifus_count == 0:
        return "▱" * 10, 0  

    progress = min(user_waifus_count / total_waifus_count, 1)
    progress_percent = round(progress * 100, 2)
    filled_width = int(progress * 10)
    progress_bar = "▰" * filled_width + "▱" * (10 - filled_width)

    return progress_bar, progress_percent

async def get_chat_top(chat_id, user_id):
    try:
        pipeline = [{"$match": {"group_id": chat_id}}, {"$sort": {"count": -1}}, {"$limit": 10}]
        leaderboard = await group_user_totals_collection.aggregate(pipeline).to_list(length=None)
        return next((i+1 for i, u in enumerate(leaderboard) if u.get('user_id') == user_id), 'N/A')
    except:
        return 'N/A'

async def get_global_top(user_id):
    try:
        pipeline = [{"$project": {"id": 1, "characters_count": {"$size": {"$ifNull": ["$characters", []]}}}}, {"$sort": {"characters_count": -1}}]
        leaderboard = await user_collection.aggregate(pipeline).to_list(length=None)
        return next((i+1 for i, u in enumerate(leaderboard) if u.get('id') == user_id), 'N/A')
    except:
        return 'N/A'

@Grabber.on_message(filters.command(["status", "mystatus"]))
async def send_grabber_status(client, message):
    try:
        loading_message = await message.reply("🔄 Fetching Profile Status...")
        await asyncio.sleep(2)

        user_id = message.from_user.id
        user = await user_collection.find_one({'id': user_id})

        if not isinstance(user, dict):
            return await message.reply_text("🚨 No profile found! Try collecting a waifu first.")

        user_characters = user.get('characters', []) if isinstance(user.get('characters'), list) else []
        total_count = len(user_characters)

        total_waifus_count = await collection.count_documents({}) or 1  
        progress_bar, progress_percent = await get_progress_bar(total_count, total_waifus_count)

        rarity_counts = await get_user_rarity_counts(user_id)
        chat_top = await get_chat_top(message.chat.id, user_id)
        global_top = await get_global_top(user_id)
        rank = get_rank(progress_percent)

        profile_image_url = user.get('profile_image_url')

        rarity_message = f"""
        ╔════════ • ✧ • ════════╗
              ⛩ **User Profile** ⛩
        ══════════════════════
        ➣ ❄️ **Name:** {message.from_user.first_name} {message.from_user.last_name or ''}
        ➣ 🍀 **User ID:** {user_id}
        ━━━━━━━━━━━━━━━━━━━━━━
        ➣ 👾 **Characters Collected:** {total_count}/{total_waifus_count} (**{progress_percent:.2f}%**)
        """ + "".join([f"├─➩ {RARITIES[r]} **{r.split()[1]}:** {rarity_counts[r]}\n" for r in RARITIES]) + f"""
        ━━━━━━━━━━━━━━━━━━━━━━
        ➣ 💠 **Rank:** {rank}
        ➣ 🏆 **Chat Top:** {chat_top if chat_top != 'N/A' else '❌ Not Ranked'}
        ➣ 🌍 **Global Top:** {global_top if global_top != 'N/A' else '❌ Not Ranked'}
        ━━━━━━━━━━━━━━━━━━━━━━
        ➣ 📈 **Progress:** {progress_bar} **{progress_percent:.2f}%**
        ╚════════ • ✧ • ════════╝
        """

        if profile_image_url:
            await message.reply_photo(photo=profile_image_url, caption=rarity_message)
        else:
            await message.reply_text(rarity_message)

        await loading_message.delete()

    except Exception as e:
        print(f"Error: {e}")
        
