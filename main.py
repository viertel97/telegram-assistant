import os

from loguru import logger
from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

from handler.document_handler import handle_document
from services.grabber_service import dump_todoist_to_monica
from services.transcriber_service import separate, video_to_text, voice_to_text
from services.wol_service import wol

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

if os.name == "nt":
    file_path = "bad_habit.json"
    DEBUG = True
else:
    file_path = "/home/pi/python/bad_habit.json"
    DEBUG = False
logger.info("DEBUG MODE: " + str(DEBUG))

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def start(update: Update, context: CallbackContext):
    update.message.reply_text(text="Do Stuff.")


def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler(str("start"), start)
    wol_handler = CommandHandler(str("wol"), wol)
    book_seperator_handler = CommandHandler(str("book_separator"), separate)
    oh_handler = MessageHandler(Filters.voice, voice_to_text)
    audiobook_to_notion_handler = MessageHandler(Filters.video, video_to_text)
    doc_handler = MessageHandler(Filters.document, handle_document)
    dump_to_monica_handler = CommandHandler(str("dump_todoist_to_monica"), dump_todoist_to_monica)

    handlers = [
        start_handler,
        wol_handler,
        book_seperator_handler,
        oh_handler,
        audiobook_to_notion_handler,
        doc_handler,
        dump_to_monica_handler,
    ]
    [dispatcher.add_handler(handler) for handler in handlers]

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
