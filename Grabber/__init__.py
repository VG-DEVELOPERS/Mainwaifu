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

OWNER_ID = '7717913705'
sudo_users = ["7717913705", "5629555417", "5595153270", "2084725192", "6181035985", "7253335675", "7499006737"]
GROUP_ID = "-1002528887253"
TOKEN = "6707312532:AAHl5iVSFQeLL48bL8j-QEjzS7HfzOdTTaw"
mongo_url = "mongodb+srv://botmaker9675208:botmaker9675208@cluster0.sc9mq8b.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
PHOTO_URL = ["/https://telegra.ph/file/aa06eb4b312f456e1fd28.jpg", "https://telegra.ph/file/aa06eb4b312f456e1fd28.jpg"]
SUPPORT_CHAT = "seal_Your_WH_Group"
UPDATE_CHAT = "SEAL_UPDATE"
BOT_USERNAME = "Seal_Your_Waifu_Bot"
CHARA_CHANNEL_ID = "-1002643258398"
api_id = "25635673"
api_hash = "ec69ce8b56c71541499c914fabd08286"
JOINLOGS = "-1002528887253"
LEAVELOGS = "-1002528887253"

application = Application.builder().token(TOKEN).build()
Grabberu = Client("Grabber", api_id, api_hash, bot_token=TOKEN)
client = AsyncIOMotorClient(mongo_url)
db = client['Character_catchers']
collection = db['anime_characterss']
user_totals_collection = db['user_totalss']
user_collection = db["user_collections"]
group_user_totals_collection = db['group_user_totals']
top_global_groups_collection = db['top_global_groupss']
