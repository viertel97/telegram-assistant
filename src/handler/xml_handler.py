import uuid
from json import dumps

from quarter_lib.logging import setup_logging
from telegram import Update

from src.services.book_note_service import get_smallest_project
from src.services.bookmark_service import get_bookmark_transcriptions
from src.services.logging_service import log_to_telegram
from src.services.todoist_service import run_todoist_sync_commands
from src.services.xml_service import xml_to_dict

logger = setup_logging(__file__)


async def handle_xml(file_path, file_name, update: Update):
	xml = open(file_path, encoding="utf-8").read()  # Read file
	xml_dict = await xml_to_dict(xml, update)
	transcribed_bookmarks, title, author = await get_bookmark_transcriptions(xml_dict, update.message.caption, update)

	project, min_size, idx = get_smallest_project("Book-Notes")
	await log_to_telegram(
		f"List {idx + 1} ({project.id}) was chosen as the smallest project with {min_size} items",
		logger,
		update,
	)

	command_list = []
	for transcribed_bookmark in transcribed_bookmarks:
		content = transcribed_bookmark["title"] + " - add highlight to Zotero"

		if "timestamp" in transcribed_bookmark and transcribed_bookmark["timestamp"] is not None:
			recording_timestamp = transcribed_bookmark["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
		else:
			recording_timestamp = None
		description_dict = {
			"recognized_text_de": transcribed_bookmark["de"],
			"recognized_text_en": transcribed_bookmark["en"],
			"recording_timestamp": recording_timestamp,
			"author": author,
			"title": title,
			"file_name": file_name,
			"file_position": transcribed_bookmark["file_position"],
			"annotation": transcribed_bookmark["annotation"],
		}
		desc = dumps(description_dict, indent=4, sort_keys=True, ensure_ascii=False).encode("utf8").decode()
		generated_temp_id = "_" + str(uuid.uuid4())
		command_list.append(
			{
				"type": "item_add",
				"temp_id": generated_temp_id,
				"args": {
					"content": content,
					"description": desc,
					"project_id": project.id,
				},
			},
		)
		command_list.append(
			{
				"type": "note_add",
				"args": {
					"content": "",
					"item_id": generated_temp_id,
					"file_attachment": {
						"file_name": transcribed_bookmark["upload_result"]["file_name"],
						"file_size": transcribed_bookmark["upload_result"]["file_size"],
						"file_type": transcribed_bookmark["upload_result"]["file_type"],
						"file_url": transcribed_bookmark["upload_result"]["file_url"],
					},
				},
			},
		)

	sync_command_results = run_todoist_sync_commands(command_list)
	if sync_command_results.status_code != 200:
		logger.error("Error while adding to Todoist")
		raise Exception("Error while adding to Todoist " + sync_command_results.text)
	logger.info(sync_command_results)
	message = f"Transcribed {len(transcribed_bookmarks)} bookmarks for {title} by {author}" + " and added them to Todoist"

	logger.info(message)
	return message
