import os

import telegram.ext.filters as filters
from loguru import logger
from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler, MessageHandler

from handler.audio_handler import handle_audio
from handler.document_handler import handle_document
from services.grabber_service import dump_todoist_to_monica
from services.notion_service import stretch_TPT
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


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(text="Do Stuff.")


def get_command_handler():
    return (
        CommandHandler(str("start"), start),
        CommandHandler(str("wol"), wol),
        CommandHandler(str("book_separator"), separate),
        CommandHandler(str("dump_todoist_to_monica"), dump_todoist_to_monica),
        CommandHandler(str("stretch_tpt"), stretch_TPT),
    )


def get_message_handler():
    return (
        MessageHandler(filters.VOICE, voice_to_text),
        MessageHandler(filters.VIDEO, video_to_text),
        MessageHandler(filters.Document.ALL, handle_document),
        MessageHandler(filters.AUDIO, handle_audio),
    )


def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    [
        application.add_handler(
            handler,
        )
        for handler in get_command_handler() + get_message_handler()
    ]
    application.run_polling()


if __name__ == "__main__":
    main()
