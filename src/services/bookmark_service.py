import time
from datetime import datetime
import json
import pandas as pd
import speech_recognition as sr
from pydub import AudioSegment
from quarter_lib.logging import setup_logging
from telegram import Update

from src.helper.file_helper import delete_files
from src.helper.telegram_helper import retry_on_error
from src.services.groq_service import transcribe_groq
from src.services.logging_service import log_to_telegram
from src.services.microsoft_service import download_file_from_path
from src.services.todoist_service import add_file_to_todoist
from src.services.transcriber_service import audio_to_text

logger = setup_logging(__file__)


def get_title_and_author(caption):
	combined = caption[11:][:-19].split("/")
	return combined[1], combined[0]

def prepare_bookmark_transcriptions(xml_data, caption):
	result_list = []
	df = pd.DataFrame(xml_data)
	for file_name, group in df.groupby("fileName"):
		for row_index, row in group.iterrows():
			file_position = int(row["filePosition"])
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
					"file_name": file_name,
					"file_position": file_position,
					"timestamp": result_timestamp,
					"annotation": result_annotation,
				},
			)
	title, author = get_title_and_author(caption)
	return result_list, title, author


async def get_bookmark_transcriptions(prepared_bookmarks:list, caption: str, title:str, author:str, update: Update) -> list[dict]:
	to_delete = []

	df = pd.DataFrame(prepared_bookmarks)
	final_bookmarks = []

	for file_name, group in df.groupby("file_name"):
		await log_to_telegram("start downloading and processing of file: " + file_name, logger, update)
		download_file_from_path(
			"Musik/Hörbücher/" + caption[11:][:-19] + "/" + file_name + ":/content",
			file_name,
		)
		logger.info(f"downloaded file '{file_name}' - start conversion")
		sound = AudioSegment.from_file(file_name)
		logger.info(f"converted file '{file_name}' - start reading and transcriptions")
		for row_index, row in group.iterrows():
			file_position = int(row["file_position"])
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

			logger.info("transcribing audio segment from file: " + file_name + " at position: " + str(file_position) + " in de-DE & en-US")

			transcription_list = await transcribe_groq(
				temp_file_name,
				file_function=update.message.reply_document,
				text_function=update.message.reply_text,
			)
			recognized_text = "".join(transcription_list).strip()

			final_bookmarks.append(
				{
					"title": title,
					"file_name": file_name,
					"file_position": file_position,
					"de": recognized_text,
					"en": recognized_text,
					"temp_file_path": temp_file_name,
					"timestamp": row["timestamp"],
					"annotation": row["annotation"],
					"upload_result": upload_result,
				})

			to_delete.append(temp_file_name)
			time.sleep(3)
		time.sleep(3)
		to_delete.append(file_name)
	delete_files(to_delete)
	message = f"finished processing {len(prepared_bookmarks)} files from {title} by {author}"
	await log_to_telegram(message, logger, update)
	return final_bookmarks


def remove_duplicated_bookmarks(prepared_bookmarks, tasks, title, author) -> list[dict]:
	df = pd.DataFrame(tasks)
	if not df.empty and 'description' in df.columns:
		description_data = []
		for desc in df['description']:
			try:
				if desc:
					parsed = json.loads(desc)
					description_data.append(parsed)
				else:
					description_data.append({})
			except (json.JSONDecodeError, TypeError):
				description_data.append({})

		desc_df = pd.json_normalize(description_data)
		df = pd.concat([df.drop('description', axis=1), desc_df], axis=1)

		df = df.loc[:,~df.columns.duplicated()]

	de_duplicated_bookmarks = []
	for bookmark in prepared_bookmarks:
		is_duplicate = (
			(df['file_name'] == bookmark['file_name']) &
			(df['file_position'] == bookmark['file_position']) &
			(df['title'] == title) &
			(df['author'] == author)
		).any()

		if not is_duplicate:
			de_duplicated_bookmarks.append(bookmark)
		else:
			logger.info(
				f"Skipping duplicate bookmark at position {bookmark['file_position']} "
				f"in file {bookmark['file_name']}"
			)
	return de_duplicated_bookmarks
