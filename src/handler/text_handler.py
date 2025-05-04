import os
import re
from datetime import datetime

import requests
from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import CallbackContext

from src.helper.config_helper import is_not_correct_chat_id
from src.helper.telegram_helper import retry_on_error, send_long_message
from src.services.groq_service import transcribe_groq
from src.services.microsoft_service import get_access_token, get_file_list

logger = setup_logging(__file__)


async def handle_text(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return
	await update.message.reply_text("start handle_text")
	await handle_transcription(update, context)

async def handle_transcription(update: Update, context: CallbackContext):
	try:
		file_info = extract_info(update.message.text)
		await retry_on_error(update.message.reply_text, retry=5, wait=0.1, text=str(file_info))
	except Exception as e:
		logger.error(e)
		await retry_on_error(update.message.reply_text, retry=5, wait=0.1, text=str(e))
		return
	token = get_access_token()
	files, destination_folder_id = get_file_list("Anwendungen/Call Recorder - SKVALEX", token)
	file_info["file"] = find_file(files, file_info["file_name"])
	if not file_info["file"]:
		await retry_on_error(update.message.reply_text, retry=5, wait=0.1, text="File not found")
		return
	await retry_on_error(update.message.reply_text, retry=5, wait=0.1, text="File found")
	with open("input.wav", "wb") as f:
		f.write(requests.get(file_info["file"]["@microsoft.graph.downloadUrl"]).content)
		await retry_on_error(
			update.message.reply_text,
			retry=5,
			wait=0.1,
			text="done downloading - start transcribing",
		)
	# await transcribe(f, file_info, update)
	transcription_list = await transcribe_groq(
		"input.wav", file_function=update.message.reply_document, text_function=update.message.reply_text
	)
	recognized_text = " ".join(transcription_list)
	await send_long_message(recognized_text, update.message.reply_text)
	await update.message.reply_text("done transcribing of " + file_info["file"]["name"])
	os.remove("input.wav")

def find_file(file_list, file_name):
	for file in file_list:
		if "@microsoft.graph.downloadUrl" in file.keys():
			if file_name in file["name"]:
				return file
	return None


def extract_info(log_string):
	# Extract date (first 12 digits)
	date_str = log_string[:12]
	if "@" in log_string:
		filename = log_string.split("@")[0]
		segment_counter = int(log_string.split("@")[1])
	else:
		filename = log_string
		segment_counter = 1
	date = datetime.strptime(date_str, "%Y%m%d%H%M")

	# Extract incoming/outgoing type
	call_type = "outgoing" if "outgoing" in log_string else "incoming"

	# Extract contact name (inside first set of brackets)
	name_match = re.search(r"\[(.*?)\]", log_string)
	contact_name = name_match.group(1) if name_match else None

	# Extract contact number (inside second set of brackets)
	number_match = re.findall(r"\[(.*?)\]", log_string)
	contact_number = number_match[-1] if len(number_match) > 1 else None

	return {
		"date": date,
		"call_type": call_type,
		"contact_name": contact_name,
		"contact_number": contact_number,
		"segment_counter": segment_counter,
		"file_name": filename,
	}
