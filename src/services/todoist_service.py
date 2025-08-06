import uuid
from datetime import datetime, timedelta
from typing import Dict
from urllib.parse import urljoin

import requests
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging
from quarter_lib_old.todoist import (
	add_note_with_attachement,
	get_items_by_label,
	get_items_by_project,
	get_user_state,
	move_item_to_project,
	run_sync_commands,
	update_due,
	upload_file,
)
from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Task


AUTHORIZATION = ("Authorization", "Bearer %s")


def create_headers(
	token: str | None = None,
) -> Dict[str, str]:
	headers: Dict[str, str] = {}

	if token:
		headers.update([(AUTHORIZATION[0], AUTHORIZATION[1] % token)])

	return headers

logger = setup_logging(__file__)
TODOIST_TOKEN = get_secrets("todoist/token")
TODOIST_API = TodoistAPI(TODOIST_TOKEN)
HEADERS = create_headers(token=TODOIST_TOKEN)
COMPLETE_TASKS_LIMIT = 200





BASE_URL = "https://api.todoist.com"
SYNC_VERSION = "v9"
SYNC_API = urljoin(BASE_URL, f"/sync/{SYNC_VERSION}/")

def get_sync_url(relative_path: str) -> str:
	return urljoin(SYNC_API, relative_path)


def run_todoist_sync_commands(commands):
	for command in commands:
		command["uuid"] = str(uuid.uuid4())
		if not command.get("temp_id"):
			command["temp_id"] = str(uuid.uuid4())
	logger.info(f"Running {len(commands)} commands: {commands}")
	return run_sync_commands(commands)


def add_to_todoist(text, project_id=None, labels=None) -> Task:
	item = TODOIST_API.add_task(text, labels=labels)
	if project_id:
		move_item_to_project(item.id, project_id)
	return item


def add_comment_to_task(task_id, comment):
	return TODOIST_API.add_comment(task_id=task_id, content=comment)


def add_to_todoist_with_description(text, description, project_id=None):
	item = TODOIST_API.add_task(
		content=text,
		description=description,
	)
	if project_id:
		move_item_to_project(item.id, project_id=project_id)
	return item


async def add_to_todoist_with_file(final_message, file_path, project_id=None, description=None, labels=None):
	item = TODOIST_API.add_task(final_message, project_id=project_id, description=description, labels=labels)
	add_note_with_attachement(task_id=item.id, file_path=file_path)


async def add_file_to_todoist(file_path):
	return upload_file(file_path=file_path)


def get_default_offset():
	tz_info = get_user_state()
	delta = timedelta(hours=tz_info["hours"], minutes=tz_info["minutes"])
	return delta, tz_info["gmt_string"]


def get_default_offset_including_check(default):
	tz_info = get_user_state()
	delta = timedelta(hours=tz_info["hours"], minutes=tz_info["minutes"])
	return delta == default, delta, tz_info["gmt_string"]


def update_due_date(task_id, due, add_reminder=False):
	return update_due(task_id, due, add_reminder=add_reminder)


def get_items_by_todoist_label(label_id):
	return get_items_by_label(label_id)



def get_items_by_todoist_project(project_id):
	paginated_items = TODOIST_API.get_tasks(project_id=project_id)
	return [item for page in paginated_items for item in page if item.is_completed == False]


def update_content(task_id, content):
	return TODOIST_API.update_task(task_id, content=content)


async def update_description(task_id, description):
	return TODOIST_API.update_task(task_id, description=description)


def get_rework_projects(project_name_start_with):
	projects = TODOIST_API.get_projects()
	rework_projects = []
	for paginated_projects in projects:
		for project in paginated_projects:
			if project.name.startswith(project_name_start_with):
				rework_projects.append(project)
	return rework_projects


def get_completed_tasks(since: datetime):
	return list(TODOIST_API.get_completed_tasks_by_completion_date(since=since, until=datetime.now()))
