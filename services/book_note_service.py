import time

import markdown
from bs4 import BeautifulSoup
from quarter_lib.logging import setup_logging

from services.logging_service import log_to_telegram
from services.todoist_service import (
    run_todoist_sync_commands,
    get_items_by_todoist_project,
    get_rework_projects,
)

logger = setup_logging(__file__)

OBSIDIAN_AUTOSTART_TRIGGER = "Obsidian-Eintrag überdenken"

NUMBER_OF_ITEMS_PER_CHUNK = 40


def read_markdown(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
        html = markdown.markdown(text)
    return BeautifulSoup(html, "html.parser")


def get_tasks(soup, file_name):
    for child in soup.find_all("h1"):
        if child.text == "Annotations":
            start_element = child
    if not start_element:
        return [], "No annotations found", file_name
    else:
        lines = [child for child in start_element.next_siblings if child != "\n"]
        tasks = []
        for idx, child in enumerate(lines):
            if not (
                idx + 1 < len(lines)
                and lines[idx + 1].name != "blockquote"
                and child.name == "blockquote"
            ):
                tasks.append(paragraph_to_task(child, title=file_name))
            else:
                tasks.append(
                    paragraph_to_task(
                        child.previous_sibling.previous_sibling,
                        comment=child.next_element.next_element.text,
                        title=file_name,
                    )
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
    text = "{text} - {title} - {trigger}".format(
        text=text, title=title, trigger=OBSIDIAN_AUTOSTART_TRIGGER
    )
    if comment:
        return text, comment
    else:
        return text


def get_smallest_project(project_name_start_with):
    rework_projects = get_rework_projects(project_name_start_with)
    project_sizes = [
        len(get_items_by_todoist_project(project.id)) for project in rework_projects
    ]
    min_size = min(project_sizes)
    idx = project_sizes.index(min_size)
    return rework_projects[idx], min_size, idx


def split_str_to_chars(text, chars=2047):
    return [text[i : i + chars] for i in range(0, len(text), chars)][0]


async def add_tasks(tasks, message, update):
    project, min_size, idx = get_smallest_project("Book-Rework")
    await log_to_telegram(
        "List {idx} ({project_id}) was chosen as the smallest project with {min_size} items".format(
            idx=idx + 1, project_id=project.id, min_size=min_size
        ),
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
                    }
                )
            else:
                task = split_str_to_chars(task)
                command_list.append(
                    {
                        "type": "item_add",
                        "args": {"content": task, "project_id": project.id},
                    }
                )
        logger.info("adding batch of {len} tasks".format(len=len(command_list)))
        chunks_of_40 = list(chunks(command_list, NUMBER_OF_ITEMS_PER_CHUNK))
        for chunk in chunks_of_40:
            logger.info("adding chunk of {len} tasks".format(len=len(chunk)))
            response = run_todoist_sync_commands(chunk)
            logger.info("response code {code}".format(code=response.status_code))
            if response.status_code != 200:
                logger.error("response body {body}".format(body=response.text))
                raise Exception("Error while adding to Todoist " + response.text)
            else:
                logger.info("response:\n{response}".format(response=response.json()))
                await log_to_telegram(
                    "Added {len} tasks".format(len=len(chunk)), logger, update
                )
            if len(chunk) == NUMBER_OF_ITEMS_PER_CHUNK:
                logger.info("sleeping for 10 seconds")
                time.sleep(10)
    else:
        error_message = (
            "Project {project_id} is full and cannot handle {len} more tasks".format(
                project_id=project.id, len=len(tasks)
            )
        )
        await log_to_telegram(error_message, logger, update)
        raise Exception(error_message)


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
