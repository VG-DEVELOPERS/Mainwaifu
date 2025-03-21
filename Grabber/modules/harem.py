import html
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler
from Grabber import application, user_collection


async def harem(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.first_name  
    user_data = await user_collection.find_one({"id": user_id})

    if not user_data or "characters" not in user_data or not user_data["characters"]:
        await update.message.reply_text("Your harem is empty! Use /guess to collect waifus.")
        return

    characters = user_data["characters"]
    favorite_character_id = user_data.get("fav_character")  

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

    # Select favorite character or random one if not set
    fav_character = None
    if favorite_character_id:
        fav_character = next((c for c in characters if isinstance(c, dict) and c.get("id") == favorite_character_id), None)

    if not fav_character:
        fav_character = random.choice([c for c in characters if isinstance(c, dict)])  # Pick a random character

    harem_message = f"**{username}'s Recent Waifus - Page: {page+1}/{total_pages}**\n\n"

    imgurl = None  # Store image URL separately
    if fav_character and isinstance(fav_character, dict):
        char_id = fav_character.get("id", "Unknown")
        name = fav_character.get("name", "Unknown")
        anime = fav_character.get("anime", "Unknown")
        rarity = fav_character.get("rarity", "Unknown")
        imgurl = fav_character.get("imgurl", None)  

        harem_message += (
            f"⭐ **Favorite Character (or Random):**\n"
            f"☘️ Name: {name} (ID: 🎭 {char_id})\n"
            f"{rarity} Rarity: {rarity_map.get(rarity, 'Unknown')}\n"
            f"⚜️ Anime: {anime} (1/{len(characters)})\n\n"
        )

    # Display the current page of characters
    characters_on_page = [c for c in characters[page * per_page : (page + 1) * per_page] if isinstance(c, dict)]
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

    # ✅ Send image **first** (if available)
    if imgurl:
        try:
            await update.message.reply_photo(photo=imgurl, caption=f"⭐ **{fav_character.get('name', 'Unknown')}** - Your Special Waifu!", parse_mode="Markdown")
        except Exception as e:
            print(f"Error sending image: {e}")  # Log error if image fails

    # ✅ Then send the harem message
    await update.message.reply_text(harem_message, reply_markup=keyboard, parse_mode="Markdown")


# Register command
application.add_handler(CommandHandler("harem", harem, block=False))
