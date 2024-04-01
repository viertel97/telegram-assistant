import csv
import os
from datetime import datetime
from os import path

import pandas as pd
import pymysql
from loguru import logger
from quarter_lib_old.database import close_server_connection, create_server_connection

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def update_sleep_entries(records):
    not_added = []
    logger.info("start update_sleep_entries")
    connection = create_server_connection()
    sql = """INSERT INTO `sleep_as_android_new` (`id`, `tz`, `sleep_from`,`sleep_to`, `sched`,`hours`,`rating`,`comment`,`snore`,`noise`,`cycles`,`deepsleep`,`lenadjust`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    for record in records:
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, record)
                connection.commit()
        except pymysql.err.IntegrityError as e:
            not_added.append(record)
            continue
    close_server_connection(connection)
    done_message = "added {new} new records from {total} in total".format(
        new=len(records) - len(not_added), total=len(records)
    )
    logger.info(done_message)
    logger.info("stop update_sleep_entries")
    return done_message


def read_sleep_csv(path):
    json = []
    with open(path, encoding="utf-8") as csvfile:
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
                        year + "-" + month[:-1] + "-" + day[1:-1] + "T" + hour + ":" + minute[0] + minute[1] + "SZ"
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
                        "id": sleepid[1:-1],
                        "tz": tz[1:-1],
                        "from": datetime.strptime(sleepfrom[1:-1], "%d. %m. %Y %H:%M"),
                        "to": datetime.strptime(sleepto[1:-1], "%d. %m. %Y %H:%M"),
                        "sched": datetime.strptime(sched[1:-1], "%d. %m. %Y %H:%M"),
                        "hours": float(hours[1:-1]),
                        "rating": float(rating[1:-1]),
                        "comment": comment[1:-1],
                        # "framerate": framerate[1:-1],
                        "snore": float(snore[1:-1]),
                        "noise": float(noise[1:-1]),
                        "cycles": float(cycles[1:-1]),
                        "deepsleep": float(deepsleep[1:-1]),
                        "lenadjust": float(lenadjust[1:-1]),
                        # "geo": geo[1:-1],
                    }

                    json.append(json_body)

            except:
                print("not worked")
                continue
    df = pd.DataFrame(json)
    df = df.where(pd.notnull(df), None)
    return df.values.tolist()
