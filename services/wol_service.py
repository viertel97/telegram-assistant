import requests
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import CallbackContext

from helper.config_helper import is_not_correct_chat_id

logger = setup_logging(__file__)
WOL_WEBHOOK = get_secrets("WOL_WEBHOOK")


async def start_pc_via_wol(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return
    start_without_monitors = not (context.args[0] == 'False') if context.args else True

    requests.post("http://192.168.178.100:8123/api/webhook/" + WOL_WEBHOOK)
    if start_without_monitors:
        requests.post("http://tasker-proxy.custom.svc.cluster.local:9000/wol/status")
        await update.message.reply_text("PC started without monitors")
    else:
        await update.message.reply_text("PC started")
