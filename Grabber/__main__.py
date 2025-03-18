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

locks = {}
message_counts = {}
warned_users = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}

# Spawn tracking
spawn_progress = {}

# Define rarity spawn system
rarity_progression = [
    ("⚪ Common", 5),  
    ("🟢 Medium", 3),  
    ("🟠 Rare", 2),  
    ("🟡 Legendary", 1),  
    ("💠 Cosmic", 2),  
    ("💮 Exclusive", 1),  
    ("🔮 Limited Edition", 1)  
]

# Load all modules dynamically
for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)

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
        if chat_id in warned_users and time.time() - warned_users[chat_id] < 600:
            return  

        # Set default message frequency
        chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_frequency.get('message_frequency', 1) if chat_frequency else 1  

        # Initialize message count tracking
        if chat_id in message_counts:
            message_counts[chat_id] += 1
        else:
            message_counts[chat_id] = 1

        # Spawn character based on message count
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

    # Determine rarity based on progression
    if chat_id not in spawn_progress:
        spawn_progress[chat_id] = {rarity: 0 for rarity, _ in rarity_progression}

    selected_rarity = "⚪ Common"  
    for rarity, threshold in rarity_progression:
        if spawn_progress[chat_id][rarity] >= threshold:
            spawn_progress[chat_id][rarity] = 0  
            selected_rarity = rarity
            break

    # Filter characters by rarity
    available_characters = [c for c in all_characters if c['rarity'] == selected_rarity and c['id'] not in sent_characters[chat_id]]
    
    if not available_characters:
        available_characters = [c for c in all_characters if c['id'] not in sent_characters[chat_id]]  

    character = random.choice(available_characters)
    
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character
    first_correct_guesses.pop(chat_id, None)  

    spawn_progress[chat_id][selected_rarity] += 1

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"""A New {character['rarity']} Character Appeared...\n/guess Character Name and add in Your Harem""",
        parse_mode='Markdown'
    )

async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_text(f'❌ Already Guessed By Someone. Try Next Time.')
        return

    guess = ' '.join(context.args).lower() if context.args else ''
    
    if "()" in guess or "&" in guess:
        await update.message.reply_text("Invalid characters in your guess! ❌")
        return

    name_parts = last_characters[chat_id]['name'].lower().split()
    if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):
        first_correct_guesses[chat_id] = user_id

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

        keyboard = [[InlineKeyboardButton(f"See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]
        
        await update.message.reply_text(
            f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> You Guessed a New Character ✅️ \n'
            f'𝗡𝗔𝗠𝗘: <b>{last_characters[chat_id]["name"]}</b> \n'
            f'𝗔𝗡𝗜𝗠𝗘: <b>{last_characters[chat_id]["anime"]}</b> \n'
            f'𝗥𝗔𝗥𝗜𝗧𝗬: <b>{last_characters[chat_id]["rarity"]}</b>\n\n'
            f'This Character added in Your harem.. use /harem To see your harem',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text('Please enter the correct character name! ❌')

async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text('Please provide Character ID.')
        return

    character_id = context.args[0]

    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_text('You have not guessed any characters yet.')
        return

    character = next((c for c in user['characters'] if c['id'] == character_id), None)
    if not character:
        await update.message.reply_text('This Character is not in your collection.')
        return

    user['favorites'] = [character_id]
    await user_collection.update_one({'id': user_id}, {'$set': {'favorites': user['favorites']}})

    await update.message.reply_text(f'Character {character["name"]} has been added to your favorites!')

def main() -> None:
    application.add_handler(CommandHandler(["guess", "protecc", "collect", "grab", "hunt"], guess, block=False))
    application.add_handler(CommandHandler("fav", fav, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    main()
        
