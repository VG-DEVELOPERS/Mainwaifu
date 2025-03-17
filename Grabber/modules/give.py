from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from Grabber import application, user_collection

# Define the special admin user who can give unlimited balance
UNLIMITED_USER_ID = 7717913705  

async def give_balance(update: Update, context: CallbackContext):
    sender_id = update.effective_user.id

    # Check if the command was a reply
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to a user to give balance.")
        return

    # Extract recipient's user ID
    recipient_id = update.message.reply_to_message.from_user.id

    # Parse the amount from the command
    try:
        amount = int(context.args[0])
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Invalid amount. Usage: `/givebalance <amount>` (Reply to user)", parse_mode="Markdown")
        return

    # If sender is the unlimited user, skip balance check
    if sender_id == UNLIMITED_USER_ID:
        await user_collection.update_one({'id': recipient_id}, {'$inc': {'balance': amount}})
        await update.message.reply_text(f"✅ {amount} coins given to {update.message.reply_to_message.from_user.username or 'the user'}!")
        return

    # Check sender's balance
    sender = await user_collection.find_one({'id': sender_id}, projection={'balance': 1})
    sender_balance = sender.get("balance", 0) if sender else 0

    if sender_balance < amount:
        await update.message.reply_text("❌ Insufficient balance to give.")
        return

    # Update balances
    await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}})
    await user_collection.update_one({'id': recipient_id}, {'$inc': {'balance': amount}})

    # Confirm transaction
    await update.message.reply_text(f"✅ You gave {amount} coins to {update.message.reply_to_message.from_user.username or 'the user'}!")

# Register command
application.add_handler(CommandHandler("givebalance", give_balance))
