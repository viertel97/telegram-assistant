import os

from loguru import logger
from telegram import Update
from telegram.ext import CallbackContext

from handler.excel_handler import handle_excel
from handler.markdown_handler import handle_markdown
from handler.pdf_handler import handle_pdf
from handler.xml_handler import handle_xml
from handler.zip_handler import handle_zip
from helper.config_helper import is_not_correct_chat_id
from helper.handler_helper import prepairing_document

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


async def handle_document(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return
    await update.message.reply_text("start handle_document")
    mime_type = update.message.document.mime_type
    logger.info("received: " + mime_type)
    await update.message.reply_text("received: " + mime_type)
    file_path, file_name = await prepairing_document(update, context)
    if mime_type == "text/comma-separated-values":
        await update.message.reply_text("start handle_excel")
        await handle_excel(file_path, file_name, update)
    elif mime_type == "application/zip":
        await update.message.reply_text("start handle_zip")
        done_message = await handle_zip(file_path, file_name, update)
        await update.message.reply_text(done_message)
    elif mime_type == "text/markdown":
        await update.message.reply_text("start handle_markdown")
        done_message = handle_markdown(file_path, file_name, update)
        await update.message.reply_text(done_message)
    elif mime_type == "text/xml" or mime_type == "application/xml":
        await update.message.reply_text("start handle_xml")
        done_message = await handle_xml(file_path, file_name, update)
        await update.message.reply_text(done_message)
    elif mime_type == "application/pdf":
        await update.message.reply_text("start handle_pdf")
        await handle_pdf(file_path, file_name, update)
    else:
        logger.error("unsupported mime type: " + mime_type)
        await update.message.reply_text("unsupported mime type: " + mime_type)
