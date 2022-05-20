import math
import os

import pandas as pd
from dateutil import parser
from loguru import logger

from apis import update_strong_entries

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


def handle_excel(file_path, file_name):
    logger.info(file_path)
    if "strong" in file_name:
        handle_strong(file_path)
    else:
        logger.error("unsupported handle_excel name: " + file_name)


def handle_strong(file_path):
    logger.info("start handle_strong")
    daily_record = read_strong_excel(file_path)
    update_strong_entries(daily_record)
    os.remove(file_path)
    logger.info("stop handle_strong")


def read_strong_excel(file_path):
    df = pd.read_csv(file_path, sep=";")
    df.drop(
        [
            "Distance",
            "Seconds",
            "Distance Unit",
            "Workout Notes",
            "Weight Unit",
            "Set Order",
        ],
        inplace=True,
        axis=1,
    )
    records = df.to_dict("records")

    daily_record = {}
    for record in records:
        date = parser.parse(record["Date"]).strftime("%Y-%m-%d")
        if date not in daily_record.keys():
            daily_record[date] = {}
        daily_record[date]["Workout Name"] = record.pop("Workout Name")
        daily_record[date]["Workout Duration"] = record.pop(
            "Workout Duration"
        )
        daily_record[date]["Datetime"] = record.pop("Date")
        exercise = {}
        for key, value in record.items():
            if (
                type(value) == float
                and not math.isnan(value)
                or not type(value) == float
            ):
                exercise[key] = value
        temp_list = (
            daily_record[date]["exercise_list"]
            if "exercise_list" in daily_record[date].keys()
            else []
        )
        temp_list.append(exercise)
        daily_record[date]["exercise_list"] = temp_list
    return daily_record
