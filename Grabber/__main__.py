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
last_user = {}
warned_users = {}

# Escape Markdown function
def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

# Message Counter for Spawn System
async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        # Fetch or set message frequency
        chat_settings = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_settings.get('message_frequency', 1) if chat_settings else 1

        # Anti-Spam: Prevent same user from spamming
        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                await update.message.reply_text(f"⚠️ Don't spam, {update.effective_user.first_name}. You will be ignored for 10 minutes.")
                warned_users[user_id] = time.time()
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        # Increment message count
        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

        # Spawn a character if the message count reaches the frequency
        if message_counts[chat_id] % message_frequency == 0:
            await spawn_character(update, context)
            message_counts[chat_id] = 0

# Character Spawn System
async def spawn_character(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    all_characters = list(await collection.find({}).to_list(length=None))

    if not all_characters:
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
        return

    character = random.choice(characters_of_rarity)
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character

    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    # Send the character image
    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"A **{character['rarity']}** character appeared!\nUse `/guess <character name>` to collect!",
        parse_mode='Markdown'
    )

# Guessing System
async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text("❌ This character has already been guessed!")
        return

    guess_text = ' '.join(context.args).lower() if context.args else ''
    character_name_parts = last_characters[chat_id]['name'].lower().split()

    # Check if the guess is correct
    if sorted(character_name_parts) == sorted(guess_text.split()) or any(part == guess_text for part in character_name_parts):
        first_correct_guesses[chat_id] = user_id

        # Update user's collection
        user = await user_collection.find_one({'id': user_id})
        if user:
            await user_collection.update_one({'id': user_id}, {'$push': {'characters': last_characters[chat_id]}})
        else:
            await user_collection.insert_one({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'characters': [last_characters[chat_id]]
            })

        keyboard = [[InlineKeyboardButton("See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(f"✅ **{last_characters[chat_id]['name']}** added to your harem!", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("❌ Incorrect name! Try again.")

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

# Favorite System
async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("⚠️ Please provide a Character ID.")
        return

    character_id = context.args[0]
    user = await user_collection.find_one({'id': user_id})

    if not user or 'characters' not in user:
        await update.message.reply_text("❌ You haven't collected any characters yet.")
        return

    character = next((c for c in user['characters'] if c['id'] == character_id), None)
    if not character:
        await update.message.reply_text("❌ This character is not in your collection.")
        return

    await user_collection.update_one({'id': user_id}, {'$set': {'favorites': [character_id]}})
    await update.message.reply_text(f"⭐ **{character['name']}** added to favorites!")

# Start Bot
def main() -> None:
    application.add_handler(CommandHandler(["guess", "grab", "hunt"], guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(CommandHandler("setfrequency", set_frequency, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    main()
            
