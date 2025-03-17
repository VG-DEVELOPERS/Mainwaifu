import requests
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from Grabber import application  # Assuming application is already initialized in shivu module

IMGBB_API_KEY = '5a5dadd79df17356e7250672f8b1b00b'

# Function to upload image to ImgBB
async def upload_to_imgbb(image_data):
    try:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                'key': IMGBB_API_KEY,
                'image': image_data
            }
        )
        response_data = response.json()

        if response_data['success']:
            return response_data['data']['url']
        else:
            return None
    except Exception as e:
        print(f"Error uploading to ImgBB: {str(e)}")
        return None

# Command handler for /gens
async def gens(update: Update, context: CallbackContext) -> None:
    # Check if the user has sent an image
    if not update.message.photo:
        await update.message.reply_text("Please send an image with this command.")
        return

    # Get the highest quality image file (largest size)
    file = await update.message.photo[-1].get_file()
    image_data = file.download_as_bytearray()

    # Upload to ImgBB
    imgbb_url = await upload_to_imgbb(image_data)

    if imgbb_url:
        # Send the image back to the user along with the URL
        await update.message.reply_photo(photo=imgbb_url, caption=f"Image successfully uploaded! Here's the URL:\n{imgbb_url}")
    else:
        await update.message.reply_text("Failed to upload image to ImgBB.")

# Handler for the /gens command
GENS_HANDLER = CommandHandler('gens', gens, block=False)

# Add the command handler to the bot's application
application.add_handler(GENS_HANDLER)
