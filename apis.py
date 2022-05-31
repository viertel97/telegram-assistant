import json
import math
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

numbers_fields_ein_guter_plan = [
    "sleep",
    "mood",
    "food",
    "hydration",
    "exercise",
    "selfcare",
    "social",
    "stress",
]

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def get_database(database_id):
    url = base_url + "databases/" + database_id + "/query"
    result_list = []
    body = None
    while True:
        r = (
            requests.post(url, headers=headers).json()
            if body is None
            else requests.post(url, data=json.dumps(body), headers=headers).json()
        )
        for results in r["results"]:
            result_list.append(results)
        body = {"start_cursor": r.get("next_cursor")}
        if not r["has_more"]:
            break
    df = pd.json_normalize(result_list, sep="~")
    return df


### Strong ###


def add_exercises_to_habit_tracker(row, daily_record):
    date = row["properties~Date~date~start"]
    if date in daily_record.keys():
        if not row["properties~Workout Name~rich_text"]:
            url = base_url + "pages/" + str(row["id"])
            data = {
                "properties": {
                    "Workout Name": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": daily_record[date]["Workout Name"]},
                            }
                        ]
                    },
                    "Workout Duration": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": daily_record[date]["Workout Duration"]},
                            }
                        ]
                    },
                    "Datetime": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": daily_record[date]["Datetime"]},
                            }
                        ]
                    },
                    "exercise_list": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": str(daily_record[date]["exercise_list"])},
                            }
                        ]
                    },
                }
            }
            r = requests.patch(url, data=json.dumps(data), headers=headers)
            if r.status_code != 200:
                logger.error(r)


def update_strong_entries(daily_record):
    habit_tracker_dict = helper.get_config_as_dict("strong.json")
    current_year = date.today().year
    habit_tracker = get_database(habit_tracker_dict[str(current_year)])

    habit_tracker.apply(
        lambda row: add_exercises_to_habit_tracker(row, daily_record),
        axis=1,
    )


### Ein guter Plan ###


def generate_data(day_object):
    data = {
        "properties": {},
    }
    for field in numbers_fields_ein_guter_plan:
        data["properties"][field] = {"number": float(day_object[field])}
    return data


def update_ein_guter_plan_entries(records):
    databases_dict = helper.get_config_as_dict("databases.json")
    database = get_database(databases_dict["ein-guter-plan"])

    for day in records.keys():
        sel_date = database.loc[database["properties~Date~date~start"] == day].iloc[0]
        if not sel_date["properties~sleep~number"] > 0:
            url = base_url + "pages/" + sel_date["id"]
            data = generate_data(records[day])
            data = json.dumps(data)
            r = requests.patch(url, data=data, headers=headers)
            if r.status_code != 200:
                logger.error(r.json())
    logger.info("update_ein_guter_plan_entries done")


### Sleep as Android ###


def update_sleep_entries(records):
    databases_dict = helper.get_config_as_dict("databases.json")
    database = get_database(databases_dict["sleeping"])

    database.apply(
        lambda row: add_entry_to_sleeping_table(row, records),
        axis=1,
    )
    print("yes")


def add_entry_to_sleeping_table(row, daily_record):
    date = row["properties~Date~date~start"]
    if date in daily_record.keys():
        url = base_url + "pages/" + str(row["id"])
        content_list = daily_record[date]
        content_json = json.dumps(content_list, indent=4, ensure_ascii=False)
        data = {"properties": {"Bulking-Details": {"rich_text": [{"type": "text", "text": {"content": content_json}}]}}}
        r = requests.patch(url, data=json.dumps(data), headers=headers).json()
