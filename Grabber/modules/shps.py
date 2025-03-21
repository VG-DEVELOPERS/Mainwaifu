import html
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext
from Grabber import application, user_collection

# Shop Items (You can add more characters)
SHOP_ITEMS = [
    {"name": "Tsubaki", "price": 500, "emoji": "🌸"},
    {"name": "Sakurako", "price": 700, "emoji": "🌺"},
    {"name": "Navia", "price": 900, "emoji": "🌟"},
    {"name": "Caspar", "price": 1200, "emoji": "🌀"},
]

async def shop(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({"id": user_id})

    if not user_data:
        await update.message.reply_text("❌ You are not registered! Start collecting characters first.")
        return

    balance = user_data.get("balance", 0)
    keyboard = [
        [InlineKeyboardButton(f"{item['emoji']} {item['name']} - {item['price']}💰", callback_data=f"buy_{item['name']}")]
        for item in SHOP_ITEMS
    ]

    await update.message.reply_text(
        f"🛍️ **Character Shop**\n\n💰 **Your Balance:** {balance} coins\nChoose a character to buy:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def buy_character(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    character_name = query.data.split("_")[1]

    user_data = await user_collection.find_one({"id": user_id})
    if not user_data:
        await query.answer("❌ You are not registered!", show_alert=True)
        return

    balance = user_data.get("balance", 0)
    owned_characters = user_data.get("characters", [])

    character = next((item for item in SHOP_ITEMS if item["name"] == character_name), None)
    if not character:
        await query.answer("❌ Character not found!", show_alert=True)
        return

    if character_name in owned_characters:
        await query.answer("✅ You already own this character!", show_alert=True)
        return

    price = character["price"]
    if balance < price:
        await query.answer("❌ Not enough coins!", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"confirm_{character_name}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    await query.message.edit_text(
        f"💰 **Price:** {price} coins\n🛒 **Character:** {character_name}\n\nConfirm purchase?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def confirm_purchase(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    character_name = query.data.split("_")[1]

    user_data = await user_collection.find_one({"id": user_id})
    if not user_data:
        await query.answer("❌ You are not registered!", show_alert=True)
        return

    balance = user_data.get("balance", 0)
    owned_characters = user_data.get("characters", [])

    character = next((item for item in SHOP_ITEMS if item["name"] == character_name), None)
    if not character:
        await query.answer("❌ Character not found!", show_alert=True)
        return

    if balance < character["price"]:
        await query.answer("❌ Not enough coins!", show_alert=True)
        return

    new_balance = balance - character["price"]
    owned_characters.append(character_name)

    # **Store character in user collection**
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"balance": new_balance}, "$push": {"characters": character_name}}
    )

    await query.message.edit_text(
        f"✅ **Purchase Successful!**\n🎉 You now own **{character_name}**!\n💰 **Remaining Balance:** {new_balance} coins",
        parse_mode="Markdown"
    )
    await query.answer()

async def cancel_purchase(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.message.edit_text("❌ Purchase cancelled.")
    await query.answer()

async def inventory(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({"id": user_id})

    if not user_data:
        await update.message.reply_text("❌ You are not registered! Start collecting characters first.")
        return

    owned_characters = user_data.get("characters", [])

    if not owned_characters:
        await update.message.reply_text("📦 Your inventory is empty! Buy characters in /shop.")
        return

    inventory_text = "🎒 **Your Characters:**\n\n" + "\n".join([f"✅ {name}" for name in owned_characters])
    await update.message.reply_text(inventory_text, parse_mode="Markdown")

# Register commands
application.add_handler(CommandHandler('shops', shop, block=False))
application.add_handler(CommandHandler('inventory', inventory, block=False))
application.add_handler(CallbackQueryHandler(buy_character, pattern="^buy_"))
application.add_handler(CallbackQueryHandler(confirm_purchase, pattern="^confirm_"))
application.add_handler(CallbackQueryHandler(cancel_purchase, pattern="^cancel$"))
  
