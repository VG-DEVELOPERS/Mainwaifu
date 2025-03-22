from pyrogram import Client, filters
import asyncio
from Grabber import Grabberu as shivuu, user_collection, group_user_totals_collection, db

# MongoDB Collections
characters_collection = db['anime_characters_lol']

# Define the possible rarities to avoid key errors
RARITIES = [
    '⚪ Common', '🟢 Medium', '🟠 Rare', '🟡 Legendary',
    '💠 Cosmic', '💮 Exclusive', '🔮 Limited Edition'
]

async def get_user_rarity_counts(user_id):
    rarity_counts = dict.fromkeys(RARITIES, 0)

    user = await user_collection.find_one({'id': user_id})
    if user:
        characters = user.get('characters', [])
        for char in characters:
            rarity = char.get('rarity', '⚪ Common')  # Default to '⚪ Common' if rarity is missing
            if rarity in rarity_counts:
                rarity_counts[rarity] += 1
            else:
                print(f"Unexpected rarity value: {rarity}")

    return rarity_counts

async def get_progress_bar(user_waifus_count, total_waifus_count):
    bar_width = 10
    progress = min(user_waifus_count / total_waifus_count, 1)
    progress_percent = min(progress * 100, 100)

    filled_width = int(progress * bar_width)
    empty_width = bar_width - filled_width

    progress_bar = "▰" * filled_width + "▱" * empty_width
    return progress_bar, progress_percent

def get_rank(progress_percent):
    ranks = [
        (5, "Bronze I"), (10, "Bronze II"), (15, "Bronze III"),
        (20, "Silver I"), (25, "Silver II"), (30, "Silver III"),
        (35, "Gold I"), (40, "Gold II"), (45, "Gold III"),
        (50, "Gold IV"), (55, "Platinum I"), (60, "Platinum II"),
        (65, "Platinum III"), (70, "Platinum IV"), (75, "Diamond I"),
        (80, "Diamond II"), (85, "Diamond III"), (90, "Diamond IV"),
        (95, "Heroic I"), (100, "Heroic II"), (105, "Heroic III"),
        (110, "Elite Heroic"), (115, "Master"), (120, "Crown"),
        (130, "Grandmaster I"), (140, "Grandmaster II"),
        (150, "Grandmaster III"), (160, "Conqueror")
    ]

    for percent, rank in ranks:
        if progress_percent <= percent:
            return rank

    return "Conqueror"

