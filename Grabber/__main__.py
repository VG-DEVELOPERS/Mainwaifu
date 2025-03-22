import importlib
import time
import random
import re
import asyncio
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from Grabber import (
    collection, top_global_groups_collection, group_user_totals_collection,
    user_collection, user_totals_collection, Grabberu, application, 
    SUPPORT_CHAT, UPDATE_CHAT, db, LOGGER
)
from Grabber.modules import ALL_MODULES

locks = {}
message_counts = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
last_user = {}
warned_users = {}
waifu_message = {}

for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)

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

    async with locks[chat_id]:
        if chat_id not in message_counts:
            message_counts[chat_id] = 0  

        chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_frequency.get('message_frequency', 100) if chat_frequency else 100

        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                await update.message.reply_text(f"⚠️ Don't Spam {update.effective_user.first_name}...\nYour Messages Will be ignored for 10 Minutes...")
                warned_users[user_id] = time.time()
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        message_counts[chat_id] += 1

        if message_counts[chat_id] % message_frequency == 0:
            await send_image(update, context)
            message_counts[chat_id] = 0  

async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    
    if chat_id not in message_counts:  
        message_counts[chat_id] = 0  

    all_characters = list(await collection.find({}).to_list(length=None))

    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    if len(sent_characters[chat_id]) == len(all_characters):
        sent_characters[chat_id] = []

    for rarity, threshold in special_rarity_thresholds.items():
        if message_counts[chat_id] % threshold == 0:
            available_characters = [c for c in all_characters if c['rarity'] == rarity]
            if available_characters:
                character = random.choice(available_characters)
                break
    else:
        rarity_cycle = [rarity for rarity, count in rarity_spawn_counts for _ in range(count)]
        required_rarity = rarity_cycle[message_counts[chat_id] % len(rarity_cycle)]

        available_characters = [c for c in all_characters if c['rarity'] == required_rarity] or all_characters
        character = random.choice(available_characters)

    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character

    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    waifu_message[chat_id] = await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"A New {character['rarity']} Character Appeared...\n/guess Character Name and add in Your Harem",
        parse_mode='Markdown'
    )

async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id
    user_guess = " ".join(context.args).strip().lower()

    if chat_id not in last_characters:
        await update.message.reply_text("No character is available to guess right now!")
        return

    character = last_characters[chat_id]
    correct_name = character["name"].lower()

    if user_guess == correct_name:
        if chat_id not in first_correct_guesses:
            first_correct_guesses[chat_id] = user_id
            await update.message.reply_text(f"🎉 {update.effective_user.first_name} guessed the character correctly! 🎊")
        else:
            await update.message.reply_text("Someone has already guessed this character!")
    else:
        await update.message.reply_text("❌ Incorrect guess. Try again!")

async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    favorites = await user_collection.find_one({"user_id": user_id}, {"favorites": 1})

    if not favorites or "favorites" not in favorites:
        await update.message.reply_text("You have no favorite characters yet.")
        return

    favorite_list = "\n".join([f"⭐ {fav}" for fav in favorites["favorites"]])
    await update.message.reply_text(f"Your Favorite Characters:\n{favorite_list}")

def main() -> None:
    application.add_handler(CommandHandler(["guess", "seal", "collect", "grab", "hunt"], guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

    application.run_polling(drop_pending_updates=True)
    
if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    main()
