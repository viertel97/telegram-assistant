import os

from quarter_lib.logging import setup_logging
from quarter_lib_old.transcriber import convert_to_wav
from telegram import Update
from telegram.ext import CallbackContext

from src.handler.excel_handler import handle_excel
from src.handler.markdown_handler import handle_markdown
from src.handler.pdf_handler import handle_pdf
from src.handler.xml_handler import handle_xml
from src.handler.zip_handler import handle_zip
from src.helper.config_helper import is_not_correct_chat_id
from src.helper.handler_helper import prepairing_document
from src.helper.telegram_helper import send_long_message
from src.services.groq_service import transcribe_groq
from src.services.todoist_service import add_to_todoist_with_file

logger = setup_logging(__file__)


async def handle_document(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return
	await update.message.reply_text("start handle_document")
	mime_type = update.message.document.mime_type
	if not mime_type:
		if update.message.document.file_name.endswith(".md"):
			mime_type = "text/markdown"
	if not mime_type:
		await update.message.reply_text("couldnt determine mime type")
		return
	logger.info("received: " + mime_type)
	await update.message.reply_text("received: " + mime_type)
	file_path, file_name = await prepairing_document(update, context)
	if mime_type == "text/comma-separated-values":
		await update.message.reply_text("start handle_excel")
		await handle_excel(file_path, file_name, update)
	elif mime_type == "application/zip":
		await update.message.reply_text("start handle_zip")
		done_message = await handle_zip(file_path, file_name, update)
		await update.message.reply_text(done_message)
	elif mime_type == "text/markdown":
		await update.message.reply_text("start handle_markdown")
		await handle_markdown(file_path, file_name, update)
	elif mime_type == "text/xml" or mime_type == "application/xml":
		await update.message.reply_text("start handle_xml")
		done_message = await handle_xml(file_path, file_name, update)
		await update.message.reply_text(done_message)
	elif mime_type == "application/pdf":
		await update.message.reply_text("start handle_pdf")
		await handle_pdf(file_path, file_name, update)
	elif mime_type == "audio/ogg":
		wav_converted_file_path = convert_to_wav(file_path)
		transcription_list = await transcribe_groq(wav_converted_file_path,
												   file_function=update.message.reply_document,
												   text_function=update.message.reply_text)
		recognized_text = " ".join(transcription_list)
		await send_long_message(recognized_text, update.message.reply_text)
		await add_to_todoist_with_file(f"{update.message.document.file_name} transcription", file_path=wav_converted_file_path,description=recognized_text, labels=["transcription", "filtered"])
		os.remove(wav_converted_file_path)
	else:
		logger.error("unsupported mime type: " + mime_type)
		await update.message.reply_text("unsupported mime type: " + mime_type)
	await update.message.reply_text("done handle_document")
