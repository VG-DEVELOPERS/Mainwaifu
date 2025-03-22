from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from itertools import groupby
import math
import random
from html import escape
from Grabber import collection, user_collection, application

async def harem(update: Update, context: CallbackContext, page=0) -> None:
    user_id = update.effective_user.id

    # Fetch user data from MongoDB
    user = await user_collection.find_one({'id': user_id})
    if not user or 'characters' not in user or not isinstance(user['characters'], list) or not user['characters']:
        if update.message:
            await update.message.reply_text('You have not guessed any characters yet!')
        else:
            await update.callback_query.edit_message_text('You have not guessed any characters yet!')
        return

    # Filter only valid characters (ensure they are dictionaries)
    characters = [c for c in user['characters'] if isinstance(c, dict) and 'id' in c and 'anime' in c and 'name' in c]

    if not characters:
        if update.message:
            await update.message.reply_text('Your character list is empty!')
        else:
            await update.callback_query.edit_message_text('Your character list is empty!')
        return

    # Sort characters by anime and character ID
    characters = sorted(characters, key=lambda x: (x['anime'], x['id']))

    # Group characters by ID and count occurrences
    character_counts = {k: len(list(v)) for k, v in groupby(characters, key=lambda x: x['id'])}

    # Remove duplicates (keeping the first occurrence)
    unique_characters = list({character['id']: character for character in characters}.values())

    # Set number of characters per page
    characters_per_page = 7
    total_pages = math.ceil(len(unique_characters) / characters_per_page)

    if page < 0 or page >= total_pages:
        page = 0

    # Harem header message
    harem_message = f"🐰 {escape(update.effective_user.first_name)} ┊ EMX ™'s Harem - Page {page+1}/{total_pages}\n\n"

    # Get characters for the current page
    current_characters = unique_characters[page * characters_per_page:(page + 1) * characters_per_page]

    # Group characters by anime and format the message
    grouped_characters = {k: list(v) for k, v in groupby(current_characters, key=lambda x: x['anime'])}

    for anime, characters in grouped_characters.items():
        harem_message += f"🎬 {anime} {len(characters)}/{await collection.count_documents({'anime': anime})}\n"
        harem_message += "━━━━━━━━━━━━━━━━━\n"

        for character in characters:
            count = character_counts[character['id']]
            rarity = character.get("rarity", "Unknown")  # Show "Unknown" if rarity is missing
            harem_message += f"🌟 {character['id']} [{rarity}] {character['name']} ×{count}\n"
            harem_message += "━━━━━━━━━━━━━━━━━\n"

    # Total character count
    total_count = len(user['characters'])

    # Inline button for collection
    keyboard = [[InlineKeyboardButton(f"📜 See Collection ({total_count})", switch_inline_query_current_chat=f"collection.{user_id}")]]
    
    # Pagination buttons
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"harem:{page-1}:{user_id}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"harem:{page+1}:{user_id}"))
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Select a favorite character or random character to display as the image
    favorite_character = None
    if 'favorites' in user and user['favorites']:
        favorite_character = next((c for c in characters if c['id'] == user['favorites'][0]), None)

    if not favorite_character:
        favorite_character = random.choice(characters) if characters else None

    # Send image + message in one response
    if favorite_character and 'img_url' in favorite_character:
        if update.message:
            await update.message.reply_photo(
                photo=favorite_character['img_url'],
                caption=harem_message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            if update.callback_query.message.caption != harem_message:
                await update.callback_query.edit_message_caption(
                    caption=harem_message,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
    else:
        if update.message:
            await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
        else:
            if update.callback_query.message.text != harem_message:
                await update.callback_query.edit_message_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)

async def harem_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data

    # Extract page and user_id from the callback data
    _, page, user_id = data.split(':')

    page = int(page)
    user_id = int(user_id)

    # Ensure only the owner can view their own harem
    if query.from_user.id != user_id:
        await query.answer("⚠️ You can't view someone else's Harem!", show_alert=True)
        return

    # Call harem function with the selected page
    await harem(update, context, page)

# Add handlers
application.add_handler(CommandHandler(["harem", "collection"], harem, block=False))
application.add_handler(CallbackQueryHandler(harem_callback, pattern='^harem', block=False))
