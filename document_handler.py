import os
import sys

from loguru import logger
from telegram import Update
from telegram.ext import CallbackContext

import kindle2notion
import process_excel

logger.add(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__))
        + "/logs/"
        + os.path.basename(__file__)
        + ".log"
    ),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def handle_document(update: Update, context: CallbackContext):
    mime_type = update.message.document.mime_type
    if mime_type == "text/comma-separated-values":
        file_id = update.message.document.file_id
        file = context.bot.get_file(file_id)
        file_name = update.message.document.file_name
        file_path = os.path.join(sys.path[0], file_name)
        file.download(file_path)
        process_excel.handle_excel(file_path, file_name)
    else:
        logger.error("unsupported mime type: " + mime_type)
