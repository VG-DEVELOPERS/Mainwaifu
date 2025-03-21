import random
import math
import html
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext
from Grabber import application, user_collection

async def harem(update: Update, context: CallbackContext, page=0) -> None:
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user or 'characters' not in user or not user['characters']:
        await update.message.reply_text("Your harem is empty! Buy characters from /shop or guess them.")
        return

    characters = user['characters']

    # Convert string-based characters into a uniform dictionary format
    cleaned_characters = []
    for char in characters:
        if isinstance(char, str):
            cleaned_characters.append({"id": char, "name": char, "anime": "Unknown", "rarity": "Common", "imgurl": None})
        else:
            cleaned_characters.append(char)

    unique_characters = {}
    character_counts = {}

    for char in cleaned_characters:
        char_id = char.get('id', str(random.randint(1000, 9999)))  # Generate an ID if missing
        unique_characters[char_id] = char
        character_counts[char_id] = character_counts.get(char_id, 0) + 1

    total_pages = math.ceil(len(unique_characters) / 15)
    page = max(0, min(page, total_pages - 1))

    harem_message = f"<b>{html.escape(update.effective_user.first_name)}'s Harem - Page {page+1}/{total_pages}</b>\n"
    current_characters = list(unique_characters.values())[page * 15:(page + 1) * 15]

    for char in current_characters:
        anime = char.get("anime", "Unknown Anime")
        rarity = char.get("rarity", "Unknown Rarity")
        count = character_counts.get(char["id"], 1)
        harem_message += f'\n<b>{anime}</b>\n{char["name"]} ({rarity}) ×{count}\n'

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

    # Find favorite character properly
    fav_character = next((c for c in cleaned_characters if isinstance(c, dict) and c.get('id') == fav_character_id), None)

    image_url = fav_character.get('imgurl') if fav_character else None

    if not image_url and cleaned_characters:
        random_character = random.choice(cleaned_characters)
        image_url = random_character.get('imgurl')

    if image_url:
        await update.message.reply_photo(photo=image_url, caption=harem_message, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)

application.add_handler(CommandHandler("harem", harem, block=False))
