import time
from datetime import datetime

import pandas as pd
import speech_recognition as sr
from pydub import AudioSegment
from quarter_lib.logging import setup_logging
from telegram import Update

from src.helper.file_helper import delete_files
from src.helper.telegram_helper import retry_on_error
from src.services.logging_service import log_to_telegram
from src.services.microsoft_service import download_file_from_path
from src.services.todoist_service import add_file_to_todoist
from src.services.transcriber_service import audio_to_text

logger = setup_logging(__file__)


def get_title_and_author(caption):
	combined = caption[11:][:-19].split("/")
	return combined[1], combined[0]


async def get_bookmark_transcriptions(xml_data, caption, update: Update):
	r = sr.Recognizer()

	result_list = []
	to_delete = []
	df = pd.DataFrame(xml_data)
	for file_name, group in df.groupby("fileName"):
		await log_to_telegram("start downloading and processing of file: " + file_name, logger, update)
		download_file_from_path(
			"Musik/Hörbücher/" + caption[11:][:-19] + "/" + file_name + ":/content",
			file_name,
		)
		logger.info(f"downloaded file '{file_name}' - start conversion")
		sound = AudioSegment.from_file(file_name)
		logger.info(f"converted file '{file_name}' - start reading and transcriptions")
		for row_index, row in group.iterrows():
			file_position = int(row["filePosition"])
			duration_in_seconds = len(sound) / 1000
			logger.info("extracting audio segment from file: " + file_name + " at position: " + str(file_position))
			if file_position < 5:
				temp_sound = sound[: (file_position + 5) * 1000]
			elif file_position > duration_in_seconds - 5:
				temp_sound = sound[(file_position - 5) * 1000 :]
			else:
				temp_sound = sound[(file_position - 5) * 1000 : (file_position + 5) * 1000]

			temp_file_name = f"{file_name[:-4]}-{file_position!s}.mp3"
			temp_sound.export(temp_file_name, format="wav")
			await retry_on_error(
				update.message.reply_document,
				retry=5,
				wait=0.1,
				document=open(temp_file_name, "rb"),
				caption=temp_file_name,
				disable_notification=True,
			)
			upload_result = await add_file_to_todoist(temp_file_name)
			logger.info(f"uploaded file '{temp_file_name}' to todoist")
			r_file = sr.AudioFile(temp_file_name)
			with r_file as source:
				audio = r.record(source)

			logger.info("transcribing audio segment from file: " + file_name + " at position: " + str(file_position) + " in de-DE & en-US")

			recognized_text_de, recognized_text_en = audio_to_text(audio)

			await retry_on_error(
				update.message.reply_text,
				retry=5,
				wait=0.1,
				text=f"de: {recognized_text_de['transcript']} ({recognized_text_de['confidence']})\n en: {recognized_text_en['transcript']} ({recognized_text_en['confidence']})",
				disable_notification=True,
			)

			if "title" in row.keys() and row["title"] is not None:
				result_timestamp = datetime.strptime(row["title"], "%Y-%m-%dT%H:%M:%S%z")
			else:
				result_timestamp = None
			if "description" in row.keys() and row["description"] is not None:
				result_annotation = row["description"]
			else:
				result_annotation = None

			result_list.append(
				{
					"title": temp_file_name,
					"file_name": file_name,
					"file_position": file_position,
					"de": recognized_text_de["transcript"],
					"de_confidence": recognized_text_de["confidence"],
					"en": recognized_text_en["transcript"],
					"en_confidence": recognized_text_en["confidence"],
					"temp_file_path": temp_file_name,
					"timestamp": result_timestamp,
					"annotation": result_annotation,
					"upload_result": upload_result,
				},
			)
			to_delete.append(temp_file_name)
			time.sleep(3)
		time.sleep(3)
		to_delete.append(file_name)
	title, author = get_title_and_author(caption)
	delete_files(to_delete)
	message = f"finished processing {len(df)} files from {title} by {author} and extracted {len(result_list)} transcriptions"
	await log_to_telegram(message, logger, update)
	return result_list, title, author
