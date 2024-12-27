import uuid
from datetime import timedelta

import requests
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging
from quarter_lib_old.todoist import (
    add_note_with_attachement,
    get_user_state,
    move_item_to_project,
    run_sync_commands,
    update_due,
    upload_file,
    get_items_by_project,
    get_items_by_label,
)
from todoist_api_python.api import TodoistAPI
from todoist_api_python.endpoints import get_sync_url
from todoist_api_python.headers import create_headers

logger = setup_logging(__file__)
TODOIST_TOKEN = get_secrets("todoist/token")
TODOIST_API = TodoistAPI(TODOIST_TOKEN)
HEADERS = create_headers(token=TODOIST_TOKEN)


def run_todoist_sync_commands(commands):
    for command in commands:
        command["uuid"] = str(uuid.uuid4())
        if not command.get("temp_id"):
            command["temp_id"] = str(uuid.uuid4())
    return run_sync_commands(commands)


def add_to_todoist(text, project_id=None):
    item = TODOIST_API.add_task(text)
    if project_id:
        move_item_to_project(item.id, project_id)


def add_to_todoist_with_description(text, description, project_id=None):
    item = TODOIST_API.add_task(
        text,
        description=description,
    )
    if project_id:
        move_item_to_project(item.id, project_id=project_id)


async def add_to_todoist_with_file(final_message, file_path, project_id=None):
    item = TODOIST_API.add_task(final_message, project_id=project_id)
    temp = add_note_with_attachement(task_id=item.id, file_path=file_path)


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
    return get_items_by_project(project_id)


def update_content(task_id, content):
    return TODOIST_API.update_task(task_id, content=content)


async def update_description(task_id, description):
    return TODOIST_API.update_task(task_id, description=description)


def get_rework_projects(project_name_start_with):
    projects = TODOIST_API.get_projects()
    rework_projects = []
    for project in projects:
        if project.name.startswith(project_name_start_with):
            rework_projects.append(project)
    return rework_projects


def get_completed_tasks(since):
    response = requests.post(
        get_sync_url("completed/get_all"),
        data={
            "annotate_notes": True,
            "annotate_items": True,
            "since": since.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        headers=HEADERS,
    ).json()
    response["items"] = [
        {
            k: v
            for k, v in item.items()
            if k
            not in [
                "completed_at",
                "content",
                "id",
                "project_id",
                "section_id",
                "user_id",
                "v2_project_id",
                "v2_section_id",
            ]
        }
        for item in response["items"]
    ]
    return response
