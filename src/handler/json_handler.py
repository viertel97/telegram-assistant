import json
import os
from datetime import datetime

from quarter_lib.logging import setup_logging

from src.services.book_note_service import add_tasks, get_tasks, read_markdown
from src.services.github_service import add_files_to_repository
from src.services.json_service import export_to_obsidian
from src.services.logging_service import log_to_telegram

logger = setup_logging(__file__)


async def handle_json(file_path, _, update):
	logger.info("start handle_json")
	now = update.message.date
	with open(file_path, "r", encoding="utf-8") as f:
		data = json.load(f)
	data = data[0]
	messages = data.pop("mapping")
	del_keys = []
	for key in messages.keys():
		if (
			messages[key]["message"] is None
			or messages[key]["message"]["content"] is None
			or messages[key]["message"]["content"]["parts"] == [""]
		):
			del_keys.append(key)
	for key in del_keys:
		del messages[key]
	messages = list(messages.values())
	messages = [message["message"] for message in messages]
	# messages = sorted(messages, key=lambda x: x["create_time"]) # sort by create_time doesn't work, because the dates from the exporter are not correct


	max_date = max(message["create_time"] for message in messages)
	last_update_time = datetime.fromtimestamp(max_date)

	file = {
		"filename": f"{last_update_time.strftime('%Y-%m-%d')}-{data['title']}.md",
		"content": export_to_obsidian(messages, data),
	}

	add_files_to_repository(
		[file],
		f"telegram-assistant: {now}",
		f"0200_Sources/ChatGPT/{now.strftime('%Y')}/{now.strftime('%m-%B')}/",
	)

	return f"{file['filename']} was added to Obsidian in path 0200_Sources/ChatGPT/{now.strftime('%Y')}/{now.strftime('%m-%B')}/"