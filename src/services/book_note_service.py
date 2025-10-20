import time

from datetime import datetime
import markdown
from bs4 import BeautifulSoup
from quarter_lib.logging import setup_logging

from src.services.logging_service import log_to_telegram
from src.services.todoist_service import (
	get_items_by_todoist_project,
	get_rework_projects,
	run_todoist_sync_commands,
)

logger = setup_logging(__file__)

OBSIDIAN_AUTOSTART_TRIGGER = "Obsidian-Eintrag überdenken"

NUMBER_OF_ITEMS_PER_CHUNK = 40


def read_markdown(file_path):
	with open(file_path, encoding="utf-8") as f:
		text = f.read()
		date = datetime.today().strftime("%Y-%m-%d")
		text = text.replace("- [ ] ", "").replace(f" ➕ {date}", "")
		html = markdown.markdown(text)
	return BeautifulSoup(html, "html.parser")


def get_tasks(soup, file_name):
	for child in soup.find_all("h1"):
		if child.text == "Annotations":
			start_element = child
	if not start_element:
		return [], "No annotations found", file_name
	lines = [child for child in start_element.next_siblings if child != "\n"]
	tasks = []
	for idx, child in enumerate(lines):
		if not (idx + 1 < len(lines) and lines[idx + 1].name != "blockquote" and child.name == "blockquote"):
			tasks.append(paragraph_to_task(child, title=file_name))
		else:
			tasks.append(
				paragraph_to_task(
					child.previous_sibling.previous_sibling,
					comment=child.next_element.next_element.text,
					title=file_name,
				),
			)
	return (
		tasks,
		len(tasks),
		len([task for task in tasks if type(task) == tuple]),
		file_name,
	)


def paragraph_to_task(paragraph, title, comment=None):
	text = ""
	for child in paragraph.contents:
		if child.name != "a":
			text += child.text
		else:
			text += "[{text}]({link})".format(text=child.text, link=child["href"])
	text = f"{text} - {title} - {OBSIDIAN_AUTOSTART_TRIGGER}"
	if comment:
		return text, comment
	return text


def get_smallest_project(project_name_start_with):
	logger.info("getting smallest project")
	rework_projects = get_rework_projects(project_name_start_with)
	project_sizes = [len(get_items_by_todoist_project(project.id)) for project in rework_projects]
	min_size = min(project_sizes)
	idx = project_sizes.index(min_size)
	return rework_projects[idx], min_size, idx


def split_str_to_chars(text, chars=2047):
	return [text[i : i + chars] for i in range(0, len(text), chars)][0]


async def add_tasks(tasks, message, update):
	project, min_size, idx = get_smallest_project("Book-Rework")
	await log_to_telegram(
		f"List {idx + 1} ({project.id}) was chosen as the smallest project with {min_size} items",
		logger,
		update,
	)
	if min_size + len(tasks) <= 300:
		command_list = []
		for task in tasks:
			if type(task) == tuple:
				temp_task = list(task)
				temp_task[0] = split_str_to_chars(temp_task[0])
				command_list.append(
					{
						"type": "item_add",
						"args": {
							"content": temp_task[0],
							"description": temp_task[1],
							"project_id": project.id,
						},
					},
				)
			else:
				task = split_str_to_chars(task)
				command_list.append(
					{
						"type": "item_add",
						"args": {"content": task, "project_id": project.id},
					},
				)
		logger.info(f"adding batch of {len(command_list)} tasks")
		chunks_of_40 = list(chunks(command_list, NUMBER_OF_ITEMS_PER_CHUNK))
		for chunk in chunks_of_40:
			logger.info(f"adding chunk of {len(chunk)} tasks")
			response = run_todoist_sync_commands(chunk)
			logger.info(f"response code {response.status_code}")
			if response.status_code != 200:
				logger.error(f"response body {response.text}")
				raise Exception("Error while adding to Todoist " + response.text)
			logger.info(f"response:\n{response.json()}")
			await log_to_telegram(f"Added {len(chunk)} tasks", logger, update)
			if len(chunk) == NUMBER_OF_ITEMS_PER_CHUNK:
				logger.info("sleeping for 10 seconds")
				time.sleep(10)
	else:
		error_message = f"Project {project.id} is full and cannot handle {len(tasks)} more tasks"
		await log_to_telegram(error_message, logger, update)
		raise Exception(error_message)


def chunks(lst, n):
	for i in range(0, len(lst), n):
		yield lst[i : i + n]
