import urllib.request
from pymongo import ReturnDocument

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from Grabber import application, sudo_users, collection, db, CHARA_CHANNEL_ID

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

async def upload(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask My Owner...')
        return

    try:
        args = context.args
        if len(args) != 4:
            await update.message.reply_text("""
❌ Wrong format! Example usage:  
/upload Img_url muzan-kibutsuji Demon-slayer 3

Format:  
img_url character-name anime-name rarity-number  

Use the correct rarity number based on the rarity map:

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

        character_name = args[1].replace('-', ' ').title()
        anime = args[2].replace('-', ' ').title()

        try:
            urllib.request.urlopen(args[0])
        except:
            await update.message.reply_text('Invalid URL.')
            return

        rarity_map = {
            1: "⚪ Common", 
            2: "🟠 Rare", 
            3: "🟡 Legendary", 
            4: "🟢 Medium", 
            5: "⛩️ Low", 
            6: "🐦‍🔥 High", 
            7: "⚡ Special", 
            8: "🔮 Limited", 
            9: "🫧 Supreme", 
            10: "💞 Valentine", 
            11: "🎃 Halloween", 
            12: "🌲 Christmas", 
            13: "❄️ Winter", 
            14: "🏖️ Summer", 
            15: "🎗 Marvellous"
        }
        
        try:
            rarity = rarity_map[int(args[3])]
        except KeyError:
            await update.message.reply_text("""
❌ Invalid rarity! Please use one of the following:

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

        id = str(await get_next_sequence_number('character_id')).zfill(2)

        character = {
            'img_url': args[0],
            'name': character_name,
            'anime': anime,
            'rarity': rarity,
            'id': id
        }

        message = await context.bot.send_photo(
            chat_id=CHARA_CHANNEL_ID,
            photo=args[0],
            caption=f'<b>Character Name:</b> {character_name}\n<b>Anime Name:</b> {anime}\n<b>Rarity:</b> {rarity}\n<b>ID:</b> {id}\nAdded by <a href="tg://user?id={update.effective_user.id}">{update.effective_user.first_name}</a>',
            parse_mode='HTML'
        )

        character['message_id'] = message.message_id
        await collection.insert_one(character)

        await update.message.reply_text('CHARACTER ADDED....')
    except Exception as e:
        await update.message.reply_text(f'Unsuccessfully uploaded. Error: {str(e)}')

UPLOAD_HANDLER = CommandHandler('upload', upload, block=False)
application.add_handler(UPLOAD_HANDLER)
