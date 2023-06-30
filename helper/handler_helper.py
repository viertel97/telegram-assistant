import os
import sys

from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import CallbackContext

logger = setup_logging(__file__)


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
