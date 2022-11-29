import os
import sys

from helper.handler_helper import prepairing_audio
from loguru import logger
from quarter_lib.easy_voice_recorder import get_meditation_logs
from telegram import Update
from telegram.ext import CallbackContext

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


async def handle_audio(update: Update, context: CallbackContext):
    mime_type, performer = update.message.audio.mime_type, update.message.audio.performer
    logger.info("received audio " + mime_type + " by " + performer)
    file_path, file_name = await prepairing_audio(update, context)
    if mime_type == "audio/mpeg" and performer == "Easy Voice Recorder Pro":
        done_message = get_meditation_logs(file_path, file_name)
        await update.message.reply_text(done_message)

    else:
        logger.error("unsupported mime type: " + mime_type)
