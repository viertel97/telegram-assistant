import os
import sys

from handler.excel_handler import handle_excel
from handler.zip_handler import handle_zip
from loguru import logger
from telegram import Update
from telegram.ext import CallbackContext

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


async def prepairing_document(update: Update, context: CallbackContext):
    file_id = update.message.document.file_id
    file = await context.bot.get_file(file_id)
    file_name = update.message.document.file_name
    file_path = os.path.join(sys.path[0], file_name)
    await file.download(file_path)
    return file_path, file_name


async def prepairing_audio(update: Update, context: CallbackContext):
    file_id = update.message.audio.file_id
    file = await context.bot.get_file(file_id)
    file_name = update.message.audio.file_name
    file_path = os.path.join(sys.path[0], file_name)
    print(file_path)
    await file.download(file_path)
    return file_path, file_name
