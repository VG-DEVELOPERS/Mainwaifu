import random
import html
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors import UserNotParticipant
from Grabber import user_collection, collection
from Grabber import Grabberu as app

# Required groups
MUST_JOIN = "seal_Your_WH_Group"
SECOND_JOIN = "SEAL_UPDATE"
BOT_USERNAME = "Seal_Your_Waifu_Bot"  # Replace with your bot's username

RARITY_WEIGHTS = {
    '⚪ Common': 60,
    '🟢 Medium': 30,
    '🟠 Rare': 9,
    '🟡 Legendary': 1
}

async def get_random_waifu():
    """Fetch a random waifu from the database based on rarity probability."""
    selected_rarity = random.choices(
        list(RARITY_WEIGHTS.keys()), weights=RARITY_WEIGHTS.values(), k=1
    )[0]

    waifu = await collection.aggregate([
        {'$match': {'rarity': selected_rarity}},  
        {'$sample': {'size': 1}}  
    ]).to_list(length=1)

    return waifu[0] if waifu else None

async def has_joined_required_groups(user_id):
    """Check if the user has joined both required groups."""
    try:
        await app.get_chat_member(MUST_JOIN, user_id)
        await app.get_chat_member(SECOND_JOIN, user_id)
        return True
    except UserNotParticipant:
        return False

async def has_started_bot(user_id):
    """Check if the user has started the bot in PM."""
    user_data = await user_collection.find_one({'id': user_id})
    return user_data is not None  # If user exists in DB, they have started the bot

@app.on_message(filters.command("claim") & filters.group)
async def claim_waifu(client: Client, message: Message):
    """Allows users to claim a waifu only if they have started the bot and joined groups."""
    user_id = message.from_user.id
    first_name = html.escape(message.from_user.first_name)  
    mention = f"[{first_name}](tg://user?id={user_id})"

    # Check if user has started the bot in PM
    if not await has_started_bot(user_id):
        return await message.reply_text(
            "🔹 **You need to start the bot in private chat first!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Start Bot", url=f"https://t.me/{BOT_USERNAME}?start=start")]
            ])
        )

    # Check if user exists in the database; if not, insert them
    user_data = await user_collection.find_one({'id': user_id})

    if not user_data:
        print(f"🔍 New user detected: {user_id}, inserting into database...")
        user_data = {
            'id': user_id,
            'first_name': first_name,
            'claimed_waifu': False,
            'joined_required_groups': False,
            'characters': [],
            'waifu_count': 0
        }
        await user_collection.insert_one(user_data)

    # Check if the user has already claimed a waifu
    if user_data.get('claimed_waifu', False):
        return await message.reply_text("🎖️ **You have already claimed your waifu! You cannot claim again.**")

    # Check if the user has joined the required groups
    if not await has_joined_required_groups(user_id):
        return await message.reply_text(
            "🔒 **To claim a waifu, you must join both groups!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Group", url=f"https://t.me/{MUST_JOIN}")],
                [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{SECOND_JOIN}")],
                [InlineKeyboardButton("🔄 Check Again", callback_data=f"check_join_{user_id}")]
            ])
        )

    # Save that user has joined the required groups
    await user_collection.update_one({'id': user_id}, {'$set': {'joined_required_groups': True}})
    print(f"✅ User {user_id} marked as joined_required_groups")

    # Get a random waifu
    waifu = await get_random_waifu()
    if not waifu:
        return await message.reply_text("⚠️ No waifus available at the moment. Try again later!")

    # Format waifu data
    waifu_data = {
        'id': waifu['id'],
        'name': waifu['name'],
        'anime': waifu['anime'],
        'rarity': waifu['rarity'],
        'img_url': waifu.get('img_url', ''),
        'vid_url': waifu.get('vid_url', '')
    }

    # Store waifu claim in user collection
    await user_collection.update_one(
        {'id': user_id},
        {
            '$set': {'claimed_waifu': True, 'first_name': first_name},
            '$push': {'characters': waifu_data},  
            '$inc': {'waifu_count': 1}  
        }
    )

    print(f"✅ Successfully updated database for {user_id}")

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

@app.on_callback_query(filters.regex(r"check_join_(\d+)"))
async def check_join(client: Client, callback_query):
    """Rechecks if the user has joined the required groups."""
    user_id = int(callback_query.matches[0].group(1))

    if callback_query.from_user.id != user_id:
        return await callback_query.answer("⚠️ This is not for you!", show_alert=True)

    if await has_joined_required_groups(user_id):
        await callback_query.message.edit_text("✅ **You have successfully joined the required groups! Now use /claim to get your waifu.**")
    else:
        await callback_query.answer("❌ You still haven't joined both groups!", show_alert=True)
        
