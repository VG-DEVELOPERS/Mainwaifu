from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from html import escape

from Grabber import collection, application

async def search_character(update: Update, context: CallbackContext):
    # Get the name to search for from the command arguments
    name_to_search = " ".join(context.args).strip()

    if not name_to_search:
        await update.message.reply_text("Please provide a name to search for.")
        return

    # Search for characters by name in the total collection
    characters_cursor = collection.find({"name": {"$regex": f".*{name_to_search}.*", "$options": "i"}})

    found_characters = []
    async for character in characters_cursor:
        found_characters.append(character)

    if not found_characters:
        await update.message.reply_text("No characters found with that name.")
        return

    # Prepare the response message with found characters
    response_message = "<b>Found Characters:</b>\n"
    for character in found_characters:
        response_message += f"ID: {character['id']}\n"
        response_message += f"Name: {escape(character['name'])}\n"
        response_message += f"Rarity: {escape(character['rarity'])}\n\n"

    await update.message.reply_text(response_message, parse_mode='HTML')

async def search_anime(update: Update, context: CallbackContext):
    # Get the anime title to search for from the command arguments
    anime_title = " ".join(context.args).strip()

    if not anime_title:
        await update.message.reply_text("Please provide an anime title to search for.")
        return

    # Search for characters by anime title in the total collection
    characters_cursor = collection.find({"anime": {"$regex": f".*{anime_title}.*", "$options": "i"}})

    found_characters = []
    async for character in characters_cursor:
        found_characters.append(character)

    if not found_characters:
        await update.message.reply_text(f"No characters found from anime titled '{anime_title}'.")
        return

    # Prepare the response message with found characters
    response_message = f"<b>Characters from Anime '{escape(anime_title)}':</b>\n"
    for character in found_characters:
        response_message += f"ID: {character['id']}\n"
        response_message += f"Name: {escape(character['name'])}\n"
        response_message += f"Rarity: {escape(character['rarity'])}\n\n"

    await update.message.reply_text(response_message, parse_mode='HTML')

# Add handlers for the /sips and /sani commands
application.add_handler(CommandHandler("sips", search_character))
application.add_handler(CommandHandler("sani", search_anime))
