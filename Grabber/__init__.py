import logging  

from pyrogram import Client 

from telegram.ext import Application
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)

logging.getLogger("apscheduler").setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger("pyrate_limiter").setLevel(logging.ERROR)
LOGGER = logging.getLogger(__name__)

OWNER_ID = '5932230962'
sudo_users = ["5932230962", "6898401947", "6898401947", "6898401947", "6898401947", "6898401947"]
GROUP_ID = "-1001875834087"
TOKEN = "6662679878:AAGNqNfkpfz0ngzhkq8xbBtanyRPrnBXmDg"
mongo_url = "mongodb+srv://husbando:husbando@cluster0.pipkivx.mongodb.net/?retryWrites=true&w=majority"
PHOTO_URL = ["/https://telegra.ph/file/aa06eb4b312f456e1fd28.jpg", "https://telegra.ph/file/aa06eb4b312f456e1fd28.jpg"]
SUPPORT_CHAT = "VG_BOTZ_SUPPORT"
UPDATE_CHAT = "TEAMS_VG"
BOT_USERNAME = "Dark_waifu_Bot"
CHARA_CHANNEL_ID = "-1001875834087"
api_id = "25635673"
api_hash = "ec69ce8b56c71541499c914fabd08286"
JOINLOGS = "-1001875834087"
LEAVELOGS = "-1001875834087"

application = Application.builder().token(TOKEN).build()
Grabberu = Client("Grabber", api_id, api_hash, bot_token=TOKEN)
client = AsyncIOMotorClient(mongo_url)
db = client['Character_catcher']
collection = db['anime_characters']
user_totals_collection = db['user_totals']
user_collection = db["user_collection"]
group_user_totals_collection = db['group_user_total']
top_global_groups_collection = db['top_global_groups']
