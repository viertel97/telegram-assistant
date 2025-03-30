from telegram import Update
from telegram.ext import CallbackContext

from src.helper.config_helper import is_not_correct_chat_id
from src.services.transcriber_service import transcribe_voice


async def voice_to_text(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return
	await transcribe_voice(update, context)
