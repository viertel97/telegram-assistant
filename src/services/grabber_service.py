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

from src.helper.config_helper import is_not_correct_chat_id
from src.helper.telegram_helper import send_long_message
from src.services.github_service import add_todoist_dump_to_github
from src.services.todoist_service import (
	TODOIST_API,
	get_completed_tasks,
	get_default_offset_including_check,
)

TODOIST_TOKEN = get_secrets("todoist/token")
CHECKED = "Yes"
UNCHECKED = "No"
DEFAULT_OFFSET = timedelta(hours=2)

VOICE_RECORDER_MATCH = r"^(([1-9]|[0-2]\d|[3][0-1])\.([1-9]|[0]\d|[1][0-2])\.[2][0]\d{2})$|^(([1-9]|[0-2]\d|[3][0-1])\.([1-9]|[0]\d|[1][0-2])\.[2][0]\d{2}\s([1-9]|[0-1]\d|[2][0-3])\:[0-5]\d.*)$"
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
	data, (content, public_content), raw = get_grabber_data(days_to_dump)
	try:
		graph = None  # create_mermaid_timeline(raw)
	except Exception as e:
		logger.error(e)
		graph = None
	# timestamp = add_todoist_dump_to_monica(data)
	timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	add_todoist_dump_to_github(data, graph)
	await update.message.reply_text(f"Dump was done at {timestamp}")
	await return_content(content, "All Content", update)
	await return_content(public_content, "Public Content", update)
	logger.info("Done Todoist dump to Monica")


async def return_content(content, intro, update: Update):
	if content is not None:
		await update.message.reply_text(f"{intro}: \n\n")
		await send_long_message(content, update.message.reply_text)
		time.sleep(5)
	else:
		await update.message.reply_text(f"No {intro} found")


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


def clean_completed_tasks(api_response):
	df = pd.DataFrame(api_response)
	df_concat = pd.concat([df.drop(["item_object"], axis=1), pd.json_normalize(df["item_object"])], axis=1)
	df_concat.drop(
		[
			"meta_data",
			"note_count",
			"v2_task_id",
			"added_by_uid",
			"assigned_by_uid",
			"child_order",
			"collapsed",
			"deadline",
			"is_deleted",
			"responsible_uid",
			"sync_id",
			"updated_at",
			"user_id",
			"v2_id",
			"v2_parent_id",
			"v2_project_id",
			"v2_section_id",
			"due.date",
			"due.is_recurring",
			"due.lang",
			"due.string",
			"due.timezone",
		],
		axis=1,
		inplace=True,
	)
	df_concat.rename(
		columns={
			"checked": "is_completed",
			"added_at": "created_at",
		},
		inplace=True,
	)
	return df_concat


HEADERS = create_headers(token=TODOIST_TOKEN)


def get_comments():
	df_notes = pd.DataFrame(
		requests.post(
			get_sync_url("sync"),
			headers=HEADERS,
			json={"sync_token": "*", "resource_types": ["notes"]},
		).json()["notes"],
	)
	df_notes["type"] = "note"
	return df_notes


def transform_values(x):
	if (isinstance(x, list) and len(x) == 0) or isinstance(x, float):
		return []
	return x  # Keep filled lists as they are


def get_items(days):
	start_date = (datetime.today() - timedelta(days=int(days))).strftime("%Y-%m-%d")

	df_items = clean_api_response(TODOIST_API.get_tasks())
	df_completed_tasks = clean_completed_tasks(get_completed_tasks(datetime.today() - timedelta(days=days + 1)))
	df_items = pd.concat([df_items, df_completed_tasks], axis=0, ignore_index=True)

	after_start_date = df_items["created_at"] >= start_date
	df_filtered_items = df_items.loc[after_start_date]
	df_filtered_items.sort_values(by="created_at", inplace=True)
	df_filtered_items = df_filtered_items.drop(
		[
			"assignee_id",
			"assigner_id",
			"comment_count",
			"creator_id",
			"due",
			"url",
			"sync_id",
			"task_id",
			"duration",
		],
		axis=1,
	)

	return df_filtered_items


def get_data(days):
	df_items = get_items(days)
	df_projects = clean_api_response(TODOIST_API.get_projects())
	# df_items = df_items[df_items.is_completed == 0]
	df_notes = get_comments()
	df_labels = clean_api_response(TODOIST_API.get_labels())

	return df_items, df_projects, df_notes, df_labels


