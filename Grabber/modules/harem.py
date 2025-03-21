from telegram import Update
from itertools import groupby
import math
from html import escape 
import random
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from Grabber import collection, user_collection, application

async def harem(update: Update, context: CallbackContext, page=0) -> None:
    user_id = update.effective_user.id

    # Retrieve user data
    user = await user_collection.find_one({'id': user_id})
    if not user:
        # If no characters guessed, notify the user
        if update.message:
            await update.message.reply_text('You Have Not Guessed any Characters Yet..')
        else:
            await update.callback_query.edit_message_text('You Have Not Guessed any Characters Yet..')
        return

    # Sort characters by anime and character ID
    characters = sorted(user['characters'], key=lambda x: (x['anime'], x['id']))

    # Group characters by ID and count occurrences
    character_counts = {k: len(list(v)) for k, v in groupby(characters, key=lambda x: x['id'])}

    # Remove duplicate characters by ID
    unique_characters = list({character['id']: character for character in characters}.values())

    # Adjusted page size to 7 characters per page
    characters_per_page = 7

    # Calculate the total number of pages for pagination
    total_pages = math.ceil(len(unique_characters) / characters_per_page)

    if page < 0 or page >= total_pages:
        page = 0

    # Create the harem message header
    harem_message = f"{escape(update.effective_user.first_name)} ┊𝗘 𝗠 𝗫 ™ 🐰's Harem - Page {page+1}/{total_pages}\n\n"

    # Get the characters to display on the current page
    current_characters = unique_characters[page*characters_per_page:(page+1)*characters_per_page]

    # Group characters by anime and format the message
    current_grouped_characters = {k: list(v) for k, v in groupby(current_characters, key=lambda x: x['anime'])}

    for anime, characters in current_grouped_characters.items():
        # Use anime name or "Unknown Series" if not provided
        harem_message += f"𖤍 {anime if anime else 'Unknown Series'} {len(characters)}/{await collection.count_documents({'anime': anime})}\n"
        harem_message += "⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋\n"

        # Display each character with their ID, name, and rarity (if provided)
        for character in characters:
            count = character_counts[character['id']]
            rarity = character.get("rarity")  # No default, rarity is shown only if provided
            rarity_display = f" [{rarity}]" if rarity else ""
            harem_message += f"𒄬 {character['id']}{rarity_display} {character['name']} ×{count}\n"
            harem_message += "⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋\n"

    # Total character count
    total_count = len(user['characters'])

    # Inline keyboard button to view the collection
    keyboard = [[InlineKeyboardButton(f"See Collection ({total_count})", switch_inline_query_current_chat=f"collection.{user_id}")]]
    
    # Pagination buttons
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"harem:{page-1}:{user_id}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"harem:{page+1}:{user_id}"))
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Show favorite character's image if available, otherwise display a random character's image or text
    if 'favorites' in user and user['favorites']:
        fav_character_id = user['favorites'][0]
        fav_character = next((c for c in user['characters'] if c['id'] == fav_character_id), None)

        if fav_character and 'img_url' in fav_character:
            if update.message:
                await update.message.reply_photo(photo=fav_character['img_url'], parse_mode='HTML', caption=harem_message, reply_markup=reply_markup)
            else:
                if update.callback_query.message.caption != harem_message:
                    await update.callback_query.edit_message_caption(caption=harem_message, reply_markup=reply_markup, parse_mode='HTML')
        else:
            if update.message:
                await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
            else:
                if update.callback_query.message.text != harem_message:
                    await update.callback_query.edit_message_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
    else:
        if user['characters']:
            random_character = random.choice(user['characters'])

            if 'img_url' in random_character:
                if update.message:
                    await update.message.reply_photo(photo=random_character['img_url'], parse_mode='HTML', caption=harem_message, reply_markup=reply_markup)
                else:
                    if update.callback_query.message.caption != harem_message:
                        await update.callback_query.edit_message_caption(caption=harem_message, reply_markup=reply_markup, parse_mode='HTML')
            else:
                if update.message:
                    await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
                else:
                    if update.callback_query.message.text != harem_message:
                        await update.callback_query.edit_message_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
        else:
            if update.message:
                await update.message.reply_text("Your List is Empty :)")

async def harem_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data

    # Extract page and user_id from the callback data
    _, page, user_id = data.split(':')

    page = int(page)
    user_id = int(user_id)

    # Ensure the user viewing the harem is the owner
    if query.from_user.id != user_id:
        await query.answer("It's not your Harem", show_alert=True)
        return

    # Call the harem function with the current page
    await harem(update, context, page)

# Add handlers
application.add_handler(CommandHandler(["harem", "collection"], harem, block=False))
harem_handler = CallbackQueryHandler(harem_callback, pattern='^harem', block=False)
application.add_handler(harem_handler)
