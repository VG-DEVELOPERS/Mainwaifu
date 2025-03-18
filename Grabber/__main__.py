import importlib
import time
import random
import re
import asyncio
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from Grabber import (collection, top_global_groups_collection, group_user_totals_collection,
                     user_collection, user_totals_collection, Grabberu)
from Grabber import application, LOGGER
from Grabber.modules import ALL_MODULES

# Load all modules
for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)

# Data tracking
locks = {}
message_counts = {}
last_characters = {}  # Stores the last spawned character for each chat
first_correct_guesses = {}
total_seals = {}

# Rarity Mapping
rarity_map = {
    1: "⚪ Common", 
    2: "🟢 Medium", 
    3: "🟠 Rare", 
    4: "🟡 Legendary", 
    5: "💠 Cosmic", 
    6: "💮 Exclusive", 
    7: "🔮 Limited Edition"
}

# Spawn Rates
rarity_spawn_counts = [
    ("⚪ Common", 5), 
    ("🟢 Medium", 3), 
    ("🟠 Rare", 2), 
    ("🟡 Legendary", 1)
]

# Special Rarity Message Thresholds
cosmic_threshold = 5000
exclusive_threshold = 10000
limited_edition_threshold = 15000
seal_limit = 50

def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

# Track Messages and Trigger Character Spawns
async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    
    lock = locks[chat_id]

    async with lock:
        chat_data = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_data.get('message_frequency', 100) if chat_data else 100

        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

        if message_counts[chat_id] % message_frequency == 0:
            await spawn_character(update, context)
            message_counts[chat_id] = 0

# Spawn a Character
async def spawn_character(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)

    chat_data = await user_totals_collection.find_one({'chat_id': chat_id})
    total_messages = chat_data.get('total_messages', 0) if chat_data else 0

    # Determine rarity based on message count
    if total_messages >= limited_edition_threshold:
        rarity = "🔮 Limited Edition"
    elif total_messages >= exclusive_threshold:
        rarity = "💮 Exclusive"
    elif total_messages >= cosmic_threshold:
        rarity = "💠 Cosmic"
    else:
        rarity = random.choices(
            [r[0] for r in rarity_spawn_counts],
            [r[1] for r in rarity_spawn_counts]
        )[0]

    # Fetch a unique character from the database
    character = await collection.find_one({'rarity': rarity})

    if not character:
        await update.message.reply_text(f"⚠️ No available characters for rarity {rarity}.")
        return

    last_characters[chat_id] = character  # Store the spawned character

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"A {rarity} character appeared! Use /guess <name> to capture.",
        parse_mode='Markdown'
    )

# Capture (Seal) Character
async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        await update.message.reply_text("❌ No character available to capture. Wait for the next spawn.")
        return

    character = last_characters[chat_id]  # Retrieve last spawned character
    guess_name = ' '.join(context.args).lower() if context.args else ''
    correct_name = character['name'].lower()

    if guess_name == correct_name:
        user = await user_collection.find_one({'id': user_id})

        if user:
            await user_collection.update_one({'id': user_id}, {'$push': {'characters': character}})
        else:
            await user_collection.insert_one({'id': user_id, 'characters': [character]})

        total_seals[chat_id] = total_seals.get(chat_id, 0) + 1
        if total_seals[chat_id] >= seal_limit:
            await update.message.reply_text("⚠️ Seal limit reached for this chat!")
            return

        await update.message.reply_text(f"✅ {character['name']} has been added to your collection!")

        del last_characters[chat_id]  # Remove character after it's sealed

    else:
        await update.message.reply_text("❌ Incorrect name! Try again.")

# Mark Favorite Character
async def fav(update: Update, context: CallbackContext) -> None:
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

    await user_collection.update_one({'id': user_id, 'characters.id': character_id}, {'$set': {'characters.$.fav': True}})

    await update.message.reply_text(f"⭐ {matched_character['name']} has been marked as your favorite!")

# Register Handlers
application.add_handler(CommandHandler(["guess", "seal"], guess, block=False))
application.add_handler(CommandHandler("fav", fav, block=False))
application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

# Start Bot
if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    application.run_polling(drop_pending_updates=True)
  
