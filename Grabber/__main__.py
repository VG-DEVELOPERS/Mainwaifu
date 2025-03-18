import importlib
import time
import random
import re
import asyncio
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from Grabber import (collection, top_global_groups_collection, group_user_totals_collection,
                     user_totals_collection, Grabberu)
from Grabber import application, LOGGER
from Grabber.modules import ALL_MODULES

# Load all modules
for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)

# Data tracking
locks = {}
message_counts = {}
last_characters = {}  
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
special_rarity_thresholds = {
    "💠 Cosmic": 5000,
    "💮 Exclusive": 10000,
    "🔮 Limited Edition": 15000
}

# Seal Limits
seal_limits = {
    "💠 Cosmic": 200,
    "💮 Exclusive": 100,
    "🔮 Limited Edition": 50
}

# Track seals per rarity
sealed_characters = {rarity: 0 for rarity in seal_limits}

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
            await send_character(update, context)
            message_counts[chat_id] = 0

async def send_character(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    all_characters = list(await collection.find({}).to_list(length=None))
    
    if not all_characters:
        return

    if chat_id not in last_characters:
        last_characters[chat_id] = []

    available_characters = [c for c in all_characters if c['id'] not in last_characters[chat_id]]
    
    if not available_characters:
        last_characters[chat_id] = []
        available_characters = all_characters

    character = random.choice(available_characters)
    last_characters[chat_id].append(character['id'])

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"""A New {character['rarity']} Character Appeared...\n/seal Character Name to capture!""",
        parse_mode='Markdown'
    )

async def seal(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        await update.message.reply_text("❌ No character available to capture. Wait for the next spawn.")
        return

    guess = ' '.join(context.args).lower() if context.args else ''
    character = next((c for c in await collection.find({'id': {'$in': last_characters[chat_id]}}).to_list(length=None)
                      if sorted(c['name'].lower().split()) == sorted(guess.split())), None)

    if not character:
        await update.message.reply_text("❌ Incorrect name! Try again.")
        return

    last_characters[chat_id].remove(character['id'])

    rarity = character['rarity']
    if rarity in sealed_characters and sealed_characters[rarity] >= seal_limits[rarity]:
        await update.message.reply_text(f"⚠️ Seal limit reached for {rarity}! Cannot capture more.")
        return

    sealed_characters[rarity] += 1
    await collection.update_one({'id': character['id']}, {'$set': {'sealed_by': user_id}})

    keyboard = [[InlineKeyboardButton(f"View Collection", switch_inline_query_current_chat=f"collection.{user_id}")]]
    await update.message.reply_text(
        f"✅ <b>{escape(update.effective_user.first_name)}</b> captured <b>{character['name']}</b> from <b>{character['anime']}</b>!\n\n📜 Rarity: {rarity}",
        parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def find_limited(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    limited_characters = await collection.find({'sealed_by': user_id, 'rarity': '🔮 Limited Edition'}).to_list(length=None)

    if not limited_characters:
        await update.message.reply_text("You have no 🔮 Limited Edition characters in your collection.")
        return

    character_list = '\n'.join([f"- {c['name']} ({c['anime']})" for c in limited_characters])
    await update.message.reply_text(f"🔮 **Limited Edition Characters:**\n\n{character_list}", parse_mode='Markdown')

def main() -> None:
    """Run bot."""
    application.add_handler(CommandHandler("seal", seal, block=False))
    application.add_handler(CommandHandler("find", find_limited, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    main()
  
