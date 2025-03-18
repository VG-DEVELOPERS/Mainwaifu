import importlib
import time
import random
import re
import asyncio
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from Grabber import collection, top_global_groups_collection, group_user_totals_collection, user_collection, user_totals_collection, Grabberu
from Grabber import application, LOGGER
from Grabber.modules import ALL_MODULES

# Load all modules
for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)

# Bot Variables
locks = {}
message_counts = {}
sent_characters = {}
last_characters = {}
first_correct_guesses = {}

# Default spawn frequency (fallback)
DEFAULT_FREQUENCY = 5  

# Escape Markdown function
def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

# Message Counter for Spawn System
async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        # Fetch message frequency (default is 5)
        chat_settings = await user_totals_collection.find_one({'chat_id': chat_id})  
        message_frequency = chat_settings.get('message_frequency', DEFAULT_FREQUENCY) if chat_settings else DEFAULT_FREQUENCY

        # Increment message count
        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

        # Debugging: Print message count to check if it's increasing
        LOGGER.info(f"Chat {chat_id} - Message Count: {message_counts[chat_id]} (Trigger at {message_frequency})")

        # Spawn a character if the message count reaches the frequency
        if message_counts[chat_id] >= message_frequency:
            await spawn_character(update, context)
            message_counts[chat_id] = 0  # Reset count after spawn

# Character Spawn System
async def spawn_character(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    all_characters = list(await collection.find({}).to_list(length=None))

    if not all_characters:
        LOGGER.warning("No characters found in the database.")
        return

    # Check if chat has already spawned all characters
    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    if len(sent_characters[chat_id]) == len(all_characters):
        sent_characters[chat_id] = []

    # Define Rarity Frequency
    spawn_order = ["Common"] * 5 + ["Medium"] * 3 + ["Rare"] * 2 + ["Legendary"] + ["Cosmic"] * 2 + ["Exclusive"] + ["Limited Edition"]
    chosen_rarity = spawn_order[len(sent_characters[chat_id]) % len(spawn_order)]

    # Select a character of the chosen rarity
    characters_of_rarity = [c for c in all_characters if c['rarity'] == chosen_rarity and c['id'] not in sent_characters[chat_id]]
    if not characters_of_rarity:
        LOGGER.warning(f"No characters available for rarity {chosen_rarity}.")
        return

    character = random.choice(characters_of_rarity)
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character

    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    LOGGER.info(f"Spawned {character['name']} ({character['rarity']}) in Chat {chat_id}")

    # Send the character image
    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"A **{character['rarity']}** character appeared!\nUse `/seal <character name>` to collect!",
        parse_mode='Markdown'
    )

# Seal (Capture) Command
async def seal(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        await update.message.reply_text("❌ No character is available to seal right now!")
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text("❌ Someone already sealed this character. Try next time!")
        return

    guess = ' '.join(context.args).lower() if context.args else ''

    if "()" in guess or "&" in guess.lower():
        await update.message.reply_text("❌ Invalid input! Special characters are not allowed.")
        return

    name_parts = last_characters[chat_id]['name'].lower().split()
    if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):
        first_correct_guesses[chat_id] = user_id

        await user_collection.update_one(
            {'id': user_id}, 
            {'$set': {'username': update.effective_user.username, 'first_name': update.effective_user.first_name}, 
             '$push': {'characters': last_characters[chat_id]}}, upsert=True
        )

        keyboard = [[InlineKeyboardButton("View Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(
            f'✅ <b>{escape(update.effective_user.first_name)}</b> sealed a new character!\n'
            f'👤 **Name:** {last_characters[chat_id]["name"]}\n'
            f'📺 **Anime:** {last_characters[chat_id]["anime"]}\n'
            f'🌟 **Rarity:** {last_characters[chat_id]["rarity"]}\n\n'
            'This character has been added to your harem! Use /harem to view your collection.',
            parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("❌ Incorrect name! Try again.")

# Favorite Character Command
async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("❌ Please provide a character ID.")
        return

    character_id = context.args[0]
    user = await user_collection.find_one({'id': user_id})

    if not user:
        await update.message.reply_text("❌ You haven't sealed any characters yet.")
        return

    character = next((c for c in user['characters'] if c['id'] == character_id), None)
    if not character:
        await update.message.reply_text("❌ Character not found in your collection.")
        return

    await user_collection.update_one({'id': user_id}, {'$set': {'favorites': [character_id]}})
    await update.message.reply_text(f"⭐ {character['name']} has been added to your favorites!")

# Set Frequency Command
async def set_frequency(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = str(update.effective_chat.id)

    if user_id != 7717913705:
        await update.message.reply_text("❌ You don't have permission to set the frequency.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ Usage: `/setfrequency <number>`")
        return

    frequency = int(context.args[0])
    if frequency < 1:
        await update.message.reply_text("⚠️ Frequency must be at least 1 message.")
        return

    await user_totals_collection.update_one({'chat_id': chat_id}, {'$set': {'message_frequency': frequency}}, upsert=True)
    await update.message.reply_text(f"✅ Spawn frequency set to {frequency} messages.")

# Start Bot
application.add_handler(CommandHandler("seal", seal, block=False))
application.add_handler(CommandHandler("fav", fav, block=False))
application.add_handler(CommandHandler("setfrequency", set_frequency, block=False))
application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

application.run_polling(drop_pending_updates=True)
