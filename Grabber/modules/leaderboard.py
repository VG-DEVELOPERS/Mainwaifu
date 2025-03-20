import os
import html
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from Grabber import (application, user_collection, 
                     top_global_groups_collection, group_user_totals_collection, sudo_users as SUDO_USERS)

async def global_leaderboard(update: Update, context: CallbackContext) -> None:
    cursor = top_global_groups_collection.aggregate([
        {"$project": {"group_name": 1, "count": 1}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ])
    leaderboard_data = await cursor.to_list(length=20)

    if not leaderboard_data:
        await update.message.reply_text("No groups have guessed characters yet.")
        return

    leaderboard_message = "<b>🏆 TOP 20 GROUPS WITH MOST GUESSED CHARACTERS 🏆</b>\n\n"
    for i, group in enumerate(leaderboard_data, start=1):
        group_name = html.escape(group.get('group_name', 'Unknown'))
        count = group['count']
        leaderboard_message += f'{i}. <b>{group_name[:25]}...</b> ➾ <b>{count}</b>\n'

    photo_url = "https://telegra.ph/file/1d9c963d5a138dc3c3077.jpg"
    await update.message.reply_photo(photo=photo_url, caption=leaderboard_message, parse_mode='HTML')

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
        first_name = html.escape(user.get('first_name', 'Unknown'))
        character_count = user['character_count']
        leaderboard_message += f'{i}. <a href="tg://user?id={user_id}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>\n'

    photo_url = "https://telegra.ph/file/1d9c963d5a138dc3c3077.jpg"
    await update.message.reply_photo(photo=photo_url, caption=leaderboard_message, parse_mode='HTML')

async def broadcast(update: Update, context: CallbackContext) -> None:
    OWNER_ID = '7717913705'
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text('Only the owner can use this command.')
        return

    if not update.message.reply_to_message:
        await update.message.reply_text('Reply to a message to broadcast.')
        return

    all_users = await user_collection.find({}).to_list(length=None)
    all_groups = await group_user_totals_collection.find({}).to_list(length=None)

    unique_user_ids = set(user['id'] for user in all_users)
    unique_group_ids = set(group['group_id'] for group in all_groups)

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

    await update.message.reply_text(f'Broadcast report:\nTotal sent: {total_sent}\nTotal failed: {total_failed}')

async def broadcast2(update: Update, context: CallbackContext) -> None:
    OWNER_ID = '7717913705'
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text('Only the owner can use this command.')
        return

    if not update.message.reply_to_message:
        await update.message.reply_text('Reply to a message to broadcast.')
        return

    all_groups = await group_user_totals_collection.find({}).to_list(length=None)
    unique_group_ids = set(group['group_id'] for group in all_groups)

    total_sent = 0
    total_failed = 0

    for group_id in unique_group_ids:
        try:
            await context.bot.forward_message(chat_id=group_id, from_chat_id=update.effective_chat.id, message_id=update.message.reply_to_message.message_id)
            total_sent += 1
        except Exception:
            total_failed += 1

    await update.message.reply_text(f'Broadcast report:\nTotal sent: {total_sent}\nTotal failed: {total_failed}')

async def stats(update: Update, context: CallbackContext) -> None:
    OWNER_ID = '7717913705'
    if str(update.effective_user.id) != OWNER_ID:
        await update.message.reply_text('Only the owner can use this command.')
        return

    user_count = await user_collection.count_documents({})
    group_count = len(await group_user_totals_collection.distinct('group_id'))
    await update.message.reply_text(f'Total Users: {user_count}\nTotal Groups: {group_count}')

async def send_users_document(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in SUDO_USERS:
        await update.message.reply_text('Only sudo users can use this command.')
        return

    cursor = user_collection.find({})
    users = []
    async for document in cursor:
        users.append(document)

    user_list = "\n".join([user['first_name'] for user in users])

    with open('users.txt', 'w') as f:
        f.write(user_list)

    with open('users.txt', 'rb') as f:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=f)

    os.remove('users.txt')

async def send_groups_document(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in SUDO_USERS:
        await update.message.reply_text('Only sudo users can use this command.')
        return

    cursor = top_global_groups_collection.find({})
    groups = []
    async for document in cursor:
        groups.append(document)

    group_list = "\n".join([group['group_name'] for group in groups])

    with open('groups.txt', 'w') as f:
        f.write(group_list)

    with open('groups.txt', 'rb') as f:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=f)

    os.remove('groups.txt')

application.add_handler(CommandHandler('ctop', leaderboard, block=False))
application.add_handler(CommandHandler('stats', stats, block=False))
application.add_handler(CommandHandler('TopGroups', global_leaderboard, block=False))
application.add_handler(CommandHandler('broadcast2', broadcast2, block=False))
application.add_handler(CommandHandler('list', send_users_document, block=False))
application.add_handler(CommandHandler('groups', send_groups_document, block=False))
application.add_handler(CommandHandler('top', leaderboard, block=False))
application.add_handler(CommandHandler('broadcast', broadcast, block=False))
  
