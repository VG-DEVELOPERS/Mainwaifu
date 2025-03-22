import random
from pyrogram import Client, filters
from pyrogram.types import Message
from Grabber import collection, application, group_user_totals_collection, JOINLOGS, LEAVELOGS


async def send_log(chat_id: int, message: str):
    await application.bot.send_message(chat_id=chat_id, text=message)

@Client.on_message(filters.new_chat_members)
async def on_new_chat_members(client: Client, message: Message):
    if (await client.get_me()).id in [user.id for user in message.new_chat_members]:
        chat_id = message.chat.id
        chat_title = message.chat.title
        chat_username = f"@{message.chat.username}" if message.chat.username else "Private Chat"
        added_by = message.from_user.mention if message.from_user else "Unknown User"

        existing_group = await group_user_totals_collection.find_one({'chat_id': chat_id})
        if not existing_group:
            await group_user_totals_collection.insert_one({
                'chat_id': chat_id,
                'chat_title': chat_title,
                'chat_username': chat_username,
                'added_by': added_by
            })

        log_text = f"✫ #NEW_GROUP ✫\n✫ Chat Title: {chat_title}\n✫ Chat ID: {chat_id}\n✫ Chat Username: {chat_username}\n✫ Added By: {added_by}"
        await send_log(JOINLOGS, log_text)

@Client.on_message(filters.left_chat_member)
async def on_left_chat_member(client: Client, message: Message):
    if (await client.get_me()).id == message.left_chat_member.id:
        chat_id = message.chat.id
        chat_title = message.chat.title
        removed_by = message.from_user.mention if message.from_user else "Unknown User"

        await group_user_totals_collection.delete_one({'chat_id': chat_id})

        log_text = f"✫ #LEFT_GROUP ✫\n✫ Chat Title: {chat_title}\n✫ Chat ID: {chat_id}\n✫ Removed By: {removed_by}"
        await send_log(LEAVELOGS, log_text)
        
