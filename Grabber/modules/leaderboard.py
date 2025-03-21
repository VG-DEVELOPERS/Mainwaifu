import os
import html
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from Grabber import (
    application, PHOTO_URL, OWNER_ID,
    user_collection, top_global_groups_collection,
    group_user_totals_collection, Grabberu as app
)
from Grabber import sudo_users as SUDO_USERS
from pyrogram import Client, filters
from pyrogram.types import Message

async def global_leaderboard(update: Update, context: CallbackContext) -> None:
    cursor = top_global_groups_collection.aggregate([
        {"$group": {"_id": "$group_id", "group_name": {"$first": "$group_name"}, "total_count": {"$sum": "$count"}}},
        {"$sort": {"total_count": -1}},
        {"$limit": 20}
    ])
    leaderboard_data = await cursor.to_list(length=20)

    if not leaderboard_data:
        await update.message.reply_text("No group data available.")
        return

    leaderboard_message = "<b>🏆 TOP 20 GROUPS WHO GUESSED MOST CHARACTERS 🏆</b>\n\n"
    for i, group in enumerate(leaderboard_data, start=1):
        group_name = html.escape(group.get('group_name', 'Unknown'))
        if len(group_name) > 25:
            group_name = group_name[:25] + '...'
        leaderboard_message += f'{i}. <b>{group_name}</b> ➾ <b>{group["total_count"]}</b>\n'

    await update.message.reply_photo(
        photo=PHOTO_URL,
        caption=leaderboard_message,
        parse_mode='HTML'
    )

async def ctop(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    cursor = group_user_totals_collection.aggregate([
        {"$match": {"group_id": chat_id}},
        {"$project": {"username": 1, "first_name": 1, "character_count": "$count"}},
        {"$sort": {"character_count": -1}},
        {"$limit": 10}
    ])
    leaderboard_data = await cursor.to_list(length=10)

    if not leaderboard_data:
        await update.message.reply_text("No data available for this group.")
        return

    leaderboard_message = "<b>TOP 10 USERS WHO GUESSED MOST CHARACTERS IN THIS GROUP</b>\n\n"
    for i, user in enumerate(leaderboard_data, start=1):
        username = user.get('username', 'Unknown')
        first_name = html.escape(str(user.get('first_name', 'Unknown') or 'Unknown'))
        character_count = user['character_count']
        leaderboard_message += f'{i}. <a href="https://t.me/{username}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>\n'

    await update.message.reply_photo(
        photo=PHOTO_URL,
        caption=leaderboard_message,
        parse_mode='HTML'
    )

async def leaderboard(update: Update, context: CallbackContext) -> None:
    cursor = user_collection.aggregate([
        {"$group": {"_id": "$id", "first_name": {"$first": "$first_name"}, "character_count": {"$sum": {"$size": "$characters"}}}},
        {"$sort": {"character_count": -1}},
        {"$limit": 10}
    ])
    leaderboard_data = await cursor.to_list(length=10)

    if not leaderboard_data:
        await update.message.reply_text("No users have collected characters yet.")
        return

    leaderboard_message = "<b>🏆 TOP 10 USERS WITH MOST CHARACTERS 🏆</b>\n\n"
    for i, user in enumerate(leaderboard_data, start=1):
        user_id = user.get('_id')
        first_name = html.escape(str(user.get('first_name', 'Unknown') or 'Unknown'))
        character_count = user['character_count']
        leaderboard_message += f'{i}. <a href="tg://user?id={user_id}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>\n'

    await update.message.reply_photo(
        photo=PHOTO_URL,
        caption=leaderboard_message,
        parse_mode='HTML'
    )

async def broadcast(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text("Only the owner can use this command.")
        return

    if update.message.reply_to_message is None:
        await update.message.reply_text("Reply to a message to broadcast.")
        return

    all_users = await user_collection.find({}).to_list(length=None)
    all_groups = await group_user_totals_collection.find({}).to_list(length=None)

    unique_user_ids = {user.get('id') for user in all_users if user.get('id')}
    unique_group_ids = {group.get('group_id') for group in all_groups if group.get('group_id')}

    total_sent = 0
    total_failed = 0

    for user_id in unique_user_ids:
        try:
            await context.bot.forward_message(chat_id=user_id, from_chat_id=update.effective_chat.id, message_id=update.message.reply_to_message.message_id)
            total_sent += 1
        except Exception:
            total_failed += 1

    for group_id in unique_group_ids:
        try:
            await context.bot.forward_message(chat_id=group_id, from_chat_id=update.effective_chat.id, message_id=update.message.reply_to_message.message_id)
            total_sent += 1
        except Exception:
            total_failed += 1

    await update.message.reply_text(f"📢 **Broadcast Report:**\n✅ Sent: {total_sent}\n❌ Failed: {total_failed}")

async def stats(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in SUDO_USERS:
        await update.message.reply_text("Only for sudo users.")
        return

    user_count = await user_collection.count_documents({})
    group_count = len(await group_user_totals_collection.distinct('group_id'))

    await update.message.reply_text(f"Total Users: {user_count}\nTotal Groups: {group_count}")

async def shop(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    shop_url = f"https://yourshopwebsite.com/login?userid={user_id}"
    await update.message.reply_text(f"🛍️ Access the shop here: [Click Here]({shop_url})", parse_mode="Markdown")

application.add_handler(CommandHandler('ctop', ctop, block=False))
application.add_handler(CommandHandler('stats', stats, block=False))
application.add_handler(CommandHandler('TopGroups', global_leaderboard, block=False))
application.add_handler(CommandHandler('broadcast', broadcast, block=False))
application.add_handler(CommandHandler('top', leaderboard, block=False))
application.add_handler(CommandHandler('shop', shop, block=False))
