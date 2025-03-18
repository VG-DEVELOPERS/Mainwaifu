import importlib
import time
import random
import re
import asyncio
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from Grabber import collection, user_collection, Grabberu, application, LOGGER 

# Global tracking dictionaries
locks = {}
message_counts = {}
sent_characters = {}
last_characters = {}
first_correct_guesses = {}
warned_users = {}
spawn_tracker = {}

# Spawn Progression Rules
SPAWN_RULES = {
    "Common": {"count": 5, "next": "Medium"},
    "Medium": {"count": 3, "next": "Rare"},
    "Rare": {"count": 2, "next": "Legendary"},
    "Legendary": {"count": 1, "next": "Cosmic"},
    "Cosmic": {"count": 2, "next": "Exclusive"},
    "Exclusive": {"count": 1, "next": "Limited Edition"},
}

# Helper Function to Escape Markdown
def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

        # Determine which rarity to spawn next
        rarity = get_next_rarity(chat_id)

        if rarity:
            await send_character(update, context, rarity)

def get_next_rarity(chat_id):
    """Determines the next rarity to spawn based on spawn progression."""
    spawn_tracker.setdefault(chat_id, {"Common": 0, "Medium": 0, "Rare": 0, "Legendary": 0, "Cosmic": 0, "Exclusive": 0})

    for rarity, rule in SPAWN_RULES.items():
        if spawn_tracker[chat_id].get(rarity, 0) >= rule["count"]:
            spawn_tracker[chat_id][rarity] = 0  # Reset count
            spawn_tracker[chat_id][rule["next"]] += 1  # Increase next rarity count
            return rule["next"]

    spawn_tracker[chat_id]["Common"] += 1  # Default to Common
    return "Common"

async def send_character(update: Update, context: CallbackContext, rarity: str) -> None:
    chat_id = update.effective_chat.id

    available_characters = list(await collection.find({'rarity': rarity}).to_list(length=None))
    if not available_characters:
        return

    sent_characters.setdefault(chat_id, [])
    available_characters = [c for c in available_characters if c['id'] not in sent_characters[chat_id]]

    if not available_characters:
        sent_characters[chat_id] = []  
        available_characters = list(await collection.find({'rarity': rarity}).to_list(length=None))

    character = random.choice(available_characters)
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character

    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"A New {character['rarity']} Character Appeared!\nUse /guess Character Name to add to your Harem.",
        parse_mode='Markdown'
    )

async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return await update.message.reply_text("No character to guess currently.")

    if chat_id in first_correct_guesses:
        return await update.message.reply_text("❌ Already guessed by someone else. Try next time!")

    guess = ' '.join(context.args).lower() if context.args else ''

    if "()" in guess or "&" in guess.lower():
        return await update.message.reply_text("❌ Invalid characters in your guess.")

    character_name = last_characters[chat_id]['name'].lower().split()

    if sorted(character_name) == sorted(guess.split()) or any(part == guess for part in character_name):
        first_correct_guesses[chat_id] = user_id
        user_data = await user_collection.find_one({'id': user_id})

        if user_data:
            await user_collection.update_one({'id': user_id}, {'$push': {'characters': last_characters[chat_id]}})
        else:
            await user_collection.insert_one({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'characters': [last_characters[chat_id]],
            })

        keyboard = [[InlineKeyboardButton("See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(
            f"<b>{escape(update.effective_user.first_name)}</b> guessed correctly! ✅\n"
            f"🎐 **Name:** {last_characters[chat_id]['name']}\n"
            f"💮 **Anime:** {last_characters[chat_id]['anime']}\n"
            f"🐙 **Rarity:** {last_characters[chat_id]['rarity']}\n\n"
            "Character added to your Harem! Use /harem to view.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("❌ Incorrect name. Try again!")

async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    if not context.args:
        return await update.message.reply_text("Please provide a Character ID to mark as favorite.")

    character_id = context.args[0]

    user_data = await user_collection.find_one({'id': user_id}, projection={'characters': 1, 'favorites': 1})
    if not user_data:
        return await update.message.reply_text("❌ You haven't guessed any characters yet!")

    character = next((c for c in user_data['characters'] if c['id'] == character_id), None)
    if not character:
        return await update.message.reply_text("❌ This character is not in your collection.")

    await user_collection.update_one({'id': user_id}, {'$set': {'favorites': [character_id]}})

    await update.message.reply_text(f"⭐ Character **{character['name']}** has been marked as your favorite!")

def main() -> None:
    """Run bot."""
    application.add_handler(CommandHandler("guess", guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    main()
    
