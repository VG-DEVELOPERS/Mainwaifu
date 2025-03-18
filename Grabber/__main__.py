import importlib
import time
import random
import asyncio
import re
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from Grabber import collection, user_totals_collection, user_collection, top_global_groups_collection, group_user_totals_collection, Grabberu
from Grabber import application, LOGGER
from Grabber.modules import ALL_MODULES

# Import all modules
for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)

# Track message counts, character spawns, and rarity control
locks = {}
message_counts = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
warned_users = {}
total_seals = {}
rarity_spawn_index = {}

# Rarity mapping with their respective conditions
rarity_map = {
    1: "⚪ Common",
    2: "🟢 Medium",
    3: "🟠 Rare",
    4: "🟡 Legendary",
    5: "💠 Cosmic",
    6: "💮 Exclusive",
    7: "🔮 Limited Edition"
}

# Spawn frequency conditions
rarity_spawn_counts = {
    "⚪ Common": 5,
    "🟢 Medium": 3,
    "🟠 Rare": 2,
    "🟡 Legendary": 1
}
special_rarity_thresholds = {
    "💠 Cosmic": {"messages": 5000, "seals": 200},
    "💮 Exclusive": {"messages": 10000, "seals": 100},
    "🔮 Limited Edition": {"messages": 15000, "limit": 50}
}

async def message_counter(update: Update, context: CallbackContext) -> None:
    """Tracks messages and spawns characters based on conditions."""
    chat_id = str(update.effective_chat.id)
    
    if chat_id not in message_counts:
        message_counts[chat_id] = 0
    message_counts[chat_id] += 1

    # Determine rarity to spawn
    rarity = get_rarity_to_spawn(chat_id)

    # Fetch character of that rarity
    character = await get_character_by_rarity(rarity)

    if not character:
        LOGGER.warning(f"No characters available for rarity {rarity}.")
        return

    sent_characters[chat_id] = character
    last_characters[chat_id] = character

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"A New {character['rarity']} Character Appeared...\nUse /seal <name> to add to your collection!",
        parse_mode='Markdown'
    )

def get_rarity_to_spawn(chat_id):
    """Determines which rarity to spawn based on message count."""
    count = message_counts[chat_id]

    for rarity, threshold in special_rarity_thresholds.items():
        if "messages" in threshold and count >= threshold["messages"]:
            return rarity

    for rarity, frequency in rarity_spawn_counts.items():
        if count % frequency == 0:
            return rarity

    return "⚪ Common"

async def get_character_by_rarity(rarity):
    """Fetch a random character of the given rarity."""
    characters = await collection.find({'rarity': rarity}).to_list(length=None)
    return random.choice(characters) if characters else None

async def seal(update: Update, context: CallbackContext) -> None:
    """Allows users to collect the character by guessing correctly."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return

    guess = ' '.join(context.args).strip().lower() if context.args else ''

    character_name = last_characters[chat_id]['name'].lower()
    if guess == character_name:
        await add_character_to_user(user_id, last_characters[chat_id])
        await update.message.reply_text(f"✅ {character_name} has been sealed into your collection!")
    else:
        await update.message.reply_text("❌ Wrong guess! Try again.")

async def add_character_to_user(user_id, character):
    """Adds a character to a user's collection."""
    await user_collection.update_one(
        {'id': user_id},
        {'$push': {'characters': character}},
        upsert=True
    )

async def fav(update: Update, context: CallbackContext) -> None:
    """Marks a character as favorite by ID."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /fav <character_id>")
        return

    character_id = context.args[0]
    user_data = await user_collection.find_one({'id': user_id})

    if not user_data or 'characters' not in user_data:
        await update.message.reply_text("❌ You have no characters to favorite.")
        return

    matched_character = next((char for char in user_data['characters'] if char['id'] == character_id), None)

    if not matched_character:
        await update.message.reply_text("❌ Character not found in your collection.")
        return

    await user_collection.update_one(
        {'id': user_id, 'characters.id': character_id}, 
        {'$set': {'characters.$.fav': True}}
    )

    await update.message.reply_text(f"⭐ {matched_character['name']} has been added to your favorites!")

# Register bot commands
application.add_handler(CommandHandler("seal", seal, block=False))
application.add_handler(CommandHandler("fav", fav, block=False))
application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    application.run_polling(drop_pending_updates=True)
    
