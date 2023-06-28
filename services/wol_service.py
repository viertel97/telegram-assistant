import os

from helper.config_helper import is_not_correct_chat_id
from loguru import logger
from telegram import Update
from telegram.ext import CallbackContext
from wakeonlan import send_magic_packet

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


async def start_pc_via_wol(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return
    send_magic_packet(os.environ["PC_MAC"])
    await update.message.reply_text("PC started")
