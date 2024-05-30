import os
import re
import time
from datetime import datetime, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup
from loguru import logger
from quarter_lib.akeyless import get_secrets
from telegram import Update
from telegram.ext import CallbackContext
from todoist_api_python.endpoints import get_sync_url
from todoist_api_python.headers import create_headers

from helper.config_helper import is_not_correct_chat_id
from services.github_service import add_todoist_dump_to_github
from services.monica_service import add_todoist_dump_to_monica
from services.todoist_service import TODOIST_API, get_default_offset_including_check

TODOIST_TOKEN = get_secrets("todoist/token")
CHECKED = "Yes"
UNCHECKED = "No"
DEFAULT_OFFSET = timedelta(hours=2)
MAX_LENGTH_PER_MESSAGE = 4096

VOICE_RECORDER_MATCH = "^(([1-9]|[0-2]\d|[3][0-1])\.([1-9]|[0]\d|[1][0-2])\.[2][0]\d{2})$|^(([1-9]|[0-2]\d|[3][0-1])\.([1-9]|[0]\d|[1][0-2])\.[2][0]\d{2}\s([1-9]|[0-1]\d|[2][0-3])\:[0-5]\d.*)$"
EASY_VOICE_RECORDER_MATCH = ".+was recorded during meditation at.+"

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


