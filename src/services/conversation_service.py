import os

from dateutil import parser
from datetime import datetime, timedelta
from quarter_lib.logging import setup_logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from src.handler.text_handler import extract_info
from src.helper.config_helper import is_not_correct_chat_id
from src.helper.telegram_helper import send_long_message
from src.services.groq_service import transcribe_groq
from src.services.microsoft_service import (
	download_file_by_id,
	get_access_token,
	get_file_list,
)
from src.services.todoist_service import add_comment_to_task, add_to_todoist, add_to_todoist_with_description

MAX_COMMENT_LENGTH = 14000
MAX_DESCRIPTION_LENGTH = 16000

logger = setup_logging(__file__)


async def get_last_calls(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return

	skip_entries = int(context.args[0]) if context.args else 0

	access_token = get_access_token()


	files = []

	now = datetime.now()
	if now.month == 1:
		last_month = now.replace(year=now.year - 1, month=12)
	else:
		last_month = now.replace(month=now.month - 1)

	files_this_month, destination_folder_id = get_file_list(f"Anwendungen/Call Recorder - SKVALEX/{now.strftime('%Y')}/{now.strftime('%m')}", access_token)
	files.extend(files_this_month)
	files_last_month, destination_folder_id = get_file_list(f"Anwendungen/Call Recorder - SKVALEX/{last_month.strftime('%Y')}/{last_month.strftime('%m')}", access_token)
	files.extend(files_last_month)

	files = [file for file in files if "@microsoft.graph.downloadUrl" in file.keys()]
	for file in files:
		file["info"] = extract_info(file["name"])
		file["sortCreatedDatetime"] = file["info"]["date"]
		if file["info"]["contact_name"]:
			file["readable"] = (
				f"{file['sortCreatedDatetime'].strftime('%d.%m.%Y %H:%M:%S')} - {file['info']['contact_name']} ({file['info']['call_type']})"
			)
		else:
			file["readable"] = (
				f"{file['sortCreatedDatetime'].strftime('%d.%m.%Y %H:%M:%S')} - {file['info']['contact_number']} ({file['info']['call_type']})"
			)

	files = sorted(files, key=lambda x: x["sortCreatedDatetime"], reverse=True)

	reply_keyboard = [[InlineKeyboardButton(file["readable"], callback_data=str(file["id"]))] for file in files[skip_entries : skip_entries + 20]]
	reply_markup = InlineKeyboardMarkup(reply_keyboard)

	await update.message.reply_text("Please choose:", reply_markup=reply_markup)


async def transcribe_call_from_one_drive(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.callback_query.message.chat_id):
		await update.message.reply_text("Nah")
		return
	logger.info("start: Call to text")
	query = update.callback_query
	file_id = query.data

	await query.answer()

	data = dict()
	for inline_keyboard in query.message.reply_markup.inline_keyboard:
		if inline_keyboard[0].callback_data == file_id:
			data.update({"id": file_id, "name": inline_keyboard[0].text})

	await query.edit_message_text(text=f"Selected option: {data['name']} ({data['id']})")

	await context.bot.send_message(
		chat_id=update.effective_chat.id,
		text=f"Downloading file {data['name']} and start transcribing",
	)
	download_file_by_id(data["id"], "input.wav")

	transcription_list = await transcribe_groq(
		"input.wav",
		file_function=context.bot.send_document,
		text_function=context.bot.send_message,
		prompt="Do not translate to another language",
		chat_id=update.effective_chat.id,
	)
	content = " ".join(transcription_list)

	await send_long_message(content, context.bot.send_message, chat_id=update.effective_chat.id)

	await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Done transcribing of {data['name']}")

	if len(content) > MAX_DESCRIPTION_LENGTH:
		item = add_to_todoist(f"Transcribe {data['name']}", labels=["filtered"])
		chunks = [content[i : i + MAX_COMMENT_LENGTH] for i in range(0, len(content), MAX_COMMENT_LENGTH)]
		for chunk in chunks:
			add_comment_to_task(item.id, chunk)

	else:
		add_to_todoist_with_description(f"Transcribe {data['name']}", content)

	await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Added to Todoist")
	os.remove("input.wav")
