import csv
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, time, timedelta

import pandas as pd
from dateutil import parser
from loguru import logger
from telegram import Update
from telegram.ext import CallbackContext

from apis import (
    numbers_fields_ein_guter_plan,
    update_ein_guter_plan_entries,
)

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


def handle_txt(file_path, file_name, update):
    if "ein-guter-plan" in file_name:
        handle_guter_plan(file_path, file_name)
        update.message.reply_text("ein-guter-plan: done")

    else:
        logger.error("unsupported file name: " + file_name)


def handle_guter_plan(file_path, file_name):
    with open(file_path) as f:
        d = json.load(f)

    df = pd.DataFrame(d["AMPEL"]["ampelData"]).reset_index()

    df = df.pivot_table(
        values="value", index="date", columns="type"
    ).reset_index()
    df.fillna(0, inplace=True)

    for field in numbers_fields_ein_guter_plan:
        df[field] = df[field] + 1
    df["date"] = df["date"].apply(
        lambda row: datetime.strptime(row, "%d.%m.%Y")
    )
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    dicts = df.set_index("date").T.to_dict()
    update_ein_guter_plan_entries(dicts)
    os.remove(file_path)
