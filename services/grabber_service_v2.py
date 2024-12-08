import json
import re
import time
from collections import defaultdict
from datetime import timedelta, datetime

import pandas as pd
import requests
import unicodedata
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import CallbackContext
from todoist_api_python.endpoints import get_sync_url

from helper.config_helper import is_not_correct_chat_id
from services.github_service import add_files_to_repository
from services.grabber_service import HEADERS, MAX_LENGTH_PER_MESSAGE
from services.grabber_service import VOICE_RECORDER_MATCH, \
    EASY_VOICE_RECORDER_MATCH, DEFAULT_OFFSET
from services.grabber_service import clean_api_response, clean_completed_tasks
from services.llm_service import get_summary
from services.todoist_service import get_completed_tasks, TODOIST_API
from services.todoist_service import get_default_offset_including_check

logger = setup_logging(__file__)

days_to_dump = 1

github_token = get_secrets(
    ["github/pat_obsidian"]
)

async def dump_todoist_to_monica(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return
    logger.info("starting Todoist dump to Monica")
    days_to_dump = int(context.args[0]) if context.args else 3
    data, list_of_files = get_grabber_data(days_to_dump)
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    add_files_to_repository(list_of_files, f"obsidian-refresher: {now}", f'0300_Spaces/Social Circle/Todoist-Dumps/{now.strftime("%Y-%m-%d")}/')
    await update.message.reply_text("Dump was done at {timestamp}".format(timestamp=timestamp))
    await return_content(list(data.content), "All Content", update)
    logger.info("Done Todoist dump to Monica")


async def return_content(content, intro, update: Update):
    if content is not None:
        content = "\n".join(f"* {task}" for task in content)
        await update.message.reply_text("{}: \n\n".format(intro))
        if len(content) + 100 < MAX_LENGTH_PER_MESSAGE:
            await update.message.reply_text(content)
        else:
            messages_needed = len(content) // MAX_LENGTH_PER_MESSAGE + 1
            for i in range(messages_needed):
                temp = content[i * MAX_LENGTH_PER_MESSAGE: (i + 1) * MAX_LENGTH_PER_MESSAGE]
                await update.message.reply_text(temp)
        time.sleep(5)
    else:
        await update.message.reply_text("No {} found".format(intro))


def get_grabber_data(days_to_dump):
    df_items, _, _, _ = get_data(days_to_dump)
    df_items = create_position_in_hierarchy(df_items)

    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    df_items.loc[df_items['parent_id'].isnull(), 'parent_content'] = slugify(f"Todoist-Dump {timestamp}")
    list_of_files = [create_index_file_from_dict(timestamp, df_items[df_items['parent_id'].isnull()])]

    for index, row in df_items.iterrows():
        file = create_file_from_dict(row)
        list_of_files.append(file)

    return df_items, list_of_files




def slugify(value, allow_unicode=False):
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    # add max length which then triggers generate title
    value = re.sub(r'[-\s]+', '-', value).strip('-_')
    if len(value) > 40:
        return value[:40]
    else:
        return value


def handle_sources(data):
    for index, row in data.iterrows():
        content = row["content"]
        if re.match(VOICE_RECORDER_MATCH, content):
            date_array = content.split(" ")
            date = f"{date_array[0]} {date_array[1]}"
            data.at[index, "created_at"] = date
            data.at[index, "content"] = content.split(date)[1][2:]
            data.at[index, "source"] = "Voice Recorder"
        elif re.match(EASY_VOICE_RECORDER_MATCH, content):
            content_array = content.split(" was recorded during meditation at ")
            data.at[index, "content"] = content_array[0].replace("'", "")
            date = content_array[1].split(".")[0].replace("'", "")
            # data.at[index, "created_at"] = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
            data.at[index, "source"] = "Easy Voice Recorder"
        else:
            data.at[index, "source"] = "Todoist"
    return data


def handle_offset(data):
    is_default_offset, offset, gmt_string = get_default_offset_including_check(DEFAULT_OFFSET)
    if not is_default_offset:
        row_indexer = f"DE: {gmt_string}"
        data[row_indexer] = pd.to_datetime(data["created_at"]) + pd.Timedelta(offset)
        data[row_indexer] = (pd.to_datetime(data["created_at"]) + pd.Timedelta(offset)).dt.strftime("%d.%m.%Y %H:%M")
    return data


def get_labels(labels, df_labels):
    return df_labels[df_labels['id'].isin(labels)]['name'].tolist()


def get_comments(days):
    df_notes = pd.DataFrame(
        requests.post(
            get_sync_url("sync"), headers=HEADERS, json={"sync_token": "*", "resource_types": ["notes"]}
        ).json()["notes"]
    )

    df_notes["type"] = "note"
    df_notes["source"] = "Todoist"
    df_notes.rename(columns={"item_id": "parent_id", "posted_at": "created_at"}, inplace=True)

    start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    df_notes = df_notes[df_notes["created_at"] >= start_date]

    df_notes = df_notes[~df_notes['content'].eq('')] # remove empty notes

    df_notes = df_notes[df_notes.is_deleted == False]
    df_notes.drop(
        columns=["is_deleted", "posted_uid", "reactions", "uids_to_notify", "v2_id", "v2_item_id", "v2_project_id",
                 "file_attachment"],
        inplace=True)
    return df_notes


def get_items(days, df_projects, df_labels, df_notes):
    df_items = pd.concat([
        clean_api_response(TODOIST_API.get_tasks()),
        clean_completed_tasks(get_completed_tasks(datetime.today() - timedelta(days=days + 1)))
    ], ignore_index=True)
    df_items = df_items.merge(df_projects[['project_id', 'project']], on='project_id', how='left')

    start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    df_filtered_items = df_items[df_items["created_at"] >= start_date]

    df_items['labels'] = df_items['labels'].apply(lambda x: get_labels(x, df_labels))

    exclusions = [
        df_filtered_items['content'].str.contains('add highlight to Zotero'),
        df_filtered_items['project'].isin(["Einkaufsliste"]),
        df_filtered_items['project'].str.contains('Book-Rework'),
        df_filtered_items['content'].str.startswith('item not found: '),
        df_filtered_items['content'].str.contains('nacharbeiten & Tracker pflegen'),
    ]
    df_filtered_items = df_filtered_items[~pd.concat(exclusions, axis=1).any(axis=1)]

    df_filtered_items = handle_sources(df_filtered_items)

    df_filtered_items["type"] = "task"
    df_filtered_items = pd.concat([df_filtered_items, df_notes])
    df_filtered_items = handle_offset(df_filtered_items)

    # remove items from which the parent is not in the list or parent id is none
    df_filtered_items = df_filtered_items[df_filtered_items['parent_id'].isin(df_filtered_items['id']) | df_filtered_items['parent_id'].isnull()]

    df_filtered_items["created_at"] = pd.to_datetime(df_filtered_items["created_at"]) + pd.Timedelta("01:00:00")
    df_filtered_items["created_at_string"] = df_filtered_items["created_at"].dt.strftime("%d.%m.%Y %H:%M")
    df_filtered_items["content"] = df_filtered_items["content"].str.replace('"', "")

    df_filtered_items.drop(columns=[
        "assignee_id", "assigner_id", "comment_count", "creator_id", "due",
        "url", "sync_id", "duration", "order", "task_id", "project_id", "section_id", "notes"
    ], inplace=True)
    df_filtered_items.sort_values(by="created_at", ascending=False, inplace=True)


    return df_filtered_items


def get_data(days):
    df_projects = clean_api_response(TODOIST_API.get_projects()).rename(columns={"id": "project_id", "name": "project"})
    df_labels = clean_api_response(TODOIST_API.get_labels())
    df_notes = get_comments(days)
    df_items = get_items(days, df_projects, df_labels, df_notes)
    df_items["summary"] = get_summary(df_items)
    df_items[['slugified_title']] = df_items['summary'].apply(lambda x: slugify(x)).apply(
        pd.Series)
    return df_items, df_projects, df_notes, df_labels


def create_position_in_hierarchy(df_items):
    # Set 'id' as the index
    df_items.set_index('id', inplace=True)

    # Create a dictionary to map IDs to their content
    id_to_content = df_items['slugified_title'].to_dict()

    # Group by 'parent_id' and include items with 'parent_id' as None
    grouped = df_items.groupby('parent_id', dropna=False)

    # Create a dictionary to store child IDs for each parent
    child_ids_dict = defaultdict(list)

    # Iterate over each group
    for parent_id, group in grouped:
        # Sort the group by 'created_at'
        sorted_group = group.sort_values(by='created_at')

        # Iterate over the sorted group to define previous and next items
        for i in range(len(sorted_group)):
            item = sorted_group.iloc[i]
            prev_item = sorted_group.iloc[i - 1] if i > 0 else None
            next_item = sorted_group.iloc[i + 1] if i < len(sorted_group) - 1 else None

            # Define previous and next items
            item_id = item.name
            df_items.at[item_id, 'prev_item'] = id_to_content[prev_item.name] if prev_item is not None else None
            df_items.at[item_id, 'next_item'] = id_to_content[next_item.name] if next_item is not None else None

            # Add child ID to the parent
            if parent_id is not None:
                child_ids_dict[parent_id].append(item_id)

    # Add child_ids column to the DataFrame
    df_items['child_contents'] = df_items.index.map(
        lambda x: [id_to_content[child_id] for child_id in child_ids_dict[x]] if x in child_ids_dict else None)

    # Map parent_id to content
    df_items['parent_content'] = df_items['parent_id'].map(lambda x: id_to_content[x] if x in id_to_content else None)
    return df_items


def generate_front_matter(hierarchy_dict, up_element_title=None, down_element_titles=None, prev_element_title=None,
                          next_element_title=None):
    metadata_json = {
        "up": f"[[{up_element_title}]]" if up_element_title else None,
        "down": [f"[[{title}]]" for title in down_element_titles] if down_element_titles else [],
        "next": f"[[{next_element_title}]]" if next_element_title else None,
        "prev": f"[[{prev_element_title}]]" if prev_element_title else None,
        "created": hierarchy_dict["created_at_string"],
        "slugified_title": hierarchy_dict["slugified_title"],
        "summary": hierarchy_dict["summary"],
        "project": hierarchy_dict["project"],
        "source": hierarchy_dict["source"],
        "labels": hierarchy_dict["labels"],
        "is_completed": hierarchy_dict["is_completed"],
        "type": hierarchy_dict["type"],
    }

    # Remove keys with None values
    metadata_json = {k: v for k, v in metadata_json.items()}

    return_string = "---\n"
    return_string += json.dumps(metadata_json, indent=4, sort_keys=True, ensure_ascii=False)
    return_string += "\n---\n\n"

    return return_string


def create_file_from_dict(hierarchy_dict):
    up_element_title = hierarchy_dict['parent_content']
    down_element_titles = hierarchy_dict['child_contents']
    prev_element_title = hierarchy_dict['prev_item']
    next_element_title = hierarchy_dict['next_item']
    filename = hierarchy_dict['slugified_title']
    content = generate_front_matter(hierarchy_dict, up_element_title, down_element_titles, prev_element_title,
                                    next_element_title)

    content += f"# {hierarchy_dict['content']}\n\n{hierarchy_dict['description']}\n\n"

    return {
        "filename": filename,
        "content": content
    }


def create_index_file_from_dict(timestamp, root_elements):
    metadata_json = {
        "down": [f"[[{title}]]" for title in root_elements.slugified_title],
        "created": timestamp
    }

    metadata_json = {k: v for k, v in metadata_json.items() if v is not None}

    content = "---\n"
    content += json.dumps(metadata_json, indent=4, sort_keys=True, ensure_ascii=False)
    content += "\n---\n\n"

    content += f"# Todoist-Dump {timestamp}\n\n"
    content += """
```breadcrumbs
type: tree
dir: down
fields: up, down, prev, next
```
```breadcrumbs
type: juggl
dir: down
layout: hierarchy
height: 500px
autoZoom: true
```
"""
    return {
        "filename": slugify(f"Todoist-Dump {timestamp}"),
        "content": content
    }
