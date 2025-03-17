import requests
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from Grabber import application  # Your bot instance

IMGBB_API_KEY = '5a5dadd79df17356e7250672f8b1b00b'

# Function to upload image to ImgBB
async def upload_to_imgbb(image_data):
    try:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={'key': IMGBB_API_KEY, 'image': image_data}
        )
        response_data = response.json()

        if response_data.get('success'):
            return response_data['data']['url']
        return None
    except Exception as e:
        print(f"Error uploading to ImgBB: {str(e)}")
        return None

# Command handler for /gens
async def gens(update: Update, context: CallbackContext) -> None:
    message = update.message
    photo = None

    # Check if command is a reply to an image
    if message.reply_to_message and message.reply_to_message.photo:
        photo = message.reply_to_message.photo[-1]
    elif message.photo:
        photo = message.photo[-1]

    if not photo:
        await update.message.reply_text("❌ Please send or reply to an image with this command.")
        return

    # Get the highest resolution image
    file = await photo.get_file()
    image_data = file.file_path  # Get file URL

    # Upload to ImgBB
    imgbb_url = await upload_to_imgbb(image_data)

    if imgbb_url:
        await update.message.reply_photo(photo=imgbb_url, caption=f"✅ Image uploaded successfully!\n🔗 {imgbb_url}")
    else:
        await update.message.reply_text("❌ Failed to upload image to ImgBB.")

# Register Command Handler
GENS_HANDLER = CommandHandler('tgm', gens, block=False)
application.add_handler(GENS_HANDLER)
