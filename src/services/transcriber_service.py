import os
import subprocess
import sys
from datetime import datetime, timedelta

import speech_recognition as sr
from quarter_lib.logging import setup_logging
from quarter_lib_old.file_helper import delete_files
from quarter_lib_old.transcriber import convert_to_wav
from telegram import Update
from telegram.ext import CallbackContext

from src.helper.config_helper import is_not_correct_chat_id
from src.services.groq_service import transcribe_groq
from src.services.todoist_service import (
	TODOIST_API,
	add_to_todoist_with_file,
	update_due_date,
)

logger = setup_logging(__file__)

r = sr.Recognizer()

FILENAME = "temp.mp4"


async def transcribe_video(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return
	logger.info("start: Video to text")
	file_id = update.message.video.file_id
	file = await context.bot.get_file(file_id)
	file_path = os.path.join(sys.path[0], FILENAME)
	await file.download(file_path)
	new_file_path = file_path + ".wav"
	wav_cmd = 'ffmpeg -y -i "' + file_path + '" -ar 48000 -ac 1 "' + new_file_path + '"'
	subprocess.call(wav_cmd, shell=True)
	r_file = sr.AudioFile(new_file_path)
	with r_file as source:
		audio = r.record(source)
	recognized_text_de, recognized_text_en = audio_to_text(audio)

	now = datetime.now()
	message = 'DE: "{recognized_text_de}" ({recognized_text_de_confidence}%) \n\nEN: "{recognized_text_en}" ({recognized_text_en_confidence}%) \n\non {date} at {time}\n\nin {audiobook} - add highlight to Zotero'.format(
		recognized_text_de=recognized_text_de["transcript"],
		recognized_text_de_confidence=recognized_text_de["confidence"],
		recognized_text_en=recognized_text_en["transcript"],
		recognized_text_en_confidence=recognized_text_en["confidence"],
		date=now.strftime("%d.%m.%Y"),
		time=now.strftime("%H:%M"),
		audiobook=update.message.caption,
	)
	await update.message.reply_text(message)
	due = {
		"date": (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
		"is_recurring": False,
		"lang": "en",
		"string": "tomorrow",
		"timezone": None,
	}
	item = TODOIST_API.add_task(message, project_id="2281154095", due_string="tomorrow")
	update_due_date(item.id, due=due, add_reminder=True)

	delete_files([file_path, new_file_path])
	logger.info("end: Video to text")


def audio_to_text(audio):
	recognized_alternatives_de = r.recognize_google(audio, language="de-DE", show_all=True)
	recognized_alternatives_en = r.recognize_google(audio, language="en-US", show_all=True)
	recognized_text_de = (
		{"transcript": "", "confidence": 0} if type(recognized_alternatives_de) is list else recognized_alternatives_de["alternative"][0]
	)
	recognized_text_en = (
		{"transcript": "", "confidence": 0} if type(recognized_alternatives_en) is list else recognized_alternatives_en["alternative"][0]
	)
	return recognized_text_de, recognized_text_en


async def transcribe_voice(update: Update, context: CallbackContext) -> None:
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return
	logger.info("start: Voice to text")
	file_id = update.message.voice.file_id
	file = await context.bot.get_file(file_id)
	file_path = os.path.join(sys.path[0], "voice.ogg")
	await file.download_to_drive(file_path)
	logger.info(file_path)

	modification_date = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%d.%m.%Y %H:%M")
	wav_converted_file_path = convert_to_wav(file_path)
	transcription_list = await transcribe_groq(
		wav_converted_file_path, file_function=update.message.reply_document, text_function=update.message.reply_text
	)
	recognized_text = " ".join(transcription_list)

	if "absatz" in recognized_text.lower():
		phrases = recognized_text.lower().split("absatz")
		for phrase in phrases:
			final_message = modification_date + " : " + phrase
			await update.message.reply_text(final_message)
			if "einkaufsliste" in phrase.lower():
				final_message = phrase.replace("Einkaufsliste", "").replace("auf", "").replace("der", "").replace(" ", "")
				await add_to_todoist_with_file(final_message, file_path, project_id="2247224944", labels=["transcription"])
			else:
				await add_to_todoist_with_file(final_message, file_path, labels=["transcription"])

	else:
		final_message = modification_date + " : " + recognized_text
		if "einkaufsliste" in recognized_text.lower():
			final_message = recognized_text.replace("Einkaufsliste", "").replace("auf", "").replace("der", "").replace(" ", "")
			await add_to_todoist_with_file(final_message, file_path, project_id="2247224944", labels=["transcription"])
		else:
			await add_to_todoist_with_file(final_message, file_path, labels=["transcription"])
		await update.message.reply_text(final_message)
	delete_files([file_path, wav_converted_file_path])
	logger.info("end: Voice to text")
