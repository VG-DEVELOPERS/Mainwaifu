import random
from pyrogram import Client, filters
from Grabber import collection, user_collection, Grabberu as app
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton



# Allowed Group ID
ALLOWED_GROUP_ID = -1002528887253
CHANNEL_LINK = "https://t.me/seal_Your_WH_Group"

@app.on_message(filters.command("claim"))
async def claim_character(client, message: Message):
    """Allows users to claim a random character, but only in the allowed group."""

    if message.chat.id != ALLOWED_GROUP_ID:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 Join Channel", url=CHANNEL_LINK)]]
        )
        await message.reply(
            "🔒 You need to join the channels to claim!",
            reply_markup=keyboard
        )
        return

    user_id = message.from_user.id

    # Get a random character from the database
    characters = list(collection.find({}))
    
    if not characters:
        await message.reply("⚠️ No characters available in the database.")
        return
    
    random_character = random.choice(characters)
    
    file_id = random_character.get("file_id")
    character_name = random_character.get("name", "Unknown Character")
    bot_username = random_character.get("bot", "Unknown Bot")

    # Add to user's collection
    user_collection.update_one(
        {"user_id": user_id},
        {"$push": {"characters": random_character}},
        upsert=True
    )

    # Send the claimed character to the user
    await client.send_photo(
        chat_id=message.chat.id,
        photo=file_id,
        caption=f"🎉 You claimed: **{character_name}**\n🤖 Bot: {bot_username}"
    )
