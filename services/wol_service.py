from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import CallbackContext
from wakeonlan import send_magic_packet

from helper.config_helper import is_not_correct_chat_id

logger = setup_logging(__file__)
PC_MAC = get_secrets("PC_MAC")


async def start_pc_via_wol(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return
    send_magic_packet(PC_MAC)
    await update.message.reply_text("PC started")
