import random
from telegram import Update
import html
from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant, PeerIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from Grabber import application, user_collection, collection
from Grabber import Grabberu as app
from Grabber import SUPPORT_CHAT, BOT_USERNAME

# Image for leaderboard or messages
photo_url = "https://telegra.ph/file/1d9c963d5a138dc3c3077.jpg"

# Allowed group ID for claiming
ALLOWED_GROUP_ID = -1002528887253  

# Required groups/channels to join before claiming
MUST_JOIN = "seal_Your_WH_Group"
SECOND_JOIN = "seal_Your_WH_Group"

# Rarity probability distribution
RARITY_WEIGHTS = {
    '⚪ Common': 60,
    '🟢 Medium': 30,
    '🟠 Rare': 9,
    '🟡 Legendary': 1
}

async def get_random_waifu():
    """Fetch a random waifu from the database based on rarity probability."""
    selected_rarity = random.choices(
        list(RARITY_WEIGHTS.keys()), 
        weights=list(RARITY_WEIGHTS.values()), 
        k=1
    )[0]

    try:
        pipeline = [
            {'$match': {'rarity': selected_rarity}},  
            {'$sample': {'size': 1}}  
        ]
        cursor = collection.aggregate(pipeline)
        waifus = await cursor.to_list(length=1)
        return waifus[0] if waifus else None
    except Exception as e:
        print(f"Error fetching waifu: {e}")
        return None

@app.on_message(filters.command("claim") & filters.group)
async def claim_waifu(client: Client, message: Message):
    """Allows users to claim a waifu, but only once."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    first_name = html.escape(message.from_user.first_name)  # Escape HTML to avoid errors
    mention = f"[{first_name}](tg://user?id={user_id})"

    if chat_id != ALLOWED_GROUP_ID:
        return await message.reply_text(f"🚫 This command is only available in the allowed group.")

    # Check if user already claimed a waifu
    user_data = await user_collection.find_one({'user_id': user_id}, {'claimed_waifu': 1})
    if user_data and user_data.get('claimed_waifu', False):
        return await message.reply_text("🎖️ **You have already claimed your waifu!**")

    # Ensure bot has access to required groups
    try:
        await app.get_chat(MUST_JOIN)
        await app.get_chat(SECOND_JOIN)
    except PeerIdInvalid:
        return await message.reply_text("⚠️ Bot lacks permissions to check required groups. Contact support.")

    # Check if the user has joined the required groups
    try:
        await app.get_chat_member(MUST_JOIN, user_id)
        await app.get_chat_member(SECOND_JOIN, user_id)
    except UserNotParticipant:
        return await message.reply_text(
            "🔒 To claim a waifu, you must join both groups!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Group", url=f"https://t.me/{MUST_JOIN}")],
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{SECOND_JOIN}")]
            ])
        )

    # Get a random waifu
    waifu = await get_random_waifu()
    if not waifu:
        return await message.reply_text("⚠️ No waifus available at the moment. Try again later!")

    # Store waifu claim in database
    await user_collection.update_one(
        {'user_id': user_id},
        {
            '$set': {
                'claimed_waifu': True,
                'first_name': first_name,
                'user_id': user_id  # Ensure user_id is stored properly
            },
            '$push': {'characters': waifu},
            '$inc': {'waifu_count': 1}
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

    # Send media (image/video) or fallback to text
    try:
        if media_url:
            if media_url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):  
                await message.reply_photo(photo=media_url, caption=caption)
            elif media_url.endswith(('.mp4', '.mov', '.avi', '.webm')):  
                await message.reply_video(video=media_url, caption=caption)
        else:
            await message.reply_text(caption)  
    except Exception as e:
        print(f"Failed to send media: {e}")
        await message.reply_text(caption)  
    
