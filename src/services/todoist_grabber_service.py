import re
from datetime import datetime, timedelta

import pandas as pd
import requests
from todoist_api_python.endpoints import get_sync_url

from src.handler.xml_handler import logger
from src.helper.file_helper import slugify
from src.helper.grabber_helper import DEFAULT_OFFSET, EASY_VOICE_RECORDER_MATCH, GHT_MATCH, VOICE_RECORDER_MATCH
from src.services.llm_service import get_summaries
from src.services.todoist_service import HEADERS, TODOIST_API, get_completed_tasks, get_default_offset_including_check


def get_data(days):
	df_projects = clean_api_response(TODOIST_API.get_projects()).rename(columns={"id": "project_id", "name": "project"})
	df_labels = clean_api_response(TODOIST_API.get_labels())
	df_notes = get_comments(days)
	df_items = get_items(days, df_projects, df_labels, df_notes)
	if df_items.empty:
		logger.info("No data to dump")
		return df_items, df_projects, df_notes, df_labels
	df_items["summary"] = get_summaries(df_items.content)
	df_items[["slugified_title"]] = df_items["summary"].apply(lambda x: slugify(x)).apply(pd.Series)
	return df_items, df_projects, df_notes, df_labels


def set_finished_label(df_items: pd.DataFrame, now: datetime):
	tag_name = f"dumped-{now.strftime('%Y%m%d')}"
	for index, file in df_items.iterrows():
		if file["type"] == "task":
			TODOIST_API.update_task(file["id"], labels=[tag_name])
	logger.info("Finished label set")


def get_labels(labels, df_labels):
	return df_labels[df_labels["id"].isin(labels)]["name"].tolist()


def get_comments(days):
	df_notes = pd.DataFrame(
		requests.post(
			get_sync_url("sync"),
			headers=HEADERS,
			json={"sync_token": "*", "resource_types": ["notes"]},
		).json()["notes"],
	)
	df_notes.rename(columns={"item_id": "parent_id", "posted_at": "created_at"}, inplace=True)

	start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
	df_notes = df_notes[df_notes["created_at"] >= start_date]

	df_notes["type"], df_notes["source"], df_notes["is_completed"] = (
		"note",
		"Todoist",
		False,
	)
	df_notes = df_notes[~df_notes["content"].eq("")]  # remove empty notes
	df_notes = df_notes[df_notes.is_deleted == False]

	df_notes = df_notes[["id", "content", "parent_id", "created_at", "type", "source", "is_completed"]]
	return df_notes


