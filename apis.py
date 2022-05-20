import json
import os
from datetime import date

import pandas as pd
import requests
import todoist
from loguru import logger

import helper

TODOIST_API = todoist.TodoistAPI(os.environ["TODOIST_TOKEN"])

api_key = os.environ["NOTION_TOKEN"]
base_url = "https://api.notion.com/v1/"
headers = {
    "Authorization": "Bearer " + api_key,
    "Content-Type": "application/json",
    "Notion-Version": "2021-08-16",
}

logger.add(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__))
        + "/logs/"
        + os.path.basename(__file__)
        + ".log"
    ),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def get_habit_tracker(database_id):
    url = base_url + "databases/" + database_id + "/query"
    result_list = []
    body = None
    while True:
        r = (
            requests.post(url, headers=headers).json()
            if body is None
            else requests.post(
                url, data=json.dumps(body), headers=headers
            ).json()
        )
        for results in r["results"]:
            result_list.append(results)
        body = {"start_cursor": r.get("next_cursor")}
        if not r["has_more"]:
            break
    df = pd.json_normalize(result_list, sep="~")
    df = df[["id", "properties~Date~date~start"]]
    return df


def add_exercises_to_habit_tracker(row, daily_record):
    date = row["properties~Date~date~start"]
    if date in daily_record.keys():
        url = base_url + "pages/" + str(row["id"])
        content_list = daily_record[date]
        content_json = json.dumps(
            content_list, indent=4, ensure_ascii=False
        )
        data = {
            "properties": {
                "Bulking-Details": {
                    "rich_text": [
                        {"type": "text", "text": {"content": content_json}}
                    ]
                }
            }
        }
        r = requests.patch(
            url, data=json.dumps(data), headers=headers
        ).json()


def update_strong_entries(daily_record):
    habit_trackers = helper.get_config("habit_tracker.json")
    habit_tracker_dict = {}
    for habit_tracker in habit_trackers:
        key = list(habit_tracker.keys())[0]
        habit_tracker_dict[int(key)] = habit_tracker[key]

    current_year = date.today().year
    habit_tracker = get_habit_tracker(habit_tracker_dict[current_year])

    habit_tracker.apply(
        lambda row: add_exercises_to_habit_tracker(row, daily_record),
        axis=1,
    )
