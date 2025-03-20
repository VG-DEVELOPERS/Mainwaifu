import os
import random
import html

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from Grabber import (application, PHOTO_URL, OWNER_ID,
                    user_collection, top_global_groups_collection, top_global_groups_collection, 
                    group_user_totals_collection, Grabberu as app)

from Grabber import sudo_users as SUDO_USERS 
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant, PeerIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

    
async def global_leaderboard(update: Update, context: CallbackContext) -> None:
   
    cursor = top_global_groups_collection.aggregate([
        {"$project": {"group_name": 1, "count": 1}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ])
    leaderboard_data = await cursor.to_list(length=20)

    leaderboard_message = "<b>TOP 20 GROUPS WHO GUESSED MOST CHARACTERS</b>\n\n"

    for i, group in enumerate(leaderboard_data, start=1):
        group_name = html.escape(group.get('group_name', 'Unknown'))

        if len(group_name) > 20:
            group_name = group_name[:25] + '...'
        count = group['count']
        leaderboard_message += f'{i}. <b>{group_name}</b> ➾ <b>{count}</b>\n'
    
    
    photo_url = "https://telegra.ph/file/1d9c963d5a138dc3c3077.jpg"  # Your photo URL

    await update.message.reply_photo(photo=photo_url, caption=leaderboard_message, parse_mode='HTML')

async def ctop(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    cursor = group_user_totals_collection.aggregate([
        {"$match": {"group_id": chat_id}},
        {"$project": {"username": 1, "first_name": 1, "character_count": "$count"}},
        {"$sort": {"character_count": -1}},
        {"$limit": 10}
    ])
    leaderboard_data = await cursor.to_list(length=10)

    leaderboard_message = "<b>TOP 10 USERS WHO GUESSED CHARACTERS MOST TIME IN THIS GROUP..</b>\n\n"

    for i, user in enumerate(leaderboard_data, start=1):
        username = user.get('username', 'Unknown')
        first_name = html.escape(user.get('first_name', 'Unknown'))

        if len(first_name) > 10:
            first_name = first_name[:15] + '...'
        character_count = user['character_count']
        leaderboard_message += f'{i}. <a href="https://t.me/{username}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>\n'
    
    photo_url = "https://telegra.ph/file/1d9c963d5a138dc3c3077.jpg"  # Your photo URL

    await update.message.reply_photo(photo=photo_url, caption=leaderboard_message, parse_mode='HTML')

async def ctop(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    cursor = group_user_totals_collection.aggregate([
        {"$match": {"group_id": chat_id}},
        {"$project": {"username": 1, "first_name": 1, "character_count": "$count"}},
        {"$sort": {"character_count": -1}},
        {"$limit": 10}
    ])
    leaderboard_data = await cursor.to_list(length=10)

    leaderboard_message = "<b>TOP 10 USERS WHO GUESSED CHARACTERS MOST TIME IN THIS GROUP..</b>\n\n"

    for i, user in enumerate(leaderboard_data, start=1):
        username = user.get('username', 'Unknown')
        first_name = html.escape(user.get('first_name', 'Unknown'))

        if len(first_name) > 10:
            first_name = first_name[:15] + '...'
        character_count = user['character_count']
        leaderboard_message += f'{i}. <a href="https://t.me/{username}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>\n'
    
    photo_url = "https://telegra.ph/file/1d9c963d5a138dc3c3077.jpg"  # Your photo URL

    await update.message.reply_photo(photo=photo_url, caption=leaderboard_message, parse_mode='HTML')
  
async def leaderboard(update: Update, context: CallbackContext) -> None:
    cursor = user_collection.aggregate([
        {"$group": {"_id": "$id", "first_name": {"$first": "$first_name"}, "character_count": {"$sum": {"$size": "$characters"}}}},
        {"$sort": {"character_count": -1}},
        {"$limit": 10}
    ])
    leaderboard_data = await cursor.to_list(length=10)

    leaderboard_message = "<b>🏆 TOP 10 USERS WITH MOST CHARACTERS 🏆</b>\n\n"

    for i, user in enumerate(leaderboard_data, start=1):
        user_id = user.get('_id')
        first_name = html.escape(user.get('first_name', 'Unknown'))
        
        if len(first_name) > 15:
            first_name = first_name[:15] + '...'

        character_count = user['character_count']
        leaderboard_message += f'{i}. <a href="tg://user?id={user_id}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>\n'

    photo_url = "https://telegra.ph/file/1d9c963d5a138dc3c3077.jpg"

    await update.message.reply_photo(photo=photo_url, caption=leaderboard_message, parse_mode='HTML')
  
async def broadcast(update: Update, context: CallbackContext) -> None:
    OWNER_ID = '7717913705'  # Set the OWNER_ID directly within the function

    if str(update.effective_user.id) == OWNER_ID:
        if update.message.reply_to_message is None:
            await update.message.reply_text('Please reply to a message to broadcast.')
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

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Broadcast report:\n\nTotal messages sent successfully: {total_sent}\nTotal messages failed to send: {total_failed}'
        )
    else:
        await update.message.reply_text('Only Murat Can use')


async def broadcast2(update: Update, context: CallbackContext) -> None:
    OWNER_ID = '7717913705'  # Set the OWNER_ID directly within the function

    if str(update.effective_user.id) == OWNER_ID:
        if update.message.reply_to_message is None:
            await update.message.reply_text('Please reply to a message to broadcast.')
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

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Broadcast report:\n\nTotal messages sent successfully: {total_sent}\nTotal messages failed to send: {total_failed}'
        )
    else:
        await update.message.reply_text('Only the owner can use this command for group broadcast.')

async def stats(update: Update, context: CallbackContext) -> None:
    OWNER_ID = ['7717913705']  # Replace '123456789' with the actual owner ID

    if str(update.effective_user.id) not in OWNER_ID:
        await update.message.reply_text('Only for sudo users...')
        return

    user_count = await user_collection.count_documents({})

    group_count = len(await group_user_totals_collection.distinct('group_id'))

    await update.message.reply_text(f'Total Users: {user_count}\nTotal Groups: {group_count}')

@app.on_message(filters.command("topss") & filters.group)
async def top_waifus(client: Client, message: Message):
    """Shows the top 10 users with the most claimed waifus."""
    
    top_users = await user_collection.find(
        {}, 
        projection={'id': 1, 'first_name': 1, 'waifu_count': 1}
    ).sort('waifu_count', -1).limit(10).to_list(10)

    if not top_users:
        return await message.reply_text("⚠️ No users have claimed waifus yet.")

    leaderboard_message = "🏆 **Top 10 Users with Most Waifus:**\n\n"

    for i, user in enumerate(top_users, start=1):
        first_name = user.get('first_name', 'Unknown')
        user_id = user.get('id', 'Unknown')
        waifu_count = user.get('waifu_count', 0)

        # Ensure user_id is an integer before making a clickable link
        if isinstance(user_id, int):
            profile_link = f"[{first_name}](tg://user?id={user_id})"
        else:
            profile_link = first_name  # If no valid ID, just show the name

        leaderboard_message += f"{i}. {profile_link} ➾ {waifu_count} waifus\n"

    await update.message.reply_photo(photo=photo_url, caption=leaderboard_message, parse_mode='HTML')




async def send_users_document(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in SUDO_USERS:
        update.message.reply_text('only For Sudo users...')
        return
    cursor = user_collection.find({})
    users = []
    async for document in cursor:
        users.append(document)
    user_list = ""
    for user in users:
        user_list += f"{user['first_name']}\n"
    with open('users.txt', 'w') as f:
        f.write(user_list)
    with open('users.txt', 'rb') as f:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
    os.remove('users.txt')

async def send_groups_document(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in SUDO_USERS:
        update.message.reply_text('Only For Sudo users...')
        return
    cursor = top_global_groups_collection.find({})
    groups = []
    async for document in cursor:
        groups.append(document)
    group_list = ""
    for group in groups:
        group_list += f"{group['group_name']}\n"
        group_list += "\n"
    with open('groups.txt', 'w') as f:
        f.write(group_list)
    with open('groups.txt', 'rb') as f:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
    os.remove('groups.txt')



application.add_handler(CommandHandler('ctop', ctop, block=False))
application.add_handler(CommandHandler('stats', stats, block=False))
application.add_handler(CommandHandler('TopGroups', global_leaderboard, block=False))
application.add_handler(CommandHandler('broadcast2', broadcast2, block=False))

application.add_handler(CommandHandler('list', send_users_document, block=False))
application.add_handler(CommandHandler('groups', send_groups_document, block=False))


application.add_handler(CommandHandler('top', leaderboard, block=False))
application.add_handler(CommandHandler('broadcast', broadcast, block=False))