def get_items(days, df_projects, df_labels, df_notes):
	df_items = pd.concat(
		[
			clean_api_response(TODOIST_API.get_tasks()),
			clean_completed_tasks(get_completed_tasks(datetime.today() - timedelta(days=days + 1))),
		],
		ignore_index=True,
	)
	df_items = df_items.merge(df_projects[["project_id", "project"]], on="project_id", how="left")

	start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
	df_filtered_items = df_items[df_items["created_at"] >= start_date]

	exclusions = [
		df_filtered_items["content"].str.contains("add highlight to Zotero"),
		df_filtered_items["labels"].apply(
			lambda x: "filtered" in x
		),  # first thought about "transcription", but this one is more precise and not all transcriptions should be filtered out
		df_filtered_items["labels"].apply(lambda x: any([label.startswith("dumped") for label in x])),
		df_filtered_items["project"].isin(["Einkaufsliste", "Habits", "Routines"]),
		df_filtered_items["project"].str.contains("Book-Rework"),
		df_filtered_items["content"].str.startswith("item not found: "),
		df_filtered_items["content"].str.contains("nacharbeiten & Tracker pflegen"),
		df_filtered_items["content"].str.contains("§§§ Obsidian-Notiz überarbeiten"),
		df_filtered_items["content"].str.contains(r"^.* in Zotero & Obsidian einpflegen$"),
		df_filtered_items["content"].isin(["Hörbücher updaten + in einzelne Kapitel aufteilen + PDF runterladen"]),
		df_filtered_items["content"].str.contains(r"^Aus Obsidian-Datei für .* Tasks generieren$"),
		df_filtered_items["content"].str.contains(
			r"^Vorherige Obsidian-Notizen aus dem Buch .* in 10 Takeaways überführen \+ Impressionen, Zitate und Bonus einpflegen$"
		),
		df_filtered_items["content"].str.contains(r"^Analyse über .* zu Cubox hinzufügen und geg. lesen$"),
		df_filtered_items["content"].str.contains("](cubox://card?id=", regex=False),  # remove daily/daily_cubox_reading_routine entries
		df_filtered_items["content"].isin(
			[
				"Spülmaschine leeren",
				"Waschmaschine leeren + Wäsche aufhängen",
				"Wäsche abhängen",
			],
		),
		df_filtered_items["description"].str.contains("Oldest file"),
		df_filtered_items["description"].str.contains("Random activity file"),
	]
	df_filtered_items = df_filtered_items[~pd.concat(exclusions, axis=1).any(axis=1)]

	df_filtered_items = handle_sources(df_filtered_items)

	df_filtered_items["type"] = "task"
	df_filtered_items = pd.concat([df_filtered_items, df_notes])
	df_filtered_items = handle_offset(df_filtered_items)

	# remove items from which the parent is not in the list or parent id is none
	df_filtered_items = df_filtered_items[
		df_filtered_items["parent_id"].isin(df_filtered_items["id"]) | df_filtered_items["parent_id"].isnull()
	]

	df_filtered_items["created_at"] = pd.to_datetime(df_filtered_items["created_at"]) + pd.Timedelta("01:00:00")
	df_filtered_items["created_at_string"] = df_filtered_items["created_at"].dt.strftime("%Y-%m-%dT%H:%M:%S")

	df_filtered_items["content"] = df_filtered_items["content"].str.split(" ~ ")
	df_filtered_items = df_filtered_items.explode("content").reset_index(drop=True)

	df_filtered_items["content"] = df_filtered_items["content"].replace({"Ş": "S", "ş": "s"}, regex=True)
	df_filtered_items["content"] = df_filtered_items["content"].str.replace('"', "")

	df_filtered_items.drop(
		columns=[
			"assignee_id",
			"assigner_id",
			"comment_count",
			"creator_id",
			"task_id",
			"due",
			"url",
			"sync_id",
			"duration",
			"order",
			"project_id",
			"section_id",
			"notes",
		],
		inplace=True,
	)

	df_filtered_items = df_filtered_items.where(pd.notnull(df_filtered_items), None)

	df_filtered_items.sort_values(by="created_at", ascending=False, inplace=True)

	return df_filtered_items


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


def handle_sources(data):
	for index, row in data.iterrows():
		content = row["content"]
		if re.match(VOICE_RECORDER_MATCH, content):
			date_array = content.split(" ")
			date = f"{date_array[0]} {date_array[1]}"
			# data.at[index, "created_at"] = parser.parse(date).strftime("%Y-%m-%d %H:%M:%S")
			data.at[index, "content"] = content.split(date)[1][2:]
			data.at[index, "source"] = "Voice Recorder"
		elif re.match(EASY_VOICE_RECORDER_MATCH, content):
			content_array = content.split(" was recorded during meditation at ")
			data.at[index, "content"] = content_array[0].replace("'", "")
			date = content_array[1].split(".")[0].replace("'", "")
			# data.at[index, "created_at"] = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
			data.at[index, "source"] = "Easy Voice Recorder"
		elif re.match(GHT_MATCH, content):
			match = re.match(GHT_MATCH, content)
			rest_of_string = content.split(match.group(0))[1]
			data.at[index, "content"] = rest_of_string
			data.at[index, "source"] = "GHT"
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
