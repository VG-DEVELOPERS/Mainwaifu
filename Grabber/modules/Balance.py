import asyncio
import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackContext, CommandHandler, MessageHandler, filters
from Grabber import application, user_collection, collection

last_guess_time = {}
current_character = {}
streaks = {}

async def add_coins(user_id: int, amount: int) -> None:
    if amount <= 0:
        return
    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": amount}, "$setOnInsert": {"balance": 0}},
        upsert=True
    )

async def spawn_character(chat_id: int, context: CallbackContext):
    characters = await collection.aggregate([{"$sample": {"size": 1}}]).to_list(1)
    
    if not characters:
        await context.bot.send_message(chat_id, "No characters available in the database.")
        return

    character = characters[0]
    character_name = character['name'].strip().lower()

    current_character[chat_id] = {
        "character": character,
        "guessed": False
    }

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption="✨🌟 Who is this Mysterious Character?? 🧐🌟✨"
    )

async def nguess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    current_time = datetime.utcnow()

    if chat_id in last_guess_time:
        elapsed_time = (current_time - last_guess_time[chat_id]).total_seconds()
        remaining_time = 300 - elapsed_time  

        if remaining_time > 0:
            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            await update.message.reply_text(f"⏳ Please wait {minutes}m {seconds}s before using /nguess again.")
            return

    last_guess_time[chat_id] = current_time  

    await spawn_character(chat_id, context)  

async def handle_guess(update: Update, context: CallbackContext) -> None:
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    guess = update.message.text.strip().lower()

    if chat_id in current_character:
        data = current_character[chat_id]
        character = data["character"]
        character_name = character['name'].strip().lower()

        if not data["guessed"] and guess == character_name:
            await add_coins(user_id, 20)

            if chat_id not in streaks:
                streaks[chat_id] = {"streak": 1, "misses": 0}
            else:
                streaks[chat_id]["streak"] += 1
                streaks[chat_id]["misses"] = 0  

            streak = streaks[chat_id]["streak"]

            await update.message.reply_text(f"🎉 Correct! You've earned 20 coins! Your current streak is {streak}! 🎉")
            data["guessed"] = True  

            reward_map = {30: 1000, 50: 1500, 100: 2000}
            if streak in reward_map:
                await add_coins(user_id, reward_map[streak])
                await update.message.reply_text(f"🎉 {streak}-streak! Earned {reward_map[streak]} coins! 🎉")

                if streak == 100:
                    streaks[chat_id]["streak"] = 0  

            await asyncio.sleep(2)
            await spawn_character(chat_id, context)

async def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_balance = await user_collection.find_one({'id': user_id}, projection={'balance': 1})

    if user_balance:
        balance_amount = user_balance.get('balance', 0)
        balance_message = f"Your current balance is: 💵{balance_amount} coins."
    else:
        balance_message = "Unable to retrieve your balance."

    await update.message.reply_text(balance_message)

async def pay(update: Update, context: CallbackContext):
    sender_id = update.effective_user.id

    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a message to use /pay.")
        return

    recipient_id = update.message.reply_to_message.from_user.id

    try:
        amount = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Invalid amount. Usage: /pay <amount>")
        return

    sender_balance = await user_collection.find_one({'id': sender_id}, projection={'balance': 1})
    if not sender_balance or sender_balance.get('balance', 0) < amount:
        await update.message.reply_text("Insufficient balance to make the payment.")
        return

    await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}})
    await user_collection.update_one({'id': recipient_id}, {'$inc': {'balance': amount}})

    updated_sender_balance = await user_collection.find_one({'id': sender_id}, projection={'balance': 1})

    await update.message.reply_text(f"💵 Payment successful! You paid {amount} coins to {update.message.reply_to_message.from_user.username}. "
                                    f"Your current balance is: 💵{updated_sender_balance.get('balance', 0)} coins.")

async def mtop(update: Update, context: CallbackContext):
    top_users = await user_collection.find({}, projection={'id': 1, 'first_name': 1, 'last_name': 1, 'balance': 1}).sort('balance', -1).limit(10).to_list(10)

    top_users_message = "Top 10 Users with Highest Balance:\n"
    for i, user in enumerate(top_users, start=1):
        first_name = user.get('first_name', 'Unknown')
        last_name = user.get('last_name', '')
        user_id = user.get('id', 'Unknown')
        full_name = f"{first_name} {last_name}" if last_name else first_name
        top_users_message += f"{i}. <a href='tg://user?id={user_id}'>{full_name}</a>, \n Balance: 💵{user.get('balance', 0)} coins\n\n"

    photo_path = 'https://telegra.ph/file/8fce79d744297133b79b6.jpg'
    await update.message.reply_photo(photo=photo_path, caption=top_users_message, parse_mode='HTML')

async def daily(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({'id': user_id}, projection={'last_daily_reward': 1, 'balance': 1})

    if user_data:
        last_claimed_date = user_data.get('last_daily_reward')

        if last_claimed_date and last_claimed_date.date() == datetime.utcnow().date():
            await update.message.reply_text("You've already claimed your daily reward today. Come back tomorrow!")
            return

    await user_collection.update_one(
        {'id': user_id},
        {'$inc': {'balance': 20}, '$set': {'last_daily_reward': datetime.utcnow()}}
    )

    await update.message.reply_text("Congratulations! You've claimed your daily reward of 20 coins.")

application.add_handler(CommandHandler("daily", daily, block=False))
application.add_handler(CommandHandler("balance", balance, block=False))
application.add_handler(CommandHandler("pay", pay, block=False))
application.add_handler(CommandHandler("mtop", mtop, block=False))
application.add_handler(CommandHandler("nguess", nguess, block=False))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess))
    
