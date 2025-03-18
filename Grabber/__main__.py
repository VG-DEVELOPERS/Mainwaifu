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

# Load all modules
for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)

# Bot tracking data
locks = {}
message_counts = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
warned_users = {}
last_user = {}
total_seals = {}

# Rarity mapping
rarity_map = {
    1: "⚪ Common", 
    2: "🟢 Medium", 
    3: "🟠 Rare", 
    4: "🟡 Legendary", 
    5: "💠 Cosmic", 
    6: "💮 Exclusive", 
    7: "🔮 Limited Edition"
}

# Spawn frequency mapping
rarity_spawn_counts = [
    ("⚪ Common", 5), 
    ("🟢 Medium", 3), 
    ("🟠 Rare", 2), 
    ("🟡 Legendary", 1), 
    ("💠 Cosmic", 2), 
    ("💮 Exclusive", 1), 
    ("🔮 Limited Edition", 1)
]

# Message thresholds for special rarity spawns
cosmic_threshold = 5000
exclusive_threshold = 10000
limited_edition_threshold = 15000
seal_limit = 50
cosmic_seal_required = 200
exclusive_seal_required = 100

# Function to mark favorite character by ID
async def fav(update: Update, context: CallbackContext) -> None:
    """Marks a character as favorite using character ID."""
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

    await update.message.reply_text(f"⭐ {matched_character['name']} has been marked as your favorite!")

# Function to spawn characters based on frequency
async def spawn_character(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)

    # Fetch total messages for the chat
    chat_data = await user_totals_collection.find_one({'chat_id': chat_id})
    total_messages = chat_data.get('total_messages', 0) if chat_data else 0

    # Select rarity based on message count
    if total_messages >= limited_edition_threshold:
        rarity = "🔮 Limited Edition"
    elif total_messages >= exclusive_threshold:
        rarity = "💮 Exclusive"
    elif total_messages >= cosmic_threshold:
        rarity = "💠 Cosmic"
    else:
        rarity = random.choice([r[0] for r in rarity_spawn_counts])

    # Fetch character from database
    character = await collection.find_one({'rarity': rarity})

    if not character:
        await update.message.reply_text(f"⚠️ No characters available for rarity {rarity}.")
        return

    # Store last character for guess check
    last_characters[chat_id] = character
    sent_characters[chat_id] = character['id']

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"A new {character['rarity']} character appeared!\nUse /seal <name> to collect.",
        parse_mode='Markdown'
    )

# Function to seal (capture) character
async def seal(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text("❌ Already sealed by someone! Try next time.")
        return

    guess = ' '.join(context.args).lower() if context.args else ''
    correct_name = last_characters[chat_id]['name'].lower()

    if correct_name == guess:
        first_correct_guesses[chat_id] = user_id

        # Store user details
        user = await user_collection.find_one({'id': user_id})
        if user:
            await user_collection.update_one(
                {'id': user_id}, 
                {'$push': {'characters': last_characters[chat_id]}}
            )
        else:
            await user_collection.insert_one({
                'id': user_id,
                'characters': [last_characters[chat_id]],
            })

        # Increase chat total seals
        total_seals[chat_id] = total_seals.get(chat_id, 0) + 1

        # Stop spawning if seal limit is reached
        if total_seals[chat_id] >= seal_limit:
            await update.message.reply_text("⚠️ Seal limit reached for this chat!")
            return

        await update.message.reply_text(f"✅ {last_characters[chat_id]['name']} has been sealed and added to your collection!")

    else:
        await update.message.reply_text("❌ Incorrect name! Try again.")

# Function to set custom frequency
async def set_frequency(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = str(update.effective_chat.id)

    if user_id != 7717913705:
        await update.message.reply_text("❌ You don't have permission to set the frequency.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ Usage: /setfrequency <number>")
        return

    frequency = int(context.args[0])

    if frequency < 1:
        await update.message.reply_text("⚠️ Frequency must be at least 1 message.")
        return

    await user_totals_collection.update_one(
        {'chat_id': chat_id},
        {'$set': {'message_frequency': frequency}},
        upsert=True
    )

    await update.message.reply_text(f"✅ Spawn frequency set to {frequency} messages.")

# Register bot commands
application.add_handler(CommandHandler("fav", fav, block=False))
application.add_handler(CommandHandler("seal", seal, block=False))
application.add_handler(CommandHandler("setfrequency", set_frequency, block=False))
application.add_handler(MessageHandler(filters.ALL, spawn_character, block=False))

# Start bot
if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    application.run_polling(drop_pending_updates=True)
    
