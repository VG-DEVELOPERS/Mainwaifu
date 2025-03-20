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
        {"$project": {"group_name": 1, "count": 1}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ])
    leaderboard_data = await cursor.to_list(length=20)

    if not leaderboard_data:
        await update.message.reply_text("No group data available.")
        return

    leaderboard_message = "<b>TOP 20 GROUPS WHO GUESSED MOST CHARACTERS</b>\n\n"
    for i, group in enumerate(leaderboard_data, start=1):
        group_name = html.escape(group.get('group_name', 'Unknown'))
        if len(group_name) > 20:
            group_name = group_name[:25] + '...'
        leaderboard_message += f'{i}. <b>{group_name}</b> ➾ <b>{group["count"]}</b>\n'

    await update.message.reply_photo(
        photo="https://telegra.ph/file/1d9c963d5a138dc3c3077.jpg",
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

    leaderboard_message = "<b>TOP 10 USERS WHO GUESSED CHARACTERS MOST IN THIS GROUP</b>\n\n"
    for i, user in enumerate(leaderboard_data, start=1):
        username = user.get('username', 'Unknown')
        first_name = html.escape(str(user.get('first_name', 'Unknown') or 'Unknown'))
        character_count = user['character_count']
        leaderboard_message += f'{i}. <a href="https://t.me/{username}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>\n'

    await update.message.reply_photo(
        photo="https://telegra.ph/file/1d9c963d5a138dc3c3077.jpg",
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
        photo="https://telegra.ph/file/1d9c963d5a138dc3c3077.jpg",
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

    unique_user_ids = {user['id'] for user in all_users}
    unique_group_ids = {group['group_id'] for group in all_groups}

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

    await update.message.reply_text(f"Broadcast Report:\nTotal Sent: {total_sent}\nTotal Failed: {total_failed}")


async def stats(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in SUDO_USERS:
        await update.message.reply_text("Only for sudo users.")
        return

    user_count = await user_collection.count_documents({})
    group_count = len(await group_user_totals_collection.distinct('group_id'))

    await update.message.reply_text(f"Total Users: {user_count}\nTotal Groups: {group_count}")


async def send_users_document(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in SUDO_USERS:
        await update.message.reply_text("Only for sudo users.")
        return

    users = await user_collection.find({}).to_list(length=None)
    user_list = "\n".join(user['first_name'] for user in users if 'first_name' in user)

    with open("users.txt", "w") as f:
        f.write(user_list)

    with open("users.txt", "rb") as f:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=f)

    os.remove("users.txt")


async def send_groups_document(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in SUDO_USERS:
        await update.message.reply_text("Only for sudo users.")
        return

    groups = await top_global_groups_collection.find({}).to_list(length=None)
    group_list = "\n".join(group['group_name'] for group in groups if 'group_name' in group)

    with open("groups.txt", "w") as f:
        f.write(group_list)

    with open("groups.txt", "rb") as f:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=f)

    os.remove("groups.txt")


application.add_handler(CommandHandler('ctop', ctop, block=False))
application.add_handler(CommandHandler('stats', stats, block=False))
application.add_handler(CommandHandler('TopGroups', global_leaderboard, block=False))
application.add_handler(CommandHandler('broadcast', broadcast, block=False))
application.add_handler(CommandHandler('list', send_users_document, block=False))
application.add_handler(CommandHandler('groups', send_groups_document, block=False))
application.add_handler(CommandHandler('top', leaderboard, block=False))
