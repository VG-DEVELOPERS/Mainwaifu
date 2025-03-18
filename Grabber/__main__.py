import importlib
import random
import asyncio
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters

from Grabber import collection, user_totals_collection, user_collection, Grabberu
from Grabber import application, LOGGER
from Grabber.modules import ALL_MODULES

# Load all modules
for module_name in ALL_MODULES:
    importlib.import_module("Grabber.modules." + module_name)

# Bot tracking data
last_characters = {}
total_seals = {}

# Rarity mapping
rarity_map = {
    1: "⚪ Common", 
    2: "🟢 Medium", 
    3: "🟠 Rare", 
    4: "🟡 Legendary", 
    5: "💠 Cosmic", 
    6: "💮 Exclusive", 
    7: "🔮 Limited Edition"
}

# Normal spawn rates
rarity_spawn_counts = [
    ("⚪ Common", 5), 
    ("🟢 Medium", 3), 
    ("🟠 Rare", 2), 
    ("🟡 Legendary", 1)
]

# Special rarity spawn thresholds
cosmic_threshold = 5000
exclusive_threshold = 10000
limited_edition_threshold = 15000
seal_limit = 50

# Seal counts required for Cosmic and Exclusive
cosmic_seal_required = 200
exclusive_seal_required = 100

# Function to spawn a character
async def spawn_character(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)

    # Get chat total messages
    chat_data = await user_totals_collection.find_one({'chat_id': chat_id})
    total_messages = chat_data.get('total_messages', 0) if chat_data else 0

    # Determine rarity based on message count
    if total_messages >= limited_edition_threshold:
        rarity = "🔮 Limited Edition"
    elif total_messages >= exclusive_threshold:
        rarity = "💮 Exclusive"
    elif total_messages >= cosmic_threshold:
        rarity = "💠 Cosmic"
    else:
        rarity = random.choices(
            [r[0] for r in rarity_spawn_counts],
            [r[1] for r in rarity_spawn_counts]
        )[0]

    # Fetch a unique character for this rarity
    existing_characters = [char['id'] for char in last_characters.values()]
    character = await collection.find_one({'rarity': rarity, 'id': {'$nin': existing_characters}})

    if not character:
        await update.message.reply_text(f"⚠️ No new characters available for rarity {rarity}.")
        return

    # Store last spawned character
    last_characters[chat_id] = character

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"A {rarity} character appeared!\nUse /seal <name> to capture.",
        parse_mode='Markdown'
    )

# Function to seal (capture) character
async def seal(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # No character to seal
    if chat_id not in last_characters:
        await update.message.reply_text("❌ No character to seal! Wait for the next spawn.")
        return

    guess = ' '.join(context.args).lower() if context.args else ''
    character = last_characters[chat_id]
    correct_name = character['name'].lower()

    # Correct guess
    if correct_name == guess:
        # Check if user already owns the character
        user = await user_collection.find_one({'id': user_id})
        if user and any(char['id'] == character['id'] for char in user.get('characters', [])):
            await update.message.reply_text("❌ You already own this character!")
            return

        # Store the sealed character
        if user:
            await user_collection.update_one({'id': user_id}, {'$push': {'characters': character}})
        else:
            await user_collection.insert_one({'id': user_id, 'characters': [character]})

        # Increase total seals in chat
        total_seals[chat_id] = total_seals.get(chat_id, 0) + 1

        # Stop spawning if seal limit is reached
        if total_seals[chat_id] >= seal_limit:
            await update.message.reply_text("⚠️ Seal limit reached for this chat!")
            return

        await update.message.reply_text(f"✅ {character['name']} has been sealed and added to your collection!")
        
        # Remove character from spawn list
        del last_characters[chat_id]

    else:
        await update.message.reply_text("❌ Incorrect name! Try again.")

# Function to mark favorite character by ID
async def fav(update: Update, context: CallbackContext) -> None:
    """Marks a character as favorite using character ID."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /fav <character_id>")
        return

    character_id = context.args[0]
    user_data = await user_collection.find_one({'id': user_id})

    if not user_data or 'characters' not in user_data:
        await update.message.reply_text("❌ You have no characters to favorite.")
        return

    matched_character = next((char for char in user_data['characters'] if char['id'] == character_id), None)

    if not matched_character:
        await update.message.reply_text("❌ Character not found in your collection.")
        return

    await user_collection.update_one(
        {'id': user_id, 'characters.id': character_id}, 
        {'$set': {'characters.$.fav': True}}
    )

    await update.message.reply_text(f"⭐ {matched_character['name']} has been marked as your favorite!")

# Function to set custom spawn frequency
async def set_frequency(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = str(update.effective_chat.id)

    if user_id != 7717913705:
        await update.message.reply_text("❌ You don't have permission to set the frequency.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ Usage: /setfrequency <number>")
        return

    frequency = int(context.args[0])

    if frequency < 1:
        await update.message.reply_text("⚠️ Frequency must be at least 1 message.")
        return

    await user_totals_collection.update_one(
        {'chat_id': chat_id},
        {'$set': {'message_frequency': frequency}},
        upsert=True
    )

    await update.message.reply_text(f"✅ Spawn frequency set to {frequency} messages.")

# Register bot commands
application.add_handler(CommandHandler("fav", fav, block=False))
application.add_handler(CommandHandler("seal", seal, block=False))
application.add_handler(CommandHandler("setfrequency", set_frequency, block=False))
application.add_handler(MessageHandler(filters.ALL, spawn_character, block=False))

# Start bot
if __name__ == "__main__":
    Grabberu.start()
    LOGGER.info("Bot started")
    application.run_polling(drop_pending_updates=True)
    
