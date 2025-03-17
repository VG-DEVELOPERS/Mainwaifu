from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from Grabber import application, sudo_users, db
OWNER_ID = 7717913705
# MongoDB collection for storing sudo users
sudo_collection = db['sudos']

async def add_sudo(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id == OWNER_ID:
        if len(context.args) != 1 or not context.args[0].isdigit():
            await update.message.reply_text("Please provide a valid user ID.")
            return

        new_sudo = int(context.args[0])
        existing_sudo = await sudo_collection.find_one({'user_id': new_sudo})
        if existing_sudo:
            await update.message.reply_text("This user is already a sudo.")
        else:
            await sudo_collection.insert_one({'user_id': new_sudo})
            await update.message.reply_text("User has been added as a sudo.")
    else:
        await update.message.reply_text("Only the owner can add sudo users.")

async def rm_sudo(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id == OWNER_ID:
        if len(context.args) != 1 or not context.args[0].isdigit():
            await update.message.reply_text("Please provide a valid user ID.")
            return

        remove_sudo = int(context.args[0])
        result = await sudo_collection.delete_one({'user_id': remove_sudo})
        if result.deleted_count:
            await update.message.reply_text("User has been removed from sudo.")
        else:
            await update.message.reply_text("This user is not a sudo.")
    else:
        await update.message.reply_text("Only the owner can remove sudo users.")

async def sudo_list(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id in sudo_users:
        sudo_users_cursor = sudo_collection.find({})
        sudo_list = await sudo_users_cursor.to_list(length=None)
        if sudo_list:
            sudo_ids = [str(sudo['user_id']) for sudo in sudo_list]
            await update.message.reply_text("Sudo users:\n" + "\n".join(sudo_ids))
        else:
            await update.message.reply_text("There are no sudo users.")
    else:
        await update.message.reply_text("You don't have permission to view the sudo list.")

# Register the command handlers
application.add_handler(CommandHandler("addsudo", add_sudo))
application.add_handler(CommandHandler("rmsudo", rm_sudo))
application.add_handler(CommandHandler("sudolist", sudo_list))
