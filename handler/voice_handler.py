from telegram import Update
from telegram.ext import CallbackContext

from services.transcriber_service import transcribe_voice


async def voice_to_text(update: Update, context: CallbackContext):
    await transcribe_voice(update, context)
