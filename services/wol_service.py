import requests
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
    start_without_monitors = not (context.args[0] == 'False') if context.args else True

    send_magic_packet(PC_MAC)
    if start_without_monitors:
        requests.post("http://127.0.0.1:9000/wol/status")
        await update.message.reply_text("PC started without monitors")
    else:
        await update.message.reply_text("PC started")
