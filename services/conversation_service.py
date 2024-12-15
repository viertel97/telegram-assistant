from quarter_lib.logging import setup_logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

from helper.config_helper import is_not_correct_chat_id
from services.microsoft_service import get_access_token, get_file_list

logger = setup_logging(__file__)

SELECTED_FILE = range(1)


async def get_last_calls(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return

    access_token = get_access_token()


    files, destination_folder_id = get_file_list("Anwendungen/Call Recorder - SKVALEX", access_token)

    file_names = [file["name"] for file in files[:20] if "@microsoft.graph.downloadUrl" in file.keys()]

    reply_keyboard = [[InlineKeyboardButton(file_name, callback_data=file_name)] for file_name in file_names]
    reply_markup = InlineKeyboardMarkup(reply_keyboard)

    await update.message.reply_text("Please choose:", reply_markup=reply_markup)


async def transcribe_call_from_one_drive(update: Update, context: CallbackContext):
    logger.info("start: Call to text")
    query = update.callback_query

    await query.answer()

    await query.edit_message_text(text=f"Selected option: {query.data}")

    logger.info("end: Call to text")