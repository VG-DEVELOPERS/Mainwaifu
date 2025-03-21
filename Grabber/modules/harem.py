import random
import math
import re
from html import escape
from itertools import groupby
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from Sanatan import user_collection, collection, LOGGER, app
from Sanatan.rarity import harem_mode_mapping

async def generate_harem_content(client: Client, user_id: int, page: int = 0):
    try:
        tg_user = await client.get_users(user_id)
        first_name = escape(tg_user.first_name)
    except Exception as e:
        LOGGER.error(f"Error fetching user {user_id}: {e}")
        first_name = "User"

    user = await user_collection.find_one({'id': user_id})
    if not user:
        return f"{first_name}, you need to register first by starting the bot.", None, None

    characters = user.get('characters', [])
    fav_character_id = user.get('favorites', [])[0] if user.get('favorites') else None
    fav_character = None

    if fav_character_id:
        for c in characters:
            if isinstance(c, dict) and c.get('id') == fav_character_id:
                fav_character = c
                break

    hmode = user.get('hhmode', 'default')
    if hmode in ["default", None]:
        characters = [char for char in characters if isinstance(char, dict)]
        characters = sorted(characters, key=lambda x: (x.get('anime', ''), x.get('id', '')))
        rarity_value = "all"
    else:
        rarity_value = harem_mode_mapping.get(hmode, "Unknown Rarity")
        characters = [
            char for char in characters if isinstance(char, dict) and char.get('rarity') == rarity_value
        ]
        characters = sorted(characters, key=lambda x: (x.get('anime', ''), x.get('id', '')))

    if not characters:
        return f"{first_name}, you don't have any ({rarity_value}) husbando. Please change it from /hhmode.", None, None

    # ✅ Fixing Image Sending Logic
    media_url = None
    if fav_character and isinstance(fav_character, dict):
        media_url = fav_character.get('imgurl') or fav_character.get('vidurl')
    else:
        characters_with_media = [
            char for char in characters if isinstance(char, dict) and ('imgurl' in char or 'vidurl' in char)
        ]
        if characters_with_media:
            random_character = random.choice(characters_with_media)
            media_url = random_character.get('imgurl') or random_character.get('vidurl')

    total_pages = math.ceil(len(characters) / 10)
    if page < 0 or page >= total_pages:
        page = 0

    harem_message = f"<b>{first_name}'s ({rarity_value}) Husbando's - Page {page + 1}/{total_pages}</b>\n"

    current_characters = characters[page * 10 : (page + 1) * 10]
    current_grouped_characters = {}
    for k, v in groupby(sorted(current_characters, key=lambda x: x.get('anime', 'Unknown')), key=lambda x: x.get('anime', 'Unknown')):
        current_grouped_characters[k] = list(v)

    included_characters = set()

    for anime, chars in current_grouped_characters.items():
        user_anime_count = len([char for char in user['characters'] if isinstance(char, dict) and char.get('anime') == anime])
        total_anime_count = await collection.count_documents({"anime": anime})
        harem_message += f'\n◆ <b>{anime} 〔{user_anime_count}/{total_anime_count}〕</b>\n'

        for char in chars:
            if char['id'] not in included_characters:
                count = chars.count(char)
                formatted_id = f"{int(char['id']):04d}"
                harem_message += f'➹ : <b>{char["id"]} ⌠ {char.get("rarity", "Unknown")[0]} ⌡ {char["name"]} ×{count}</b>\n'
                included_characters.add(char['id'])

    total_count = len(user['characters'])
    keyboard = [
        [InlineKeyboardButton(f"𝗵𝘂𝘀𝗯𝗮𝗻𝗱𝗼 ({total_count})", switch_inline_query_current_chat=f"collection.{user_id}")]
    ]

    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"harem:{page - 1}:{user_id}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"harem:{page + 1}:{user_id}"))
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    return harem_message, reply_markup, media_url

@app.on_message(filters.command("harem"))
async def harem_command(client: Client, message: Message):
    user_id = message.from_user.id
    harem_message, reply_markup, media_url = await generate_harem_content(client, user_id, 0)

    if not reply_markup:
        await message.reply_text(harem_message, parse_mode=ParseMode.HTML)
        return

    try:
        if media_url:
            if media_url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                await message.reply_photo(
                    photo=media_url,
                    caption=harem_message,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            elif media_url.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                await message.reply_video(
                    video=media_url,
                    caption=harem_message,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
        else:
            await message.reply_text(
                text=harem_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        LOGGER.error(f"Failed to send media: {e}")
        await message.reply_text(
            text=harem_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

@app.on_callback_query(filters.regex(r"^harem:(-?\d+):(\d+)$"))
async def harem_callback(client: Client, callback_query: CallbackQuery):
    match = re.match(r"^harem:(-?\d+):(\d+)$", callback_query.data)
    if not match:
        await callback_query.answer("Invalid callback data.")
        return

    page = int(match.group(1))
    user_id = int(match.group(2))

    if callback_query.from_user.id != user_id:
        await callback_query.answer("This isn't your harem!", show_alert=True)
        return

    harem_message, reply_markup, media_url = await generate_harem_content(client, user_id, page)

    if not reply_markup:
        await callback_query.message.edit_text(harem_message, parse_mode=ParseMode.HTML)
        await callback_query.answer()
        return

    try:
        if media_url:
            await callback_query.message.edit_caption(
                caption=harem_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        else:
            await callback_query.message.edit_text(
                text=harem_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        LOGGER.error(f"Failed to edit message: {e}")
        await callback_query.message.edit_text(
            text=harem_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

    await callback_query.answer()
        