async def dump_todoist_to_monica(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return
    logger.info("starting Todoist dump to Monica")
    days_to_dump = int(context.args[0]) if context.args else 3
    data, (content, public_content) = get_grabber_data(days_to_dump)
    timestamp = add_todoist_dump_to_monica(data)
    add_todoist_dump_to_github(data)
    await update.message.reply_text("Dump was done at {timestamp}".format(timestamp=timestamp))
    await return_content(content, "All Content", update)
    await return_content(public_content, "Public Content", update)
    logger.info("Done Todoist dump to Monica")


async def return_content(content, intro, update: Update):
    if content is not None:
        await update.message.reply_text("{}: \n\n".format(intro))
        if len(content) < MAX_LENGTH_PER_MESSAGE:
            await update.message.reply_text(content)
        else:
            messages_needed = len(content) // MAX_LENGTH_PER_MESSAGE + 1
            for i in range(messages_needed):
                temp = content[i * MAX_LENGTH_PER_MESSAGE: (i + 1) * MAX_LENGTH_PER_MESSAGE]
                await update.message.reply_text(temp)
        time.sleep(5)
    else:
        await update.message.reply_text("No {} found".format(intro))


def get_labels(labels, df_labels):
    is_checked = UNCHECKED
    label_list = []
    for label_id in labels:
        label = df_labels.loc[df_labels.id == label_id].name
        label_list.append(label)
        if "DONE" in str(label):
            is_checked = CHECKED
            label_list.remove(label)
    return [item for sublist in label_list for item in sublist], is_checked


def clean_api_response(api_response):
    temp_list = []
    for entry in api_response:
        temp_list.append(entry.__dict__)
    return pd.DataFrame(temp_list)


HEADERS = create_headers(token=TODOIST_TOKEN)


def get_comments():
    return pd.DataFrame(
        requests.post(
            get_sync_url("sync"), headers=HEADERS, json={"sync_token": "*", "resource_types": ["notes"]}
        ).json()["notes"]
    )


def filter_data(days):
    df_items = clean_api_response(TODOIST_API.get_tasks())
    df_projects = clean_api_response(TODOIST_API.get_projects())
    # df_items = df_items[df_items.is_completed == 0]
    df_notes = get_comments()
    df_labels = clean_api_response(TODOIST_API.get_labels())

    start_date = (datetime.today() - timedelta(days=int(days))).strftime("%Y-%m-%d")

    after_start_date = df_items["created_at"] >= start_date
    df_filtered_items = df_items.loc[after_start_date]

    cleared_list = []
    for index, row in df_filtered_items.iterrows():
        comments = None

        row_id = row["id"]
        date_added = row["created_at"]
        content = row["content"]
        priority = row["priority"]
        description = row["description"]
        notes = df_notes[df_notes.item_id == row_id]
        labels, checked = get_labels(df_filtered_items.loc[index, "labels"], df_labels)
        project = df_projects.loc[df_projects['id'] == row["project_id"]]['name'].values[0]

        if len(notes) > 0:
            comments = notes["content"].values
        cleared_list.append(
            {
                "id": row_id,
                "checked": checked,
                "date_added": date_added,
                "content": content,
                "priority": int(priority),
                "comments": comments,
                "labels": labels,
                "description": description,
                "project": project,
            }
        )

    filtered_dates = pd.DataFrame(cleared_list)

    filtered_dates.sort_values(by="date_added", inplace=True)
    filtered_dates.reset_index(drop=True, inplace=True)

    filtered_dates["temp_date"] = pd.to_datetime(filtered_dates["date_added"])
    filtered_dates["temp_date"] = filtered_dates["temp_date"] + pd.Timedelta("02:00:00")
    filtered_dates["temp_date_string"] = filtered_dates["temp_date"].dt.strftime("%d.%m.%Y %H:%M")
    filtered_dates = filtered_dates.drop(["temp_date", "date_added"], axis=1)
    filtered_dates = filtered_dates.rename(columns={"temp_date_string": "date_added"})
    filtered_dates["content"] = filtered_dates["content"].str.replace('"', "")
    filtered_dates["source"] = "Todoist"
    filtered_dates["rework-comments"] = ""

    for index, row in filtered_dates.iterrows():
        filtered_dates.at[index, "comments"] = " / ".join(row["comments"]) if row["comments"] is not None else ""
        filtered_dates.at[index, "labels"] = " / ".join(row["labels"]) if row["labels"] is not None else ""

        content = row["content"]
        if re.match(VOICE_RECORDER_MATCH, content):
            date_array = content.split(" ")
            date = date_array[0] + " " + date_array[1]
            filtered_dates.at[index, "date_added"] = date
            new_content = content.split(date)[1][2:]
            filtered_dates.at[index, "content"] = new_content
            filtered_dates.at[index, "source"] = "Voice Recorder"
        elif re.match(EASY_VOICE_RECORDER_MATCH, content):
            content_array = content.split(" was recorded during meditation at ")
            filtered_dates.at[index, "content"] = content_array[0].replace("'", "")
            date = content_array[1].split(".")[0].replace("'", "")
            filtered_dates.at[index, "date_added"] = datetime.strftime(
                datetime.strptime(date, "%Y-%m-%d %H:%M:%S"), "%d.%m.%Y %H:%M"
            )
            filtered_dates.at[index, "source"] = "Easy Voice Recorder"
            filtered_dates.at[index, "source"] = "Easy Voice Recorder"

    is_default_offset, offset, gmt_string = get_default_offset_including_check(DEFAULT_OFFSET)
    if not is_default_offset:
        row_indexer = "DE: " + gmt_string
        filtered_dates["temp_date"] = pd.to_datetime(filtered_dates["date_added"])
        filtered_dates[row_indexer] = filtered_dates["temp_date"] + pd.Timedelta(offset)
        filtered_dates[row_indexer] = filtered_dates[row_indexer].dt.strftime("%d.%m.%Y %H:%M")
        filtered_dates = filtered_dates[
            [
                "checked",
                "date_added",
                row_indexer,
                "content",
                "rework-comments",
                "priority",
                "comments",
                "description",
                "project",
                "labels",
                "source",
                "id",
            ]
        ]
    else:
        filtered_dates = filtered_dates[
            [
                "checked",
                "date_added",
                "content",
                "rework-comments",
                "priority",
                "comments",
                "description",
                "project",
                "labels",
                "source",
                "id",
            ]
        ]
    filtered_dates = filtered_dates.sort_values("date_added")
    return filtered_dates


def format_html(data):
    data["checked"].replace("No", "❌", inplace=True)
    data["checked"].replace("Yes", "✔️", inplace=True)
    soup = BeautifulSoup(data.to_html())
    for i in soup.findAll("th"):
        if i.text.isnumeric():
            i.name = "td"
    return str(soup)


def format_md(data):
    data["checked"].replace("No", "❌", inplace=True)
    data["checked"].replace("Yes", "✔️", inplace=True)
    return data.to_markdown(tablefmt="pipe")


def get_grabber_data(days_to_dump):
    data = filter_data(days_to_dump)
    data.drop("id", axis=1, inplace=True)
    return format_md(data), (get_content(data), get_content(data, "public"))


def get_content(data, filter_by=None):
    message = None
    for index, row in data.iterrows():
        content = data.loc[index, "content"]
        if filter_by is None:
            message = message + "* " + content + "\n" if message is not None else "* " + content + "\n"
        else:
            label = data.loc[index, "labels"]
            if filter_by in label:
                message = message + "* " + content + "\n" if message is not None else "* " + content + "\n"
    return message
