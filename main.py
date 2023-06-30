import os

import telegram.ext.filters as filters
from loguru import logger
from quarter_lib.akeyless import get_secrets
from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler, MessageHandler

from handler.audio_handler import handle_audio
from handler.command_handler import wol, separate, dump_todoist_to_monica, stretch_TPT
from handler.document_handler import handle_document
from handler.error_handler import handle_error
from handler.video_handler import video_to_text
from handler.voice_handler import voice_to_text

TELEGRAM_TOKEN = get_secrets("telegram/token")

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
        for handler in get_command_handler() + get_message_handler()  # + get_conversation_handler()
    ]
    application.add_error_handler(handle_error)

    application.run_polling()


if __name__ == "__main__":
    main()