async def get_chat_top(chat_id, user_id):
    try:
        pipeline = [
            {"$match": {"group_id": chat_id}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        cursor = group_user_totals_collection.aggregate(pipeline)
        leaderboard_data = await cursor.to_list(length=None)
        
        for i, user in enumerate(leaderboard_data, start=1):
            if user.get('user_id') == user_id:
                return i
        
        return 'N/A'
    except Exception as e:
        print(f"Error getting chat top: {e}")
        return 'N/A'

async def get_global_top(user_id):
    try:
        pipeline = [
            {"$project": {"id": 1, "characters_count": {"$size": {"$ifNull": ["$characters", []]}}}},
            {"$sort": {"characters_count": -1}}
        ]
        cursor = user_collection.aggregate(pipeline)
        leaderboard_data = await cursor.to_list(length=None)
        
        for i, user in enumerate(leaderboard_data, start=1):
            if user.get('id') == user_id:
                return i
        
        return 'N/A'
    except Exception as e:
        print(f"Error getting global top: {e}")
        return 'N/A'

@shivuu.on_message(filters.command(["find"]))
async def find_character(client, message):
    try:
        character_id = " ".join(message.text.split()[1:]).strip()

        if not character_id:
            await message.reply("Please provide a character ID.")
            return

        character = await characters_collection.find_one({"id": character_id})

        if not character:
            await message.reply("No character found with that ID.")
            return

        response_message = (
            f"🧩 𝖶𝖺𝗂𝖿𝗎 𝖨𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇:\n\n"
            f"🪭 𝖭𝖺𝗆𝗲: {character['name']}\n"
            f"⚕️ 𝖱𝖺𝗋𝗂𝗍𝗒: {character['rarity']}\n"
            f"⚜️ 𝖠𝗇𝗂𝗆𝖾: {character['anime']}\n"
            f"🪅 𝖨𝖳: {character['id']}\n\n"
        )

        if 'image_url' in character:
            await message.reply_photo(
                photo=character['image_url'],
                caption=response_message
            )
        else:
            await message.reply_text(response_message)

        user_list_message = "✳️ 𝖧𝖾𝗋𝖾 𝗂𝗌 𝗍𝗁𝖾 𝗅𝗂𝗌𝗍 𝗈𝖿 𝗎𝗌𝖾𝗋𝗌 𝗐𝗁𝗈 𝗁𝖺𝗏𝖾 𝗍𝗁𝾀𝗂𝓈 𝖼𝗁𝖺𝗋𝖺𝒸𝗍𝖾𝗋 〽️:\n"
        user_cursor = characters_collection.find({"id": character['id']})
        user_list = []
        async for user in user_cursor:
            user_list.append(f"{user['username']} x{user['count']}")

        if user_list:
            user_list_message += "\n".join(user_list)
        else:
            user_list_message += "No users found."

        await message.reply_text(user_list_message)

    except Exception as e:
        print(f"Error: {e}")

@shivuu.on_message(filters.command(["status", "mystatus"]))
async def send_grabber_status(client, message):
    try:
        loading_message = await message.reply("🔄 Fetching Grabber Status...")

        for i in range(1, 6):
            await asyncio.sleep(1)
            await loading_message.edit_text("🔄 Fetching Grabber Status" + "." * i)

        user_id = message.from_user.id
        user = await user_collection.find_one({'id': user_id})

        if user:
            user_characters = user.get('characters', [])
            total_count = len(user_characters)
        else:
            total_count = 0

        total_waifus_count = await user_collection.count_documents({})

        chat_top = await get_chat_top(message.chat.id, user_id)
        global_top = await get_global_top(user_id)

        progress_bar, progress_percent = await get_progress_bar(total_count, total_waifus_count)
        rank = get_rank(progress_percent)
        current_xp = total_count
        next_level_xp = min(100, total_waifus_count)

        rarity_counts = await get_user_rarity_counts(user_id)

        profile_image_url = user.get('profile_image_url', None)

        rarity_message = (
            f"╔════════ • ✧ • ════════╗\n"
            f"          ⛩  『𝗨𝘀𝗲𝗿 𝗽𝗿𝗼𝗳𝗶𝗹𝗲』  ⛩\n"
            f"══════════════════════\n"
            f"➣ ❄️ 𝗡𝗮𝗺𝗲: {message.from_user.first_name} {message.from_user.last_name or ''}\n"
            f"➣ 🍀 𝗨𝘀𝗲𝗿 𝗜𝗗: {user_id}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 👾 𝗖𝗵𝗮𝗿𝗮𝗰𝘁𝗲𝗿𝘀 𝗖𝗼𝗹𝗹𝗲𝗰𝘁𝗲𝗱: {total_count}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 🧩 𝗟𝗲𝗀𝗲𝗇𝗱𝗮𝗿𝘆: {rarity_counts['🟡 Legendary']}\n"
            f"➣ 🧩 𝗥𝗮𝗿𝗲: {rarity_counts['🟠 Rare']}\n"
            f"➣ 🧩 𝗠𝗲𝗱𝗂𝘂𝗆: {rarity_counts['🟢 Medium']}\n"
            f"➣ 🧩 𝗖𝗼𝗺𝗺𝗼𝗻: {rarity_counts['⚪ Common']}\n"
            f"➣ 🧩 𝗖𝗼𝘀𝗺𝗶𝗰: {rarity_counts['💠 Cosmic']}\n"
            f"➣ 🧩 𝗘𝘅𝗰𝗹𝘂𝘀𝗂𝘃𝗲: {rarity_counts['💮 Exclusive']}\n"
            f"➣ 🧩 𝗟𝗶𝗺𝗶𝘁𝗲𝗱 𝗘𝗱𝗶𝘁𝗂𝗈𝗇: {rarity_counts['🔮 Limited Edition']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 💠 𝗚𝗿𝗮𝗯𝗯𝗲𝗋 𝗥𝗮𝗻𝗄: {rank}\n"
            f"➣ 🔝 𝗖𝗵𝗮𝘁 𝗧𝗼𝗽: {chat_top}\n"
            f"➣ 🔝 𝗚𝗹𝗼𝗯𝗮𝗹 𝗧𝗼𝗽: {global_top}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 📈 𝗣𝗿𝗈𝗀𝗋𝗲𝘀𝘀: {progress_bar} {progress_percent:.2f}%\n"
            f"➣ 📊 𝗫𝗽: {current_xp}/{next_level_xp}\n"
            f"╚════════ • ✧ • ════════╝"
        )

        if profile_image_url:
            await message.reply_photo(photo=profile_image_url, caption=rarity_message)
        else:
            await message.reply_text(rarity_message)

    except Exception as e:
        print(f"Error: {e}")

# Initialize the bot
