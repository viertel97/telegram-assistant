from telegram import Update
from telegram.ext import CallbackContext

from services.transcriber_service import transcribe_video


async def video_to_text(update: Update, context: CallbackContext):
    await transcribe_video(update, context)
