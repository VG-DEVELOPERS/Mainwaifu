import aiohttp
from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from Grabber import application, sudo_users, collection, db, CHARA_CHANNEL_ID

# Generate a unique character ID
async def get_next_sequence_number(sequence_name):
    sequence_collection = db.sequences
    sequence_document = await sequence_collection.find_one_and_update(
        {'_id': sequence_name}, 
        {'$inc': {'sequence_value': 1}}, 
        return_document=ReturnDocument.AFTER
    )
    if not sequence_document:
        await sequence_collection.insert_one({'_id': sequence_name, 'sequence_value': 0})
        return 0
    return sequence_document['sequence_value']

# Validate image URL
async def is_valid_url(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url) as resp:
                return resp.status == 200
    except:
        return False

# Upload Command
async def upload(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('❌ You do not have permission to use this command.')
        return

    try:
        args = context.args
        if len(args) != 4:
            await update.message.reply_text("""
❌ Incorrect format! Example:  
/upload Img_url muzan-kibutsuji Demon-slayer 3  

<b>Rarity Map:</b>  
1 - ⚪ Common  
2 - 🟠 Rare  
3 - 🟡 Legendary  
4 - 🟢 Medium  
5 - ⛩️ Low  
6 - 🐦‍🔥 High  
7 - ⚡ Special  
8 - 🔮 Limited  
9 - 🫧 Supreme  
10 - 💞 Valentine  
11 - 🎃 Halloween  
12 - 🌲 Christmas  
13 - ❄️ Winter  
14 - 🏖️ Summer  
15 - 🎗 Marvellous  
""", parse_mode="HTML")
            return

        image_url, character_name, anime_name, rarity_number = args
        character_name = character_name.replace('-', ' ').title()
        anime_name = anime_name.replace('-', ' ').title()

        if not await is_valid_url(image_url):
            await update.message.reply_text('❌ Invalid image URL. Please check and try again.')
            return

        rarity_map = {
            1: "⚪ Common", 2: "🟠 Rare", 3: "🟡 Legendary", 4: "🟢 Medium",
            5: "⛩️ Low", 6: "🐦‍🔥 High", 7: "⚡ Special", 8: "🔮 Limited",
            9: "🫧 Supreme", 10: "💞 Valentine", 11: "🎃 Halloween",
            12: "🌲 Christmas", 13: "❄️ Winter", 14: "🏖️ Summer", 15: "🎗 Marvellous"
        }

        try:
            rarity = rarity_map[int(rarity_number)]
        except KeyError:
            await update.message.reply_text("❌ Invalid rarity number! Check the rarity map and try again.", parse_mode="HTML")
            return

        character_id = str(await get_next_sequence_number('character_id')).zfill(2)

        character = {
            'img_url': image_url,
            'name': character_name,
            'anime': anime_name,
            'rarity': rarity,
            'id': character_id
        }

        message = await context.bot.send_photo(
            chat_id=CHARA_CHANNEL_ID,
            photo=image_url,
            caption=f'<b>Character Name:</b> {character_name}\n<b>Anime Name:</b> {anime_name}\n<b>Rarity:</b> {rarity}\n<b>ID:</b> {character_id}\nAdded by <a href="tg://user?id={update.effective_user.id}">{update.effective_user.first_name}</a>',
            parse_mode='HTML'
        )

        character['message_id'] = message.message_id
        await collection.insert_one(character)

        await update.message.reply_text('✅ CHARACTER ADDED SUCCESSFULLY!')
    except Exception as e:
        await update.message.reply_text(f'❌ Upload failed. Error: {str(e)}')

# Delete Command
async def delete(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('❌ You do not have permission to use this command.')
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text('❌ Incorrect format! Use: `/delete ID`', parse_mode="Markdown")
            return

        character_id = args[0]

        character = await collection.find_one_and_delete({'id': character_id})
        if not character:
            await update.message.reply_text(f'❌ No character found with ID: {character_id}')
            return

        try:
            await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
            await update.message.reply_text(f'✅ Character with ID {character_id} deleted successfully.')
        except:
            await update.message.reply_text(f'⚠️ Character deleted from the database but not found in the channel.')

    except Exception as e:
        await update.message.reply_text(f'❌ Error while deleting: {str(e)}')

# Update Command
async def update(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('❌ You do not have permission to use this command.')
        return

    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text('❌ Incorrect format! Use: `/update ID field new_value`', parse_mode="Markdown")
            return

        character_id, field, new_value = args

        character = await collection.find_one({'id': character_id})
        if not character:
            await update.message.reply_text('❌ Character not found.')
            return

        valid_fields = ['img_url', 'name', 'anime', 'rarity']
        if field not in valid_fields:
            await update.message.reply_text(f'❌ Invalid field. Choose from: {", ".join(valid_fields)}')
            return

        if field in ['name', 'anime']:
            new_value = new_value.replace('-', ' ').title()
        elif field == 'rarity':
            rarity_map = {
                1: "⚪ Common", 2: "🟠 Rare", 3: "🟡 Legendary", 4: "🟢 Medium",
                5: "⛩️ Low", 6: "🐦‍🔥 High", 7: "⚡ Special", 8: "🔮 Limited",
                9: "🫧 Supreme", 10: "💞 Valentine", 11: "🎃 Halloween",
                12: "🌲 Christmas", 13: "❄️ Winter", 14: "🏖️ Summer", 15: "🎗 Marvellous"
            }
            try:
                new_value = rarity_map[int(new_value)]
            except KeyError:
                await update.message.reply_text('❌ Invalid rarity number!')
                return

        await collection.find_one_and_update({'id': character_id}, {'$set': {field: new_value}})

        await update.message.reply_text(f'✅ Character {field} updated successfully!')
    except Exception as e:
        await update.message.reply_text(f'❌ Update failed: {str(e)}')

# Register Handlers
application.add_handler(CommandHandler('upload', upload, block=False))
application.add_handler(CommandHandler('delete', delete, block=False))
application.add_handler(CommandHandler('update', update, block=False))
