import os
import sys

from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import CallbackContext

logger = setup_logging(__file__)


async def prepairing_document(update: Update, context: CallbackContext):
    file_id = update.message.document
    file = await context.bot.get_file(file_id)
    file_name = update.message.document.file_name
    file_extension = file_name.split(".")[-1]
    file_path = os.path.join(sys.path[0], "file." + file_extension)
    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass
    await file.download_to_drive(file_path)
    return file_path, file_name


async def prepairing_audio(update: Update, context: CallbackContext):
    file_id = update.message.audio.file_id
    file = await context.bot.get_file(file_id)
    file_name = update.message.audio.file_name
    file_path = os.path.join(sys.path[0], "audio.mp3")
    print(file_path)
    await file.download(file_path)
    return file_path, file_name
