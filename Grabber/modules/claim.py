import random
import html
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant, PeerIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from Grabber import application, user_collection, collection
from Grabber import Grabberu as app
from Grabber import SUPPORT_CHAT, BOT_USERNAME

# Constants
ALLOWED_GROUP_ID = -1002528887253  # Your group ID where claiming is allowed
MUST_JOIN = "seal_Your_WH_Group"  # Main required group username
SECOND_JOIN = "seal_Your_WH_Group"  # Second required channel

# Rarity list with weighted probability
RARITY_WEIGHTS = {
    '⚪ Common': 60,  # 60% chance
    '🟢 Medium': 30,  # 30% chance
    '🟠 Rare': 9,     # 9% chance
    '🟡 Legendary': 1  # 1% chance
}

async def get_random_waifu():
    """Fetch a random waifu from the database based on rarity probability."""
    selected_rarity = random.choices(
        list(RARITY_WEIGHTS.keys()), 
        weights=list(RARITY_WEIGHTS.values()), 
        k=1
    )[0]  # Select based on probability

    try:
        pipeline = [
            {'$match': {'rarity': selected_rarity}},  # Match the chosen rarity
            {'$sample': {'size': 1}}  # Random sampling
        ]
        cursor = collection.aggregate(pipeline)
        waifus = await cursor.to_list(length=None)
        return waifus
    except Exception as e:
        print(f"Error fetching random waifu: {e}")
        return []

@app.on_message(filters.command("claim") & filters.group)
async def claim_waifu(client: Client, message: Message):
    """Allows users to claim a waifu, but only once ever."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    mention = f"[{first_name}](tg://user?id={user_id})"

    # Check if the command is used in the allowed group
    if chat_id != ALLOWED_GROUP_ID:
        return await message.reply_text(f"This command is only available in @{BOT_USERNAME}.")

    # Check if the user has already claimed a waifu
    user_data = await user_collection.find_one({'id': user_id}, projection={'claimed_waifu': 1})
    if user_data and user_data.get('claimed_waifu', False):
        return await message.reply_text("🎖️ **You have already claimed your waifu!**")

    # Check if the bot can access the required channels
    try:
        await app.get_chat(MUST_JOIN)
        await app.get_chat(SECOND_JOIN)
    except PeerIdInvalid:
        return await message.reply_text("Bot cannot access the required groups. Please verify bot permissions.")

    # Check if the user has joined both channels
    try:
        await app.get_chat_member(MUST_JOIN, user_id)
        await app.get_chat_member(SECOND_JOIN, user_id)
    except UserNotParticipant:
        link1 = f"https://t.me/{MUST_JOIN}"
        link2 = f"https://t.me/{SECOND_JOIN}"
        return await message.reply_text(
            "🔒 To claim a waifu, you must join both groups!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Group", url=link1)],
                [InlineKeyboardButton("Join Channel", url=link2)]
            ])
        )

    # Get a random waifu
    waifus = await get_random_waifu()
    if not waifus:
        return await message.reply_text("⚠️ No waifus available. Please try again later.")

    waifu = waifus[0]

    # Update user's database entry to mark waifu as claimed and increment their waifu count
    await user_collection.update_one(
        {'id': user_id},
        {
            '$set': {'claimed_waifu': True, 'first_name': first_name},
            '$push': {'characters': waifu},
            '$inc': {'waifu_count': 1}  # Increase the waifu count
        },
        upsert=True
    )

    # Prepare response message
    media_url = waifu.get('img_url') or waifu.get('vid_url')
    caption = (
        f"{mention} 🎉 You have claimed a waifu!\n"
        f"🎐 **Name:** {waifu['name']}\n"
        f"🐙 **Rarity:** {waifu['rarity']}\n"
        f"💮 **Anime:** {waifu['anime']}\n"
    )

    # Send image/video or fallback to text
    if media_url:
        try:
            if media_url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):  
                await message.reply_photo(photo=media_url, caption=caption)
            elif media_url.endswith(('.mp4', '.mov', '.avi', '.webm')):  
                await message.reply_video(video=media_url, caption=caption)
        except Exception as e:
            print(f"Failed to send media: {e}")
            await message.reply_text(caption)  
    else:
        await message.reply_text(caption)  

@app.on_message(filters.command("tops") & filters.group)
async def top_waifus(client: Client, message: Message):
    """Shows the top 10 users with the most claimed waifus."""
    
    top_users = await user_collection.find(
        {}, 
        projection={'id': 1, 'first_name': 1, 'waifu_count': 1}
    ).sort('waifu_count', -1).limit(10).to_list(10)

    if not top_users:
        return await message.reply_text("⚠️ No users have claimed waifus yet.")

    leaderboard_message = "🏆 **Top 10 Users with Most Waifus:**\n\n"

    for i, user in enumerate(top_users, start=1):
        first_name = user.get('first_name', 'Unknown')
        user_id = user.get('id', 'Unknown')
        waifu_count = user.get('waifu_count', 0)

        # Ensure user_id is an integer before making a clickable link
        if isinstance(user_id, int):
            profile_link = f"[{first_name}](tg://user?id={user_id})"
        else:
            profile_link = first_name  # If no valid ID, just show the name

        leaderboard_message += f"{i}. {profile_link} ➾ {waifu_count} waifus\n"

    await message.reply_text(leaderboard_message, parse_mode="HTML")


@app.on_message(filters.command("waifu_help") & filters.private)
async def waifu_help(client: Client, message: Message):
    """Displays help information for claiming a waifu."""
    help_text = (
        "👋 **Welcome to the Waifu Claim Bot!**\n\n"
        "**Commands:**\n"
        "/claim - Claim a random waifu (only in the allowed group, one-time only)\n"
        "/top_waifus - See the top 10 users with the most waifus\n"
        "/waifu_help - Show this help message\n\n"
        "**Instructions:**\n"
        f"1. Make sure you have joined both @{SUPPORT_CHAT} and @{MUST_JOIN}.\n"
        "2. Use `/claim` to claim a waifu. You can only claim **once** in your lifetime.\n\n"
        "🎉 Rarity Chances:\n"
        "⚪ Common - 60%\n"
        "🟢 Medium - 30%\n"
        "🟠 Rare - 9%\n"
        "🟡 Legendary - 1%\n\n"
        "Good luck and happy claiming!"
    )
    await message.reply_text(help_text)
    
