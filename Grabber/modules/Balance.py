import asyncio
import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
from pymongo import MongoClient

from Grabber import user_collection, collection, application

current_character = {}
streaks = {}
SUPPORT_ID = -1002528887253  # Replace with your support group ID
OWNER_ID = 7717913705
async def add_coins(user_id: int, amount: int):
    if amount <= 0:
        return
    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": amount}, "$setOnInsert": {"balance": 0}},
        upsert=True
    )

async def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({'id': user_id}, projection={'balance': 1})
    balance_amount = user_data.get('balance', 0) if user_data else 0
    await update.message.reply_text(f"Your balance: 💵 {balance_amount} coins.")

async def pay(update: Update, context: CallbackContext):
    sender_id = update.effective_user.id
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user and use `/pay <amount>`.")
        return
    recipient_id = update.message.reply_to_message.from_user.id
    try:
        amount = int(context.args[0])
        if amount <= 0:
            raise ValueError
    except (IndexError, ValueError):
        await update.message.reply_text("Invalid amount. Usage: /pay <amount>")
        return
    sender_data = await user_collection.find_one({'id': sender_id}, projection={'balance': 1})
    if not sender_data or sender_data.get('balance', 0) < amount:
        await update.message.reply_text("Insufficient balance.")
        return
    await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}})
    await user_collection.update_one({'id': recipient_id}, {'$inc': {'balance': amount}})
    updated_balance = await user_collection.find_one({'id': sender_id}, projection={'balance': 1})
    await update.message.reply_text(f"✅ You paid {amount} coins to {update.message.reply_to_message.from_user.username}. "
                                    f"New balance: 💵 {updated_balance.get('balance', 0)} coins.")

async def mtop(update: Update, context: CallbackContext):
    top_users = await user_collection.find({}, projection={'id': 1, 'first_name': 1, 'balance': 1}) \
                                    .sort('balance', -1).limit(10).to_list(10)
    message = "🏆 **Top 10 Users** 🏆\n\n"
    for i, user in enumerate(top_users, 1):
        name = user.get('first_name', 'Unknown')
        message += f"{i}. {name} - 💵 {user.get('balance', 0)} coins\n"
    await update.message.reply_text(message)

async def daily_reward(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({'id': user_id}, projection={'last_daily_reward': 1, 'balance': 1})
    last_claimed = user_data.get('last_daily_reward') if user_data else None
    if last_claimed and last_claimed.date() == datetime.utcnow().date():
        await update.message.reply_text("You've already claimed your daily reward today! 🎁")
        return
    await user_collection.update_one({'id': user_id}, {'$inc': {'balance': 20}, '$set': {'last_daily_reward': datetime.utcnow()}}, upsert=True)
    await update.message.reply_text("🎉 You claimed your daily reward of 20 coins!")

async def nguess(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if chat_id != SUPPORT_ID:
        return
    if chat_id in current_character:
        await update.message.reply_text("A waifu is already active!")
        return
    characters = await collection.aggregate([{"$sample": {"size": 1}}]).to_list(1)
    if not characters:
        await update.message.reply_text("No waifus found in the database.")
        return
    character = characters[0]
    character_name = character['name'].strip().lower()
    current_character[chat_id] = {"character": character, "guessed": False}

    await update.message.reply_photo(photo=character['img_url'], caption="✨ Guess this Waifu! 🧐✨")

    # Start a background task for timeout
    context.job_queue.run_once(send_timeout_message, when=300, data={"chat_id": chat_id, "character_name": character_name})

async def handle_guess(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    guess = update.message.text.strip().lower()
    if chat_id in current_character:
        data = current_character[chat_id]
        character = data["character"]
        character_name = character['name'].strip().lower()
        if not data["guessed"] and guess == character_name:
            await add_coins(user_id, 20)
            streaks[chat_id] = streaks.get(chat_id, {"streak": 0, "misses": 0})
            streaks[chat_id]["streak"] += 1
            streaks[chat_id]["misses"] = 0
            streak = streaks[chat_id]["streak"]
            await update.message.reply_text(f"🎉 Correct! You earned 20 coins! Streak: {streak} 🔥")
            del current_character[chat_id]
            await nguess(update, context)  # Automatically start a new waifu round

async def send_timeout_message(context: CallbackContext):
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    character_name = job_data["character_name"]
    if chat_id in current_character and not current_character[chat_id]["guessed"]:
        await context.bot.send_message(chat_id, f"⏳ Time's up! The correct answer was **{character_name}**.")
        del current_character[chat_id]

application.add_handler(CommandHandler("balance", balance))
application.add_handler(CommandHandler("pay", pay))
application.add_handler(CommandHandler("mtop", mtop))
application.add_handler(CommandHandler("dailyreward", daily_reward))
application.add_handler(CommandHandler("nguess", nguess))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess))
