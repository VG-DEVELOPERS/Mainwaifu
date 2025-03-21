from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from itertools import groupby
import math
import random
from html import escape
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from Grabber import user_collection, application


async def harem(update: Update, context: CallbackContext, page=0) -> None:
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user or 'characters' not in user or not user['characters']:
        message = "Your harem is empty! Guess characters to add them."
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.edit_message_text(message)
        return

    characters = user['characters']
    unique_characters = {char['id']: char for char in characters}.values()
    character_counts = {char['id']: characters.count(char) for char in characters}
    
    total_pages = math.ceil(len(unique_characters) / 15)
    page = max(0, min(page, total_pages - 1))

    harem_message = f"<b>{escape(update.effective_user.first_name)}'s Harem - Page {page+1}/{total_pages}</b>\n"
    current_characters = list(unique_characters)[page * 15:(page + 1) * 15]

    grouped_characters = {k: list(v) for k, v in groupby(sorted(current_characters, key=lambda x: x['anime']), key=lambda x: x['anime'])}

    for anime, chars in grouped_characters.items():
        total_anime_characters = sum(1 for c in characters if c.get('anime') == anime)
        harem_message += f'\n<b>{anime} {len(chars)}/{total_anime_characters}</b>\n'
        for char in chars:
            char_id = char['id']
            rarity = char.get('rarity', 'Unknown Rarity')
            count = character_counts.get(char_id, 1)
            harem_message += f'{char_id} ({rarity}) {char["name"]} ×{count}\n'

    total_count = len(user['characters'])
    keyboard = [[InlineKeyboardButton(f"See Collection ({total_count})", switch_inline_query_current_chat=f"collection.{user_id}")]]
    
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"harem:{page-1}:{user_id}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"harem:{page+1}:{user_id}"))
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    fav_character_id = user.get('favorites', [None])[0]
    fav_character = next((c for c in characters if c['id'] == fav_character_id), None)
    image_url = fav_character['img_url'] if fav_character and 'img_url' in fav_character else None

    if not image_url and characters:
        random_character = random.choice(characters)
        image_url = random_character.get('img_url')

    if image_url:
        if update.message:
            await update.message.reply_photo(photo=image_url, caption=harem_message, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_caption(caption=harem_message, reply_markup=reply_markup, parse_mode='HTML')
    else:
        if update.message:
            await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)


async def harem_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data
    _, page, user_id = data.split(':')
    page = int(page)
    user_id = int(user_id)

    if query.from_user.id != user_id:
        await query.answer("This is not your harem.", show_alert=True)
        return

    await harem(update, context, page)


application.add_handler(CommandHandler(["harem", "collection"], harem, block=False))
application.add_handler(CallbackQueryHandler(harem_callback, pattern='^harem', block=False))
