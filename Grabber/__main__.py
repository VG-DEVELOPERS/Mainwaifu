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

# Track user messages and bot logic
locks = {}
message_counts = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
warned_users = {}
last_user = {}

# Character spawn frequency mapping
rarity_map = {
    1: "⚪ Common", 
    2: "🟢 Medium", 
    3: "🟠 Rare", 
    4: "🟡 Legendary", 
    5: "💠 Cosmic", 
    6: "💮 Exclusive", 
    7: "🔮 Limited Edition"
}

rarity_spawn_counts = {
    "⚪ Common": 5, 
    "🟢 Medium": 3, 
    "🟠 Rare": 2, 
    "🟡 Legendary": 1, 
    "💠 Cosmic": 2, 
    "💮 Exclusive": 1, 
    "🔮 Limited Edition": 1
}

async def message_counter(update: Update, context: CallbackContext) -> None:
    """Tracks messages and triggers character spawns."""
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()

    async with locks[chat_id]:
        chat_settings = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_settings.get('message_frequency', 5) if chat_settings else 5

        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                await update.message.reply_text(f"⚠️ Stop spamming {update.effective_user.first_name}! Messages will be ignored for 10 minutes.")
                warned_users[user_id] = time.time()
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

        if message_counts[chat_id] % message_frequency == 0:
            await send_character(update, context)
            message_counts[chat_id] = 0

async def send_character(update: Update, context: CallbackContext) -> None:
    """Sends a character image based on rarity spawn frequency."""
    chat_id = update.effective_chat.id

    if chat_id not in sent_characters:
        sent_characters[chat_id] = {}

    for rarity, count in rarity_spawn_counts.items():
        sent_characters[chat_id][rarity] = sent_characters[chat_id].get(rarity, 0) + 1
        if sent_characters[chat_id][rarity] >= count:
            sent_characters[chat_id][rarity] = 0
            break
    else:
        rarity = "⚪ Common"

    available_characters = await collection.find({'rarity': rarity}).to_list(length=None)
    
    if not available_characters:
        LOGGER.warning(f"No characters available for rarity {rarity}")
        return

    character = random.choice(available_characters)
    last_characters[chat_id] = character

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"A {character['rarity']} character appeared!\nUse /seal <name> to capture it.",
        parse_mode='Markdown'
    )

async def seal(update: Update, context: CallbackContext) -> None:
    """Captures a character if the name is guessed correctly."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        await update.message.reply_text("No character to capture.")
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text(f'❌ Already captured by someone else.')
        return

    guess = ' '.join(context.args).lower() if context.args else ''
    name_parts = last_characters[chat_id]['name'].lower().split()

    if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):
        first_correct_guesses[chat_id] = user_id
        character = last_characters[chat_id]

        await user_collection.update_one({'id': user_id}, {'$push': {'characters': character}}, upsert=True)
        await group_user_totals_collection.update_one({'user_id': user_id, 'group_id': chat_id}, {'$inc': {'count': 1}}, upsert=True)
        await top_global_groups_collection.update_one({'group_id': chat_id}, {'$inc': {'count': 1}}, upsert=True)

        keyboard = [[InlineKeyboardButton(f"See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(
            f'🎉 <b>{escape(update.effective_user.first_name)}</b> captured {character["name"]}!\nRarity: {character["rarity"]}',
            parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text('❌ Incorrect name. Try again!')

async def fav(update: Update, context: CallbackContext) -> None:
    """Adds/removes a character from favorites."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text('Provide a character ID to favorite.')
        return

    character_id = context.args[0]
    user = await user_collection.find_one({'id': user_id})

    if not user:
        await update.message.reply_text('You have no characters.')
        return

    character = next((c for c in user['characters'] if c['id'] == character_id), None)
    if not character:
        await update.message.reply_text('Character not found in your collection.')
        return

    if 'favorites' in user and character_id in user['favorites']:
        await user_collection.update_one({'id': user_id}, {'$pull': {'favorites': character_id}})
        await update.message.reply_text(f'❌ Removed {character["name"]} from favorites.')
    else:
        await user_collection.update_one({'id': user_id}, {'$push': {'favorites': character_id}})
        await update.message.reply_text(f'⭐ {character["name"]} added to favorites!')

async def set_frequency(update: Update, context: CallbackContext) -> None:
    """Sets message frequency for spawning characters (admin only)."""
    user_id = update.effective_user.id
    chat_id = str(update.effective_chat.id)

    if user_id != 7717913705:
        await update.message.reply_text("❌ You don't have permission to set frequency.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ Usage: /setfrequency <number>")
        return

    frequency = max(1, int(context.args[0]))
    await user_totals_collection.update_one({'chat_id': chat_id}, {'$set': {'message_frequency': frequency}}, upsert=True)
    await update.message.reply_text(f"✅ Spawn frequency set to {frequency} messages.")

# Register bot commands
application.add_handler(CommandHandler("seal", seal, block=False))
application.add_handler(CommandHandler("fav", fav, block=False))
application.add_handler(CommandHandler("setfrequency", set_frequency, block=False))
application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

# Start bot
if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    application.run_polling(drop_pending_updates=True)
            
