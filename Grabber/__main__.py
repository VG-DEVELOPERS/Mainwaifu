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
from Grabber import application, SUPPORT_CHAT, UPDATE_CHAT, db, LOGGER
from Grabber.modules import ALL_MODULES

locks = {}
message_counts = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
last_grab = {}
waifu_message = {}

for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)

last_user = {}
warned_users = {}

rarity_map = {
    1: "⚪ Common", 
    2: "🟢 Medium", 
    3: "🟠 Rare", 
    4: "🟡 Legendary", 
    5: "💠 Cosmic", 
    6: "💮 Exclusive", 
    7: "🔮 Limited Edition"
}

rarity_spawn_counts = [
    ("⚪ Common", 5), 
    ("🟢 Medium", 3), 
    ("🟠 Rare", 2), 
    ("🟡 Legendary", 1)
]

special_rarity_thresholds = {
    "💠 Cosmic": 5000,
    "💮 Exclusive": 10000,
    "🔮 Limited Edition": 15000
}

def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_frequency.get('message_frequency', 100) if chat_frequency else 100

        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                await update.message.reply_text(
                    f"⚠️ Don't Spam {update.effective_user.first_name}...\nYour Messages Will be ignored for 10 Minutes..."
                )
                warned_users[user_id] = time.time()
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

        if message_counts[chat_id] % message_frequency == 0:
            await send_image(update, context)
            message_counts[chat_id] = 0

async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    all_characters = list(await collection.find({}).to_list(length=None))

    if chat_id not in sent_characters:
        sent_characters[chat_id] = []
    
    if len(sent_characters[chat_id]) == len(all_characters):
        sent_characters[chat_id] = []

    # Check if a special rarity character should spawn
    for rarity, threshold in special_rarity_thresholds.items():
        if message_counts[chat_id] % threshold == 0:
            available_characters = [c for c in all_characters if c['rarity'] == rarity]
            if available_characters:
                character = random.choice(available_characters)
                break
    else:
        # Rarity-based spawn cycle
        rarity_cycle = [rarity for rarity, count in rarity_spawn_counts for _ in range(count)]
        current_rarity_index = message_counts[chat_id] % len(rarity_cycle)
        required_rarity = rarity_cycle[current_rarity_index]

        available_characters = [c for c in all_characters if c['rarity'] == required_rarity] or all_characters
        character = random.choice(available_characters)

    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character

    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    waifu_message[chat_id] = await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"""A New {character['rarity']} Character Appeared...\n/guess Character Name and add in Your Harem""",
        parse_mode='Markdown'
    )

def main() -> None:
    """Run bot."""
    application.add_handler(CommandHandler(["guess", "seal", "collect", "grab", "hunt"], guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

    application.run_polling(drop_pending_updates=True)
    
if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    main()
    
