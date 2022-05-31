import csv
import os
import shutil
import sys
import zipfile

from dateutil import parser
from loguru import logger
from telegram import Update
from telegram.ext import CallbackContext

from apis import update_sleep_entries

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


def handle_zip(file_path, file_name):
    folder = file_path[:-4]
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(folder)
    json = read_sleep_csv(folder + "/sleep-export.csv")
    update_sleep_entries(json)
    os.remove(file_path)
    shutil.rmtree(folder)


def read_sleep_csv(path):
    json = []
    with open(path) as csvfile:
        sleep_reader = csv.reader(csvfile, delimiter=",", quotechar="|")
        for row in sleep_reader:
            try:
                row_length = len(row[1])
                if row_length > 2:
                    day = row[2].split().pop(0)
                    month = row[2].split().pop(1)
                    year = row[2].split().pop(2)
                    time = row[2].split().pop(3)
                    hour, minute = time.split(":")
                    current_time = (
                        year
                        + "-"
                        + month[:-1]
                        + "-"
                        + day[1:-1]
                        + "T"
                        + hour
                        + ":"
                        + minute[0]
                        + minute[1]
                        + "SZ"
                    )
                    sleepid = row[0]
                    tz = row[1]
                    sleepfrom = row[2]
                    sleepto = row[3]
                    sched = row[4]
                    hours = row[5]
                    rating = row[6]
                    comment = row[7]
                    framerate = row[8]
                    snore = row[9]
                    noise = row[10]
                    cycles = row[11]
                    deepsleep = row[12]
                    lenadjust = row[13]
                    geo = row[14]
                    json_body = {
                        # "measurement": "sleep",
                        # "tags": {
                        #     "sensor": "sleep"
                        # },
                        # "time": current_time,
                        # "id": sleepid[1:-1],
                        "tz": tz[1:-1],
                        "from": parser.parse(sleepfrom[1:-1]),
                        "to": parser.parse(sleepto[1:-1]),
                        "sched": sched[1:-1],
                        "hours": float(hours[1:-1]),
                        "rating": float(rating[1:-1]),
                        "comment": comment[1:-1],
                        # "framerate": framerate[1:-1],
                        "snore": float(snore[1:-1]),
                        "noise": float(noise[1:-1]),
                        "cycles": float(cycles[1:-1]),
                        "deepsleep": float(deepsleep[1:-1]),
                        "lenadjust": float(lenadjust[1:-1]),
                        # "geo": geo[1:-1]
                    }

                    json.append(json_body)

            except:
                print("not worked")
                continue
    return json
