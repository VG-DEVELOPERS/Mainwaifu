import html
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from Grabber import application, user_collection


async def harem(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.first_name  # Get actual username
    user_data = await user_collection.find_one({"id": user_id})

    if not user_data or "characters" not in user_data or not user_data["characters"]:
        await update.message.reply_text("Your harem is empty! Use /guess to collect waifus.")
        return

    characters = user_data["characters"]
    favorite_character_id = user_data.get("fav_character")  # Get favorite character if exists

    per_page = 5  
    page = int(context.args[0]) if context.args and context.args[0].isdigit() else 0
    total_pages = (len(characters) + per_page - 1) // per_page  

    rarity_map = {
        "⚪": "Common",
        "🟠": "Rare",
        "🟡": "Legendary",
        "🟢": "Medium",
        "💠": "Cosmic",
        "💮": "Exclusive",
        "🔮": "Limited Edition",
    }

    # Select favorite character or random one if none is set
    if favorite_character_id:
        fav_character = next((c for c in characters if c.get("id") == favorite_character_id), None)
    else:
        fav_character = random.choice(characters) if characters else None

    harem_message = f"{username}'s Recent Waifus - Page: {page+1}/{total_pages}\n\n"

    # Show favorite character (or random one if no favorite)
    if fav_character:
        char_id = fav_character.get("id", "Unknown")
        name = fav_character.get("name", "Unknown")
        anime = fav_character.get("anime", "Unknown")
        rarity = fav_character.get("rarity", "Unknown")
        harem_message += (
            f"⭐ **Favorite Character:**\n"
            f"☘️ Name: {name} (ID: 🎭 {char_id})\n"
            f"{rarity} Rarity: {rarity_map.get(rarity, 'Unknown')}\n"
            f"⚜️ Anime: {anime} (1/{len(characters)})\n\n"
        )

    # Display the current page of characters
    characters_on_page = characters[page * per_page : (page + 1) * per_page]
    for char in characters_on_page:
        if char == fav_character:  # Skip if already displayed as favorite
            continue

        char_id = char.get("id", "Unknown")
        name = char.get("name", "Unknown")
        anime = char.get("anime", "Unknown")
        rarity = char.get("rarity", "Unknown")

        harem_message += (
            f"☘️ Name: {name} (ID: 🎭 {char_id})\n"
            f"{rarity} Rarity: {rarity_map.get(rarity, 'Unknown')}\n"
            f"⚜️ Anime: {anime} (1/{len(characters)})\n\n"
        )

    # Pagination buttons
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⏮ Previous", callback_data=f"harem_{page-1}"))
    if page + 1 < total_pages:
        buttons.append(InlineKeyboardButton("⏭ Next", callback_data=f"harem_{page+1}"))

    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None

    await update.message.reply_text(harem_message, reply_markup=keyboard, parse_mode="Markdown")


async def harem_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.first_name
    user_data = await user_collection.find_one({"id": user_id})

    if not user_data or "characters" not in user_data or not user_data["characters"]:
        await query.answer("Your harem is empty!")
        return

    characters = user_data["characters"]
    favorite_character_id = user_data.get("fav_character")
    page = int(query.data.split("_")[1]) if query.data else 0
    per_page = 5  
    total_pages = (len(characters) + per_page - 1) // per_page  

    rarity_map = {
        "⚪": "Common",
        "🟠": "Rare",
        "🟡": "Legendary",
        "🟢": "Medium",
        "💠": "Cosmic",
        "💮": "Exclusive",
        "🔮": "Limited Edition",
    }

    # Select favorite character or random one
    if favorite_character_id:
        fav_character = next((c for c in characters if c.get("id") == favorite_character_id), None)
    else:
        fav_character = random.choice(characters) if characters else None

    harem_message = f"{username}'s Recent Waifus - Page: {page+1}/{total_pages}\n\n"

    if fav_character:
        char_id = fav_character.get("id", "Unknown")
        name = fav_character.get("name", "Unknown")
        anime = fav_character.get("anime", "Unknown")
        rarity = fav_character.get("rarity", "Unknown")
        harem_message += (
            f"⭐ **Favorite Character:**\n"
            f"☘️ Name: {name} (ID: 🎭 {char_id})\n"
            f"{rarity} Rarity: {rarity_map.get(rarity, 'Unknown')}\n"
            f"⚜️ Anime: {anime} (1/{len(characters)})\n\n"
        )

    # Display characters on the current page
    characters_on_page = characters[page * per_page : (page + 1) * per_page]
    for char in characters_on_page:
        if char == fav_character:
            continue

        char_id = char.get("id", "Unknown")
        name = char.get("name", "Unknown")
        anime = char.get("anime", "Unknown")
        rarity = char.get("rarity", "Unknown")

        harem_message += (
            f"☘️ Name: {name} (ID: 🎭 {char_id})\n"
            f"{rarity} Rarity: {rarity_map.get(rarity, 'Unknown')}\n"
            f"⚜️ Anime: {anime} (1/{len(characters)})\n\n"
        )

    # Pagination buttons
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⏮ Previous", callback_data=f"harem_{page-1}"))
    if page + 1 < total_pages:
        buttons.append(InlineKeyboardButton("⏭ Next", callback_data=f"harem_{page+1}"))

    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None

    await query.message.edit_text(harem_message, reply_markup=keyboard, parse_mode="Markdown")
    await query.answer()


# Register command and callback handler
application.add_handler(CommandHandler("harem", harem, block=False))
application.add_handler(CallbackQueryHandler(harem_callback, pattern="^harem_"))
        
