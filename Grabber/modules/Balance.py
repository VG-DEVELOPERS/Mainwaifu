import asyncio
import random
from datetime import datetime
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, CallbackContext
from pymongo import MongoClient

from Grabber import user_collection, collection, application

SUPPORT_GROUP_ID = -1002528887253  # Replace with your support group ID
OWNER_ID = 7717913705  # Replace with your actual group ID
current_characters = {}  # Stores waifu per group
current_character = {}  # Stores active waifu guesses for each chat

async def add_coins(user_id: int, amount: int):
    if amount <= 0:
        return

    user_data = await user_collection.find_one({"id": user_id}, projection={"balance": 1})

    if user_data:
        await user_collection.update_one({"id": user_id}, {"$inc": {"balance": amount}})
    else:
        await user_collection.insert_one({"id": user_id, "balance": amount})

async def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({'id': user_id}, projection={'balance': 1})
    balance_amount = user_data.get('balance', 0) if user_data else 0
    await update.message.reply_text(f"Your balance: 💵 {balance_amount} coins.")

async def pay(update: Update, context: CallbackContext):
    sender_id = update.effective_user.id

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to use /pay.")
        return

    recipient_id = update.message.reply_to_message.from_user.id
    try:
        amount = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Invalid amount. Usage: /pay <amount>")
        return

    sender_balance = await user_collection.find_one({'id': sender_id}, projection={'balance': 1})
    if not sender_balance or sender_balance.get('balance', 0) < amount:
        await update.message.reply_text("Insufficient balance.")
        return

    await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}})
    await user_collection.update_one({'id': recipient_id}, {'$inc': {'balance': amount}})

    updated_sender_balance = await user_collection.find_one({'id': sender_id}, projection={'balance': 1})
    await update.message.reply_text(
        f"💵 Payment successful! You paid {amount} coins to {update.message.reply_to_message.from_user.username}. "
        f"Your balance: 💵 {updated_sender_balance.get('balance', 0)} coins."
    )

async def daily_reward(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({'id': user_id}, projection={'last_daily_reward': 1, 'balance': 1})

    if user_data:
        last_claimed_date = user_data.get('last_daily_reward')
        if last_claimed_date and last_claimed_date.date() == datetime.utcnow().date():
            await update.message.reply_text("You've already claimed your daily reward today.")
            return

    await user_collection.update_one(
        {'id': user_id},
        {'$inc': {'balance': 20}, '$set': {'last_daily_reward': datetime.utcnow()}}
    )
    await update.message.reply_text("🎉 You've claimed your daily reward of 20 coins!")

async def mtop(update: Update, context: CallbackContext):
    top_users = await user_collection.find({}, projection={'id': 1, 'first_name': 1, 'balance': 1}).sort('balance', -1).limit(10).to_list(10)

    top_message = "🏆 **Top 10 Users with Highest Balance:**\n"
    for i, user in enumerate(top_users, start=1):
        first_name = user.get('first_name', 'Unknown')
        user_id = user.get('id', 'Unknown')
        top_message += f"{i}. <a href='tg://user?id={user_id}'>{first_name}</a> - 💵 {user.get('balance', 0)} coins\n"

    await update.message.reply_photo(
        photo='https://telegra.ph/file/8fce79d744297133b79b6.jpg',
        caption=top_message,
        parse_mode='HTML'
    )

async def nguess(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if chat_id != SUPPORT_GROUP_ID:
        await update.message.reply_text("❌ This command only works in @seal_Your_WH_Group.")
        return

    characters = await collection.aggregate([{"$sample": {"size": 1}}]).to_list(1)
    if not characters:
        await update.message.reply_text("No waifus found in the database.")
        return

    character = characters[0]
    character_name = character['name'].strip().lower()

    current_characters[chat_id] = {
        "character": character,
        "guessed": False
    }

    await update.message.reply_photo(photo=character['img_url'], caption="✨ Guess this Waifu! 🧐✨")

    context.job_queue.run_once(send_timeout_message, when=300, data={"chat_id": chat_id, "character_name": character_name})



async def handle_guess(update, context):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    guess = update.message.text.strip().lower()

    if chat_id in current_character:
        data = current_character[chat_id]
        character = data["character"]
        correct_name = character['name'].strip().lower()

        if not data["guessed"] and guess in correct_name:  # Allow partial name match
            await add_coins(user_id, 20)

            if chat_id not in streaks:
                streaks[chat_id] = {"streak": 1, "misses": 0}
            else:
                streaks[chat_id]["streak"] += 1
                streaks[chat_id]["misses"] = 0  

            streak = streaks[chat_id]["streak"]

            await update.message.reply_text(f"🎉 Correct! You've earned 20 coins! Your streak is {streak}! 🎉")
            data["guessed"] = True  

            if "timeout" in data and not data["timeout"].done():
                data["timeout"].cancel()

            reward_map = {30: 1000, 50: 1500, 100: 2000}
            if streak in reward_map:
                await add_coins(user_id, reward_map[streak])
                await update.message.reply_text(f"🎉 {streak}-streak! Earned {reward_map[streak]} coins! 🎉")

                if streak == 100:
                    streaks[chat_id]["streak"] = 0  

            del current_character[chat_id]

async def send_timeout_message(context: CallbackContext):
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    character_name = job_data["character_name"]

    if chat_id in current_characters and not current_characters[chat_id]["guessed"]:
        await context.bot.send_message(chat_id, f"⏳ Time's up! The correct answer was **{character_name}**.")
        del current_characters[chat_id]

async def name(update, context):
    if not update.message or not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("Please reply to a waifu image to get the character name.")
        return

    chat_id = update.effective_chat.id

    if chat_id in current_character:
        character = current_character[chat_id]["character"]
        character_name = character['name']

        copy_string = f"None {character_name}"

        await update.message.reply_text(
            f"**Character Name:** {character_name}\n\n"
            f"**Copy String:** `{copy_string}`",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("No active waifu guess found!")
        
application.add_handler(CommandHandler("balance", balance))
application.add_handler(CommandHandler("pay", pay))
application.add_handler(CommandHandler("daily", daily_reward))
application.add_handler(CommandHandler("mtop", mtop))
application.add_handler(CommandHandler("nguess", nguess))
application.add_handler(CommandHandler("name", name))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess))
