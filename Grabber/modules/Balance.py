from telegram.ext import CommandHandler, MessageHandler
from Grabber import application, user_collection, collection
from telegram import Update
from telegram.ext import CallbackContext
from datetime import datetime
import asyncio

current_character = {}
streaks = {}

async def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({'id': user_id}, projection={'coins': 1})

    if user_data:
        coins = user_data.get('coins', 0)
        balance_message = f"Your current balance is: 💵{coins} coins."
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

    sender_data = await user_collection.find_one({'id': sender_id}, projection={'coins': 1})

    if not sender_data or sender_data.get('coins', 0) < amount:
        await update.message.reply_text("Insufficient balance to make the payment.")
        return

    await user_collection.update_one({'id': sender_id}, {'$inc': {'coins': -amount}})
    await user_collection.update_one({'id': recipient_id}, {'$inc': {'coins': amount}})

    updated_sender_data = await user_collection.find_one({'id': sender_id}, projection={'coins': 1})

    await update.message.reply_text(f"💵 Payment successful! You paid {amount} coins to {update.message.reply_to_message.from_user.username}. "
                                    f"Your current balance is: 💵{updated_sender_data.get('coins', 0)} coins.")

async def mtop(update: Update, context: CallbackContext):
    top_users = await user_collection.find({}, projection={'id': 1, 'first_name': 1, 'last_name': 1, 'coins': 1}).sort('coins', -1).limit(10).to_list(10)

    top_users_message = "🏆 Top 10 Users with Highest Coins 🏆\n"
    for i, user in enumerate(top_users, start=1):
        first_name = user.get('first_name', 'Unknown')
        last_name = user.get('last_name', '')
        user_id = user.get('id', 'Unknown')
        full_name = f"{first_name} {last_name}" if last_name else first_name

        top_users_message += f"{i}. <a href='tg://user?id={user_id}'>{full_name}</a>, Coins: 💵{user.get('coins', 0)}\n\n"

    photo_path = 'https://telegra.ph/file/8fce79d744297133b79b6.jpg'
    await update.message.reply_photo(photo=photo_path, caption=top_users_message, parse_mode='HTML')

async def daily(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({'id': user_id}, projection={'last_daily_reward': 1, 'coins': 1})

    if user_data:
        last_claimed = user_data.get('last_daily_reward')

        if last_claimed and last_claimed.date() == datetime.utcnow().date():
            await update.message.reply_text("You've already claimed your daily reward today. Come back tomorrow!")
            return

    await user_collection.update_one(
        {'id': user_id},
        {'$inc': {'coins': 20}, '$set': {'last_daily_reward': datetime.utcnow()}}
    )

    await update.message.reply_text("🎉 Congratulations! You've claimed your daily reward of 20 coins! 🎉")

async def nguess(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if chat_id in current_character:
        await context.bot.send_message(chat_id, "A guess is already in progress.")
        return

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

    task = asyncio.create_task(send_timeout_message(context, chat_id, character_name, 15))
    current_character[chat_id]["timeout"] = task

    await context.bot.send_photo(chat_id=chat_id, photo=character['img_url'], caption="✨🌟 Who is this Mysterious Character?? 🧐🌟✨")

async def handle_guess(update: Update, context: CallbackContext):
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
            await user_collection.update_one({"id": user_id}, {"$inc": {"coins": 20}}, upsert=True)

            if chat_id not in streaks:
                streaks[chat_id] = {"streak": 1, "misses": 0}
            else:
                streaks[chat_id]["streak"] += 1
                streaks[chat_id]["misses"] = 0  

            streak = streaks[chat_id]["streak"]

            await update.message.reply_text(f"🎉 Correct! You've earned 20 coins! Your current streak is {streak}! 🎉")
            data["guessed"] = True  

            if "timeout" in data and not data["timeout"].done():
                data["timeout"].cancel()

            reward_map = {30: 1000, 50: 1500, 100: 2000}
            if streak in reward_map:
                await user_collection.update_one({"id": user_id}, {"$inc": {"coins": reward_map[streak]}})
                await update.message.reply_text(f"🎉 {streak}-streak! Earned {reward_map[streak]} coins! 🎉")

                if streak == 100:
                    streaks[chat_id]["streak"] = 0  

            del current_character[chat_id]  

async def send_timeout_message(context: CallbackContext, chat_id: int, character_name: str, timeout: int):
    await asyncio.sleep(timeout)

    if chat_id in current_character and not current_character[chat_id]["guessed"]:
        await context.bot.send_message(chat_id, f"⏳ Time's up! The character was {character_name}.")
        del current_character[chat_id]

application.add_handler(CommandHandler("daily", daily, block=False))
application.add_handler(CommandHandler("balance", balance, block=False))
application.add_handler(CommandHandler("pay", pay, block=False))
application.add_handler(CommandHandler("mtop", mtop, block=False))
application.add_handler(CommandHandler("nguess", nguess, block=False))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess))