def filter_data(days):
	df_filtered_items, df_projects, df_notes, df_labels = get_data(days)

	df_filtered_items["notes"] = df_filtered_items["notes"].apply(transform_values)
	cleared_list = []
	df_filtered_items.sort_values(by="created_at", inplace=True)
	for index, row in df_filtered_items.iterrows():
		row_id = row["id"]
		date_added = row["created_at"]
		content = row["content"]
		priority = row["priority"]
		description = row["description"]
		notes = df_notes[df_notes.item_id == row_id]
		# check if "notes" is empty and row["notes"] is not None

		labels, checked = get_labels(df_filtered_items.loc[index, "labels"], df_labels)
		if row["is_completed"] == True:
			checked = CHECKED
		project = df_projects.loc[df_projects["id"] == row["project_id"]]["name"].values[0]
		completed_at = row["completed_at"]

		if len(notes) > 0:
			comments = notes["content"].values
		elif len(row["notes"]) > 0:
			comments = [note["content"] for note in row["notes"]]
		else:
			comments = None
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
				"completed_at": completed_at,
			},
		)

	filtered_dates = pd.DataFrame(cleared_list)

	filtered_dates.sort_values(by="date_added", inplace=True)
	filtered_dates.reset_index(drop=True, inplace=True)

	filtered_dates["date_added"] = pd.to_datetime(filtered_dates["date_added"])
	filtered_dates["date_added"] = filtered_dates["date_added"] + pd.Timedelta("01:00:00")
	filtered_dates["date_added_string"] = filtered_dates["date_added"].dt.strftime("%d.%m.%Y %H:%M")
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
			filtered_dates.at[index, "date_added"] = datetime.strftime(datetime.strptime(date, "%Y-%m-%d %H:%M:%S"), "%d.%m.%Y %H:%M")
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
				"date_added_string",
				"completed_at",
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
				"date_added_string",
				"completed_at",
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
	filtered_dates.drop("date_added", axis=1, inplace=True)
	filtered_dates.rename(columns={"date_added_string": "date_added"}, inplace=True)
	filtered_dates = filtered_dates[~filtered_dates["content"].str.contains("add highlight to Zotero")]
	filtered_dates = filtered_dates[~filtered_dates["project"].isin(["Einkaufsliste"])]
	filtered_dates = filtered_dates[~filtered_dates["content"].str.startswith("item not found: ")]
	return filtered_dates


def filter_data_new(days):
	df_items, df_projects, df_notes, df_labels = get_data(days)

	start_date = (datetime.today() - timedelta(days=int(days))).strftime("%Y-%m-%d")

	after_start_date = df_items["created_at"] >= start_date
	df_filtered_items = df_items.loc[after_start_date]
	df_filtered_items.sort_values(by="created_at", inplace=True)
	df_filtered_items = df_filtered_items.drop(
		[
			"assignee_id",
			"assigner_id",
			"comment_count",
			"creator_id",
			"due",
			"url",
			"sync_id",
			"task_id",
			"duration",
		],
		axis=1,
	)
	df_filtered_items["notes"] = df_filtered_items["notes"].apply(transform_values)
	cleared_list = []
	df_filtered_items.sort_values(by="created_at", inplace=True)
	for index, row in df_filtered_items.iterrows():
		row_id = row["id"]
		date_added = row["created_at"]
		content = row["content"]
		priority = row["priority"]
		description = row["description"]
		notes = df_notes[df_notes.item_id == row_id]
		# check if "notes" is empty and row["notes"] is not None

		labels, checked = get_labels(df_filtered_items.loc[index, "labels"], df_labels)
		if row["is_completed"] == True:
			checked = CHECKED
		project = df_projects.loc[df_projects["id"] == row["project_id"]]["name"].values[0]
		completed_at = row["completed_at"]

		if len(notes) > 0:
			comments = notes["content"].values
		elif len(row["notes"]) > 0:
			comments = [note["content"] for note in row["notes"]]
		else:
			comments = None
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
				"completed_at": completed_at,
				"parent_id": row["parent_id"],
			},
		)

	filtered_dates = pd.DataFrame(cleared_list)

	filtered_dates.sort_values(by="date_added", inplace=True)
	filtered_dates.reset_index(drop=True, inplace=True)

	filtered_dates["date_added"] = pd.to_datetime(filtered_dates["date_added"])
	filtered_dates["date_added"] = filtered_dates["date_added"] + pd.Timedelta("01:00:00")
	filtered_dates["date_added_string"] = filtered_dates["date_added"].dt.strftime("%d.%m.%Y %H:%M")
	filtered_dates["content"] = filtered_dates["content"].str.replace('"', "")
	filtered_dates["source"] = "Todoist"
	filtered_dates["rework-comments"] = ""

	for index, row in filtered_dates.iterrows():
		# filtered_dates.at[index, "comments"] = " / ".join(row["comments"]) if row["comments"] is not None else ""
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
			filtered_dates.at[index, "date_added"] = datetime.strftime(datetime.strptime(date, "%Y-%m-%d %H:%M:%S"), "%d.%m.%Y %H:%M")
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
				"date_added_string",
				"completed_at",
				row_indexer,
				"content",
				"rework-comments",
				"priority",
				"comments",
				"description",
				"project",
				"labels",
				"source",
				"parent_id",
				"id",
			]
		]
	else:
		filtered_dates = filtered_dates[
			[
				"checked",
				"date_added",
				"date_added_string",
				"completed_at",
				"content",
				"rework-comments",
				"priority",
				"comments",
				"description",
				"project",
				"labels",
				"source",
				"parent_id",
				"id",
			]
		]
	filtered_dates = filtered_dates.sort_values("date_added")
	filtered_dates.drop("date_added", axis=1, inplace=True)
	filtered_dates.rename(columns={"date_added_string": "date_added"}, inplace=True)
	filtered_dates = filtered_dates[~filtered_dates["content"].str.contains("add highlight to Zotero")]
	filtered_dates = filtered_dates[~filtered_dates["project"].isin(["Einkaufsliste"])]
	filtered_dates = filtered_dates[~filtered_dates["content"].str.startswith("item not found: ")]
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
	return format_md(data), (get_content(data), get_content(data, "public")), data


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
