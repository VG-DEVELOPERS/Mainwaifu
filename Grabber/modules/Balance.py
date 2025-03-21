import asyncio
import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackContext, CommandHandler, MessageHandler, filters
from Grabber import application, user_collection, collection
from config import OWNER_ID, SUPPORT_ID  

# Globals
current_character = {}
streaks = {}
GUESS_TIME = 300  # 5 minutes
DAILY_REWARD_AMOUNT = 20

async def add_coins(user_id: int, amount: int):
    if amount > 0:
        await user_collection.update_one(
            {"id": user_id},
            {"$inc": {"balance": amount}, "$setOnInsert": {"balance": 0}},
            upsert=True
        )

async def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({"id": user_id}, {"balance": 1})
    balance_amount = user_data.get("balance", 0) if user_data else 0
    await update.message.reply_text(f"Your balance: 💵 {balance_amount} coins.")

async def pay(update: Update, context: CallbackContext):
    sender_id = update.effective_user.id
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to send coins!")
        return

    recipient_id = update.message.reply_to_message.from_user.id
    try:
        amount = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Invalid format. Use: /pay <amount>")
        return

    sender_data = await user_collection.find_one({"id": sender_id}, {"balance": 1})
    sender_balance = sender_data.get("balance", 0) if sender_data else 0

    if sender_balance < amount:
        await update.message.reply_text("Insufficient balance!")
        return

    await user_collection.update_one({"id": sender_id}, {"$inc": {"balance": -amount}})
    await user_collection.update_one({"id": recipient_id}, {"$inc": {"balance": amount}})
    await update.message.reply_text(f"✅ You paid {amount} coins to {update.message.reply_to_message.from_user.username}.")
    await balance(update, context)

async def daily_reward(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({"id": user_id}, {"last_daily_reward": 1, "balance": 1})
    
    last_claim = user_data.get("last_daily_reward") if user_data else None
    if last_claim and last_claim.date() == datetime.utcnow().date():
        await update.message.reply_text("You've already claimed today's reward!")
        return

    await user_collection.update_one(
        {"id": user_id}, 
        {"$inc": {"balance": DAILY_REWARD_AMOUNT}, "$set": {"last_daily_reward": datetime.utcnow()}}, 
        upsert=True
    )
    await update.message.reply_text(f"🎉 Daily reward claimed! You received {DAILY_REWARD_AMOUNT} coins.")

async def mtop(update: Update, context: CallbackContext):
    top_users = await user_collection.find({}, {"id": 1, "first_name": 1, "balance": 1}).sort("balance", -1).limit(10).to_list(10)
    
    message = "🏆 **Top 10 Richest Users** 🏆\n"
    for i, user in enumerate(top_users, start=1):
        first_name = user.get("first_name", "Unknown")
        user_id = user.get("id", "Unknown")
        balance = user.get("balance", 0)
        message += f"{i}. <a href='tg://user?id={user_id}'>{first_name}</a> - 💵 {balance} coins\n"

    photo_url = 'https://telegra.ph/file/8fce79d744297133b79b6.jpg'
    await update.message.reply_photo(photo=photo_url, caption=message, parse_mode='HTML')

async def nguess(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if chat_id != SUPPORT_ID or chat_id in current_character:
        return

    characters = await collection.aggregate([{"$sample": {"size": 1}}]).to_list(1)
    if not characters:
        await context.bot.send_message(chat_id, "No waifus found.")
        return

    character = characters[0]
    character_name = character['name'].strip().lower()
    current_character[chat_id] = {"character": character, "guessed": False}

    task = asyncio.create_task(send_timeout_message(context, chat_id, character_name))
    current_character[chat_id]["timeout"] = task

    await context.bot.send_photo(chat_id=chat_id, photo=character['img_url'], caption="✨ Guess this Waifu! 🧐✨")

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

            streaks[chat_id] = {"streak": streaks.get(chat_id, {}).get("streak", 0) + 1, "misses": 0}
            streak = streaks[chat_id]["streak"]

            await update.message.reply_text(f"🎉 Correct! You earned 20 coins! Streak: {streak} 🎉")
            data["guessed"] = True

            if "timeout" in data and not data["timeout"].done():
                data["timeout"].cancel()

            await context.bot.send_message(chat_id, f"✅ The waifu was **{character_name}**!")
            del current_character[chat_id]

            await asyncio.sleep(3)
            await nguess(update, context)

async def send_timeout_message(context: CallbackContext, chat_id: int, character_name: str):
    await asyncio.sleep(GUESS_TIME)
    if chat_id in current_character and not current_character[chat_id]["guessed"]:
        await context.bot.send_message(chat_id, f"⏳ Time's up! The waifu was **{character_name}**.")
        del current_character[chat_id]
        await asyncio.sleep(3)
        await nguess(context.bot, CallbackContext(context.bot))

application.add_handler(CommandHandler("balance", balance))
application.add_handler(CommandHandler("pay", pay))
application.add_handler(CommandHandler("dailyreward", daily_reward))
application.add_handler(CommandHandler("mtop", mtop))
application.add_handler(CommandHandler("nguess", nguess))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess))
