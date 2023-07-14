import time

import markdown
import requests
from bs4 import BeautifulSoup
from quarter_lib.logging import setup_logging

from helper.caching import ttl_cache
from services.todoist_service import run_todoist_sync_commands, get_items_by_todoist_project

logger = setup_logging(__file__)
PROJECT_IDS_URL = "https://viertel-it.de/files/rework_project_ids.json"

OBSIDIAN_AUTOSTART_TRIGGER = "Obsidian-Eintrag überdenken"

NUMBER_OF_ITEMS_PER_CHUNK = 40


@ttl_cache(ttl=60 * 60)
def get_ids_from_web():
    logger.info("getting ids from web")
    response = requests.get(PROJECT_IDS_URL, headers={'User-Agent': 'Mozilla/5.0'}, verify=False)
    data = response.json()
    return data


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
            if not (idx + 1 < len(lines) and lines[idx + 1].name != "blockquote" and child.name == "blockquote"):
                tasks.append(paragraph_to_task(child, title=file_name))
            else:
                tasks.append(
                    paragraph_to_task(
                        child.previous_sibling.previous_sibling,
                        comment=child.next_element.next_element.text,
                        title=file_name,
                    )
                )
        return tasks, "{len} annotations with {comments} comments were found in '{title}' and added to Todoist".format(
            len=len(tasks), comments=len([task for task in tasks if type(task) == tuple]), title=file_name
        )


def paragraph_to_task(paragraph, title, comment=None):
    text = ""
    for child in paragraph.contents:
        if child.name != "a":
            text += child.text
        else:
            text += "[{text}]({link})".format(text=child.text, link=child["href"])
    text = "{text} - {title} - {trigger}".format(text=text, title=title, trigger=OBSIDIAN_AUTOSTART_TRIGGER)
    if comment:
        return (text, comment)
    else:
        return text


def get_smallest_project():
    project_ids = get_ids_from_web()
    project_sizes = [len(get_items_by_todoist_project(project_id)) for project_id in project_ids]
    min_size = min(project_sizes)
    idx = project_sizes.index(min_size)
    return project_ids[idx], min_size, idx


def add_tasks(tasks, message):
    project_id, min_size, idx = get_smallest_project()
    message = "{message} - List {idx} ({project_id}) was chosen as the smallest project with {min_size} items".format(
        idx=idx + 1, message=message, project_id=project_id, min_size=min_size)
    if min_size + len(tasks) <= 300:
        command_list = []
        for task in tasks:
            if type(task) == tuple:
                command_list.append(
                    {
                        "type": "item_add",
                        "args": {"content": task[0], "description": task[1], "project_id": project_id},
                    }
                )
            else:
                command_list.append({"type": "item_add", "args": {"content": task, "project_id": project_id}})
        logger.info("adding batch of {len} tasks".format(len=len(command_list)))
        chunks_of_40 = list(chunks(command_list, NUMBER_OF_ITEMS_PER_CHUNK))
        for chunk in chunks_of_40:
            logger.info("adding chunk of {len} tasks".format(len=len(chunk)))
            response = run_todoist_sync_commands(chunk)
            logger.info("response code {code}".format(code=response.status_code))
            if response.status_code != 200:
                logger.error("response body {body}".format(body=response.text))
            else:
                logger.info("response:\n{response}".format(response=response.json()))
            if len(chunk) == NUMBER_OF_ITEMS_PER_CHUNK:
                logger.info("sleeping for 10 seconds")
                time.sleep(10)
    else:
        raise Exception("Project {project_id} is full".format(project_id=project_id))
    return message


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i: i + n]
