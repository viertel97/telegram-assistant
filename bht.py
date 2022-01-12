import json
import os
from datetime import datetime, time
from json.decoder import JSONDecodeError

import speech_recognition as sr
from loguru import logger
from telegram import Update
from telegram.ext import CallbackContext

from helper import is_not_correct_chat_id

if os.name == "nt":
    bat_habit_file_path = "bad_habit.json"
    windows = True
else:
    bat_habit_file_path = "/home/pi/python/bad_habit.json"

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def write_to_file(splitted_string, timestamp):
    try:
        with open(bat_habit_file_path, encoding="utf-8") as data_file:
            data = json.loads(data_file.read())
    except JSONDecodeError:
        data = []
    dict_to_save = {"bad_habit": splitted_string[1], "timestamp": timestamp, "payed": False}
    data.append(dict_to_save)
    with open(bat_habit_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def bht(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        update.message.reply_text("Nah")
        return
    timestamp = datetime.now().isoformat()
    splitted_string = update.message.text.split("bht_")
    write_to_file(splitted_string, timestamp)
    update.message.reply_text("{timestamp}: '{bht}' inserted".format(timestamp=timestamp, bht=splitted_string[1]))
