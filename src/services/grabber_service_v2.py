import json
from collections import defaultdict
from datetime import datetime

import pandas as pd
import yaml
from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import CallbackContext

from src.helper.config_helper import is_not_correct_chat_id
from src.helper.file_helper import slugify
from src.helper.grabber_helper import is_nan_or_none, return_content
from src.services.github_service import add_files_to_repository
from src.services.todoist_grabber_service import get_data, set_finished_label

logger = setup_logging(__file__)


async def dump_todoist_to_monica(update: Update, context: CallbackContext):
	if is_not_correct_chat_id(update.message.chat_id):
		await update.message.reply_text("Nah")
		return
	await update.message.reply_text("Starting Todoist dump V2")
	logger.info("starting Todoist dump to Monica")
	days_to_dump = int(context.args[0]) if context.args else 3
	df_items, list_of_files = get_grabber_data(days_to_dump)
	if df_items.empty:
		await update.message.reply_text("No tasks to dump")
		return
	now = datetime.now()
	timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
	add_files_to_repository(
		list_of_files,
		f"obsidian-refresher: {now}",
		f"0300_Spaces/Social Circle/Todoist-Dumps/{now.strftime('%Y%m%d')}/",
	)
	set_finished_label(df_items, now)
	await update.message.reply_text(f"Dump was done at {timestamp}")
	await return_content(list(df_items.content), "All Content", update)
	logger.info("Done Todoist dump to Monica")


def get_grabber_data(days_to_dump: int) -> tuple[pd.DataFrame, list[dict]]:
	df_items, _, _ = get_data(days_to_dump)
	if df_items.empty:
		return df_items, []
	df_items = create_position_in_hierarchy(df_items)

	timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
	index_file_name = slugify(f"AAA_Todoist-Dump {timestamp}")
	df_items.loc[df_items["parent_id"].isnull(), "parent_content"] = index_file_name
	list_of_files = [create_index_file_from_dict(index_file_name, timestamp, df_items[df_items["parent_id"].isnull()])]

	for index, row in df_items.iterrows():
		file = create_file_from_dict(row)
		list_of_files.append(file)

	return df_items, list_of_files


def create_position_in_hierarchy(df_items):
	df_items.set_index("id", inplace=True)

	id_to_content = df_items["slugified_title"].to_dict()

	grouped = df_items.groupby("parent_id", dropna=False)

	child_ids_dict = defaultdict(list)

	for parent_id, group in grouped:
		sorted_group = group.sort_values(by="created_at")

		for i in range(len(sorted_group)):
			item = sorted_group.iloc[i]
			prev_item = sorted_group.iloc[i - 1] if i > 0 else None
			next_item = sorted_group.iloc[i + 1] if i < len(sorted_group) - 1 else None

			item_id = item.name
			df_items.at[item_id, "prev_item"] = id_to_content[prev_item.name] if prev_item is not None else None
			df_items.at[item_id, "next_item"] = id_to_content[next_item.name] if next_item is not None else None

			if parent_id is not None:
				child_ids_dict[parent_id].append(item_id)

	df_items["child_contents"] = df_items.index.map(
		lambda x: [id_to_content[child_id] for child_id in child_ids_dict[x]] if x in child_ids_dict else None,
	)

	df_items["parent_content"] = df_items["parent_id"].map(lambda x: id_to_content[x] if x in id_to_content else None)

	df_items.reset_index(inplace=True)
	return df_items


def generate_front_matter(
	hierarchy_dict,
	up_element_title=None,
	down_element_titles=None,
	prev_element_title=None,
	next_element_title=None,
):
	if hierarchy_dict["content"].startswith("LLM:") or hierarchy_dict["source"] == "GHT":
		updated_content = hierarchy_dict["content"].split("\n")[0]
		if len(updated_content) > 100:
			updated_content = hierarchy_dict["summary"]
			if len(updated_content) > 100:
				updated_content = hierarchy_dict["summary"][:100] + "..."
	else:
		updated_content = None

	metadata_json = {
		"up": f"[[{up_element_title}]]" if up_element_title else None,
		"down": [f"[[{title}]]" for title in down_element_titles] if down_element_titles else [],
		"next": f"[[{next_element_title}]]" if not is_nan_or_none(next_element_title) else None,
		"prev": f"[[{prev_element_title}]]" if not is_nan_or_none(prev_element_title) else None,
		"created": hierarchy_dict["created_at_string"],
		"slugified_title": hierarchy_dict["slugified_title"],
		"content": hierarchy_dict["content"] if updated_content is None else updated_content,
		"summary": hierarchy_dict["summary"],
		"description": hierarchy_dict["description"] if hierarchy_dict["description"] else None,
		"project": hierarchy_dict["project"],
		"source": hierarchy_dict["source"],
		"tags": hierarchy_dict["labels"],
		"deadline": hierarchy_dict["deadline"],
		"due": hierarchy_dict["due"],
		"is_completed": True if hierarchy_dict["completed_at"] is not None else False,
		"type": hierarchy_dict["type"],
		"id": hierarchy_dict["id"] if not is_nan_or_none(hierarchy_dict["id"]) else None,
	}

	metadata_json = {k: v.strip() if isinstance(v, str) else v for k, v in metadata_json.items()}

	return_string = "---\n"
	return_string += yaml.dump(metadata_json, allow_unicode=True, default_flow_style=False)
	return_string += "---\n\n"

	return return_string


def create_file_from_dict(hierarchy_dict):
	up_element_title = hierarchy_dict["parent_content"]
	down_element_titles = hierarchy_dict["child_contents"]
	prev_element_title = hierarchy_dict["prev_item"]
	next_element_title = hierarchy_dict["next_item"]
	filename = hierarchy_dict["slugified_title"]
	content = generate_front_matter(
		hierarchy_dict,
		up_element_title,
		down_element_titles,
		prev_element_title,
		next_element_title,
	)

	content += f"{hierarchy_dict['content']}"
	content += f"\n\n{hierarchy_dict['description']}\n\n" if hierarchy_dict["description"] else ""

	return {"filename": filename + ".md", "content": content}


def create_index_file_from_dict(index_file_name, timestamp, root_elements):
	metadata_json = {
		"down": [f"[[{title}]]" for title in root_elements.slugified_title],
		"created": timestamp,
	}

	metadata_json = {k: v for k, v in metadata_json.items() if v is not None}

	content = "---\n"
	content += json.dumps(metadata_json, indent=4, sort_keys=True, ensure_ascii=False)
	content += "\n---\n\n"

	content += f"# Todoist-Dump {timestamp}\n\n"
	content += """

# Dataview

## All

```dataview
TABLE WITHOUT ID link(file.link, replace(content, "
", " ")) AS "Content", 
    description,
    choice(is_completed = true, "✅", "❌") AS "Completion Status", 
    created, tags, project, source, due, deadline
WHERE contains(file.folder, this.file.folder) and file != this.file
SORT created
```

## Open Tasks

```dataview
TABLE WITHOUT ID link(file.link, replace(content, "
", " ")) AS "Content", 
    description,
    choice(is_completed = true, "✅", "❌") AS "Completion Status", 
    created, tags, project, source, due, deadline
WHERE contains(file.folder, this.file.folder) and file != this.file and is_completed = false
SORT created
```

# Breadcrumbs

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
	return {"filename": index_file_name + ".md", "content": content}
