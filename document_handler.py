import os
import sys

from loguru import logger
from telegram import Update
from telegram.ext import CallbackContext

import kindle2notion
from process_excel import handle_excel
from process_txt import handle_txt
from process_zip import handle_zip

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


def prepairing(update: Update, context: CallbackContext):
    file_id = update.message.document.file_id
    file = context.bot.get_file(file_id)
    file_name = update.message.document.file_name
    file_path = os.path.join(sys.path[0], file_name)
    file.download(file_path)
    return file_path, file_name


def handle_document(update: Update, context: CallbackContext):
    mime_type = update.message.document.mime_type
    logger.info("received: " + mime_type)
    if mime_type == "text/comma-separated-values":
        file_path, file_name = prepairing(update, context)
        handle_excel(file_path, file_name, update)
    elif mime_type == "application/zip":
        file_path, file_name = prepairing(update, context)
        handle_zip(file_path, file_name)
        update.message.reply_text("done")
    elif mime_type == "text/plain":
        file_path, file_name = prepairing(update, context)
        handle_txt(file_path, file_name, update)
    else:
        logger.error("unsupported mime type: " + mime_type)
