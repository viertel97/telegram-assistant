import os

from quarter_lib.logging import setup_logging
from quarter_lib.voice_recorder import get_meditation_logs
from quarter_lib.transcriber import convert_to_wav
from telegram import Update
from telegram.ext import CallbackContext

from src.helper.config_helper import is_not_correct_chat_id
from src.helper.handler_helper import prepairing_audio
from src.helper.telegram_helper import send_long_message
from src.services.groq_service import transcribe_groq

logger = setup_logging(__file__)


async def handle_audio(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return
	mime_type, performer = (
		update.message.audio.mime_type,
		update.message.audio.performer,
	)
	if not mime_type:
		if os.path.splitext(update.message.document.file_name)[1] in ["ogg", "oga"]:
			mime_type = "audio/ogg"
		if os.path.splitext(update.message.document.file_name)[1] in ["mp3", "m4a"]:
			mime_type = "audio/mpeg"
	if not performer:
		performer = "unknown"
	logger.info("received audio " + mime_type + " by " + performer)
	file_path, file_name = await prepairing_audio(update, context)

	if mime_type == "audio/mpeg" and performer == "Easy Voice Recorder Pro":
		await update.message.reply_text("start get_meditation_logs")
		done_message = get_meditation_logs(file_path, file_name)
		await update.message.reply_text(done_message)
	elif mime_type == "audio/ogg" or mime_type == "audio/mpeg":
		await update.message.reply_text("start transcribe_groq")
		wav_converted_file_path = convert_to_wav(file_path)
		transcription_list = await transcribe_groq(
			wav_converted_file_path, file_function=update.message.reply_document, text_function=update.message.reply_text
		)
		recognized_text = " ".join(transcription_list)
		await send_long_message(recognized_text, update.message.reply_text)
		os.remove(wav_converted_file_path)
		await update.message.reply_text("end transcribe_groq")
	else:
		await update.message.reply_text("unsupported mime type: " + str(mime_type))
		logger.error("unsupported mime type: " + str(mime_type))
