import importlib
import time
import random
import re
import asyncio
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from Grabber import (collection, user_collection, user_totals_collection, Grabberu)
from Grabber import application, LOGGER

locks = {}
message_counts = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
last_grab = {}
waifu_message = {}
last_user = {}
warned_users = {}

rarity_map = {
    "⚪ Common": 5,
    "🟢 Medium": 3,
    "🟠 Rare": 2,
    "🟡 Legendary": 1
}

special_rarity_thresholds = {
    "💠 Cosmic": 5000,
    "💮 Exclusive": 10000,
    "🔮 Limited Edition": 15000
}

for module_name in importlib.import_module("Grabber.modules").ALL_MODULES:
    importlib.import_module(f"Grabber.modules.{module_name}")

def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    
    async with locks[chat_id]:
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

    for rarity, threshold in special_rarity_thresholds.items():
        if message_counts[chat_id] % threshold == 0:
            available_characters = [c for c in all_characters if c['rarity'] == rarity]
            if available_characters:
                character = random.choice(available_characters)
                break
    else:
        rarity_cycle = sum(([rarity] * count for rarity, count in rarity_map.items()), [])
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
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return

    if chat_id in first_correct_guesses:
        last_grabber_id = first_correct_guesses[chat_id]
        last_grabber_user = await user_collection.find_one({'id': last_grabber_id})
        last_grabber_name = last_grabber_user['first_name'] if last_grabber_user else 'Unknown User'
        await update.message.reply_text(
            f'⚠ Waifu already grabbed by <a href="tg://openmessage?user_id={last_grabber_id}">{escape(last_grabber_name)}</a>.\nℹ Wait for a new waifu to appear.',
            parse_mode='HTML'
        )
        return

    guess = ' '.join(context.args).lower() if context.args else ''
    
    if "()" in guess or "&" in guess.lower():
        await update.message.reply_text("Nahh You Can't use This Types of words in your guess..❌️")
        return

    name_parts = last_characters[chat_id]['name'].lower().split()
    
    if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):
        first_correct_guesses[chat_id] = user_id
        last_grab[chat_id] = user_id

        await user_collection.update_one({'id': user_id}, {'$push': {'characters': last_characters[chat_id]}}, upsert=True)

        keyboard = [[InlineKeyboardButton(f"See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(
            f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> You Guessed a New Character ✅️ \n\n𝗡𝗔𝗠𝗘: <b>{last_characters[chat_id]["name"]}</b> \n𝗔𝗡𝗜𝗠𝗘: <b>{last_characters[chat_id]["anime"]}</b> \n𝗥𝗔𝗥𝗜𝗧𝗬: <b>{last_characters[chat_id]["rarity"]}</b>\n\nThis Character added to your harem. Use /harem to see your harem.',
            parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text('Please Write Correct Character Name... ❌️')

async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text('Please provide Character id...')
        return

    character_id = context.args[0]

    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_text('You have not Guessed any characters yet....')
        return

    await user_collection.update_one({'id': user_id}, {'$set': {'favorites': [character_id]}})

    await update.message.reply_text(f'Character has been added to your favorite...')

def main() -> None:
    application.add_handler(CommandHandler(["guess", "collect", "grab", "hunt"], guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    main()
  
