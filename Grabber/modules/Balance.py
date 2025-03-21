import random
from Grabber import application, user_collection  
from telegram.ext import CommandHandler
from telegram import Update
from telegram.ext import CallbackContext
from datetime import datetime

async def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_balance = await user_collection.find_one({'id': user_id}, projection={'balance': 1})
    balance_amount = user_balance.get('balance', 0) if user_balance else 0
    await update.message.reply_text(f"Your current balance is: 💵 {balance_amount} coins.")

async def pay(update: Update, context: CallbackContext):
    sender_id = update.effective_user.id

    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a message to use /pay.")
        return

    recipient_id = update.message.reply_to_message.from_user.id

    try:
        amount = int(context.args[0])
        if amount <= 0:
            raise ValueError
    except (IndexError, ValueError):
        await update.message.reply_text("Invalid amount. Usage: /pay <amount>")
        return

    sender = await user_collection.find_one({'id': sender_id}, projection={'balance': 1})
    if not sender or sender.get('balance', 0) < amount:
        await update.message.reply_text("Insufficient balance to make the payment.")
        return

    async with user_collection.database.client.start_session() as session:
        async with session.start_transaction():
            await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}}, session=session)
            await user_collection.update_one({'id': recipient_id}, {'$inc': {'balance': amount}}, session=session)

    updated_sender_balance = await user_collection.find_one({'id': sender_id}, projection={'balance': 1})
    await update.message.reply_text(
        f"💵 Payment successful! You paid {amount} coins to {update.message.reply_to_message.from_user.username}. "
        f"Your current balance is: 💵 {updated_sender_balance.get('balance', 0)} coins."
    )

async def daily_reward(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({'id': user_id}, projection={'last_daily_reward': 1, 'balance': 1})

    if user_data and user_data.get('last_daily_reward'):
        last_claimed_date = user_data['last_daily_reward']
        if last_claimed_date.replace(tzinfo=None).date() == datetime.utcnow().date():
            await update.message.reply_text("You've already claimed your daily reward today. Come back tomorrow!")
            return

    await user_collection.update_one(
        {'id': user_id},
        {'$inc': {'balance': 20}, '$set': {'last_daily_reward': datetime.utcnow()}},
        upsert=True
    )
    await update.message.reply_text("🎉 Congratulations! You've claimed your daily reward of 20 coins.")

async def mtop(update: Update, context: CallbackContext):
    top_users = await user_collection.find({}, projection={'id': 1, 'first_name': 1, 'last_name': 1, 'balance': 1}) \
                                     .sort('balance', -1).limit(10).to_list(length=10)

    if not top_users:
        await update.message.reply_text("No users found with balances.")
        return

    top_users_message = "🏆 **Top 10 Users with Highest Balance:**\n\n"
    for i, user in enumerate(top_users, start=1):
        first_name = user.get('first_name', 'Unknown')
        last_name = user.get('last_name', '')
        user_id = user.get('id', 'Unknown')
        full_name = f"{first_name} {last_name}".strip()
        top_users_message += f"{i}. <a href='tg://user?id={user_id}'>{full_name}</a> — 💵 {user.get('balance', 0)} coins\n"

    photo_path = 'https://telegra.ph/file/8fce79d744297133b79b6.jpg'
    await update.message.reply_photo(photo=photo_path, caption=top_users_message, parse_mode='HTML')

async def nguess(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    try:
        guess = int(context.args[0])
        if guess < 1 or guess > 10:
            raise ValueError
    except (IndexError, ValueError):
        await update.message.reply_text("Invalid input! Usage: /nguess <number between 1-10>")
        return

    correct_number = random.randint(1, 10)

    if guess == correct_number:
        reward = random.randint(5, 20)
        await user_collection.update_one({'id': user_id}, {'$inc': {'balance': reward}}, upsert=True)
        await update.message.reply_text(f"🎉 Congratulations! You guessed correctly ({correct_number}) and won {reward} coins!")
    else:
        await update.message.reply_text(f"❌ Wrong guess! The correct number was {correct_number}. Try again!")

application.add_handler(CommandHandler("balance", balance))
application.add_handler(CommandHandler("pay", pay))
application.add_handler(CommandHandler("daily", daily_reward))
application.add_handler(CommandHandler("mtop", mtop))
application.add_handler(CommandHandler("nguess", nguess))
        
