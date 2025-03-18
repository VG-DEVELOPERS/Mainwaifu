import importlib
import time
import random
import re
import asyncio
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from Grabber import (
    collection,
    top_global_groups_collection,
    group_user_totals_collection,
    user_collection,
    user_totals_collection,
    Grabberu,
    application,
    LOGGER,
)
from Grabber.modules import ALL_MODULES

# Load all bot modules
for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)

# Rarity System
rarity_map = {
    1: "⚪ Common",
    2: "🟢 Medium",
    3: "🟠 Rare",
    4: "🟡 Legendary",
    5: "💠 Cosmic",
    6: "💮 Exclusive",
    7: "🔮 Limited Edition",
}

# Tracking message counters and spam control
locks = {}
message_counts = {}
sent_characters = {}
first_correct_guesses = {}
last_characters = {}
warned_users = {}


def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)


async def message_counter(update: Update, context: CallbackContext) -> None:
    """Counts messages and spawns characters at the defined frequency."""
    chat_id = str(update.effective_chat.id)

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    
    async with locks[chat_id]:
        chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id}) or {}
        message_frequency = chat_frequency.get('message_frequency', 5)  # Default: 5 messages

        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

        if message_counts[chat_id] >= message_frequency:
            await send_character(update, context)
            message_counts[chat_id] = 0  # Reset counter


async def send_character(update: Update, context: CallbackContext) -> None:
    """Sends a character image with rarity logic."""
    chat_id = update.effective_chat.id
    all_characters = list(await collection.find({}).to_list(length=None))

    if not all_characters:
        LOGGER.warning(f"No characters available for chat {chat_id}")
        return

    # Determine rarity based on the spawn system
    spawn_history = sent_characters.get(chat_id, [])
    rarity_level = 1  # Default: Common

    if spawn_history.count(1) >= 5:
        rarity_level = 2  # Spawn Medium
    if spawn_history.count(2) >= 3:
        rarity_level = 3  # Spawn Rare
    if spawn_history.count(3) >= 2:
        rarity_level = 4  # Spawn Legendary
    if spawn_history.count(4) >= 1:
        rarity_level = 5  # Spawn Cosmic
    if spawn_history.count(5) >= 2:
        rarity_level = 6  # Spawn Exclusive
    if spawn_history.count(6) >= 1:
        rarity_level = 7  # Spawn Limited Edition

    # Select a character of the determined rarity
    available_characters = [c for c in all_characters if c['rarity'] == rarity_map[rarity_level]]

    if not available_characters:
        LOGGER.warning(f"No characters available for rarity {rarity_map[rarity_level]}")
        return

    character = random.choice(available_characters)
    sent_characters[chat_id].append(rarity_level)  # Track spawned rarity
    last_characters[chat_id] = character
    first_correct_guesses.pop(chat_id, None)

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"A new {character['rarity']} character has appeared!\nUse /seal <name> to capture it.",
        parse_mode='Markdown'
    )


async def seal(update: Update, context: CallbackContext) -> None:
    """Handles character capture (previously 'guess')."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text("❌ Someone has already sealed this character!")
        return

    guess = ' '.join(context.args).lower() if context.args else ''

    if "()" in guess or "&" in guess.lower():
        await update.message.reply_text("❌ Invalid characters in name.")
        return

    correct_name = last_characters[chat_id]['name'].lower()
    if sorted(correct_name.split()) == sorted(guess.split()) or any(part == guess for part in correct_name.split()):
        first_correct_guesses[chat_id] = user_id

        # Store character in user's collection
        await user_collection.update_one(
            {'id': user_id},
            {'$push': {'characters': last_characters[chat_id]}},
            upsert=True
        )

        keyboard = [[InlineKeyboardButton("See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(
            f"✅ <b>{escape(update.effective_user.first_name)}</b> sealed a character!\n"
            f"𝗡𝗔𝗠𝗘: <b>{last_characters[chat_id]['name']}</b>\n"
            f"𝗔𝗡𝗜𝗠𝗘: <b>{last_characters[chat_id]['anime']}</b>\n"
            f"𝗥𝗔𝗥𝗜𝗧𝗬: <b>{last_characters[chat_id]['rarity']}</b>\n\n"
            f"This character is now in your harem! Use /harem to view.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("❌ Incorrect name. Try again!")


async def fav(update: Update, context: CallbackContext) -> None:
    """Marks a character as a favorite."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /fav <character_id>")
        return

    character_id = context.args[0]
    user = await user_collection.find_one({'id': user_id})

    if not user or not any(c['id'] == character_id for c in user.get('characters', [])):
        await update.message.reply_text("❌ Character not found in your collection.")
        return

    await user_collection.update_one({'id': user_id}, {'$set': {'favorites': [character_id]}})
    await update.message.reply_text("✅ Character marked as favorite!")


async def set_frequency(update: Update, context: CallbackContext) -> None:
    """Allows the bot owner to set spawn frequency."""
    user_id = update.effective_user.id
    chat_id = str(update.effective_chat.id)

    if user_id != 7717913705:
        await update.message.reply_text("❌ You don't have permission to change frequency.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ Usage: /setfrequency <number>")
        return

    frequency = max(1, int(context.args[0]))
    await user_totals_collection.update_one({'chat_id': chat_id}, {'$set': {'message_frequency': frequency}}, upsert=True)
    await update.message.reply_text(f"✅ Spawn frequency set to {frequency} messages.")


def main():
    application.add_handler(CommandHandler("seal", seal, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(CommandHandler("setfrequency", set_frequency, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    main()
    
