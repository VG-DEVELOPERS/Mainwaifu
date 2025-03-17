import random
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant, ChatWriteForbidden, PeerIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from Grabber import application, user_collection, collection
from Grabber import Grabberu as app
from Grabber import SUPPORT_CHAT, BOT_USERNAME

# Constants
ALLOWED_GROUP_ID = -1002528887253
MUST_JOIN = "seal_Your_WH_Group"  # Replace with your main group username
SECOND_JOIN = "seal_Your_WH_Group"  # Replace with second required channel
COOLDOWN_DURATION = timedelta(days=1)  # Cooldown for 24 hours

# Rarity list
RARITIES = [
    '⚪ Common', '🟡 Legendary', '🟢 Medium', '💠 Cosmic', 
    '💮 Exclusive', '🔮 Limited Edition', '🟠 Rare'
]

async def get_random_husbando():
    """Fetch a random husbando from the database based on rarity."""
    selected_rarity = random.choice(RARITIES)
    try:
        pipeline = [
            {'$match': {'rarity': selected_rarity}},  # Match rarity
            {'$sample': {'size': 1}}  # Random sampling
        ]
        cursor = collection.aggregate(pipeline)
        waifus = await cursor.to_list(length=None)
        return waifus
    except Exception as e:
        print(f"Error fetching random husbando: {e}")
        return []

@app.on_message(filters.command("claim") & filters.group)
async def claim_husbando(client: Client, message: Message):
    """Allows users to claim a husbando but only in the allowed group."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    mention = f"[{first_name}](tg://user?id={user_id})"

    # Check if the command is used in the allowed group
    if chat_id != ALLOWED_GROUP_ID:
        return await message.reply_text(f"This command is only available in @{BOT_USERNAME}.")

    # Cooldown check
    user_data = await user_collection.find_one({'id': user_id}, projection={'last_husbando_claim': 1})
    if user_data and user_data.get('last_husbando_claim'):
        last_claim = user_data['last_husbando_claim']
        if datetime.utcnow() - last_claim < COOLDOWN_DURATION:
            remaining_time = (COOLDOWN_DURATION - (datetime.utcnow() - last_claim)).total_seconds()
            hours, remainder = divmod(remaining_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            return await message.reply_text(
                f"⏳ You can claim your next husbando in {int(hours)}h {int(minutes)}m {int(seconds)}s."
            )

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
            "🔒 To claim a husbando, you must join both groups!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Group", url=link1)],
                [InlineKeyboardButton("Join Channel", url=link2)]
            ])
        )

    # Get a random husbando
    waifus = await get_random_husbando()
    if not waifus:
        return await message.reply_text("⚠️ No husbandos available. Please try again later.")

    waifu = waifus[0]

    # Update user's collection
    await user_collection.update_one(
        {'id': user_id},
        {'$push': {'characters': waifu}, '$set': {'last_husbando_claim': datetime.utcnow()}},
        upsert=True
    )

    # Prepare response message
    media_url = waifu.get('img_url') or waifu.get('vid_url')
    caption = (
        f"{mention} 🎉 You claimed a husbando!\n"
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

@app.on_message(filters.command("husbando_help") & filters.private)
async def husbando_help(client: Client, message: Message):
    """Displays help information for claiming a husbando."""
    help_text = (
        "👋 **Welcome to the Husbando Claim Bot!**\n\n"
        "**Commands:**\n"
        "/claim - Claim a random husbando (only in the allowed group)\n"
        "/husbando_help - Show this help message\n\n"
        "**Instructions:**\n"
        f"1. Make sure you have joined both @{SUPPORT_CHAT} and @{MUST_JOIN}.\n"
        "2. Use `/claim` to claim a husbando. You can only claim once every 24 hours.\n\n"
        "Happy claiming!"
    )
    await message.reply_text(help_text)
            
