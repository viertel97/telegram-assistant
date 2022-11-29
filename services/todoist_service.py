import os
import uuid
from datetime import timedelta

from loguru import logger
from quarter_lib.todoist import (
    add_note_with_attachement,
    add_reminder,
    get_user_state,
    move_item_to_project,
    run_sync_commands,
    update_due,
    upload_file,
)
from todoist_api_python.api import TodoistAPI

TODOIST_API = TodoistAPI(os.environ["TODOIST_TOKEN"])

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def run_todoist_sync_commands(commands):
    for command in commands:
        command["uuid"] = str(uuid.uuid4())
        command["temp_id"] = (str(uuid.uuid4()),)
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


async def add_to_todoist_with_file(final_message, file_path):
    item = TODOIST_API.add_task(final_message)
    add_note_with_attachement(task_id=item.id, file_path=file_path)


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
