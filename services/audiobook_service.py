import csv
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from os import path

import pandas as pd
import pymysql
from loguru import logger
from quarter_lib.database import close_server_connection, create_server_connection

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)

SQL_INSERT = """INSERT INTO `audiobook_statistics` (`seconds`, `author`, `title`, `month`) VALUES (%s, %s, %s, %s)"""
SQL_UPDATE = """UPDATE `audiobook_statistics` SET seconds = %s WHERE author = %s AND title = %s AND month = %s"""


def get_records_to_add_add_and_update(old_records, new_records):
    to_add, to_update, unchanged = [], [], []
    m = new_records.merge(old_records, on=["author", "title", "month"], how="left", indicator=True)
    m["seconds_x"] = pd.to_numeric(m["seconds_x"])
    m["seconds_y"] = pd.to_numeric(m["seconds_y"])

    for index, row in m.iterrows():
        if pd.notnull(m.loc[index, "seconds_y"]):
            if row["seconds_x"] > row["seconds_y"]:
                to_update.append(tuple(row[["seconds_x", "author", "title", "month"]]))
            elif row["seconds_x"] == row["seconds_y"]:
                unchanged.append(tuple(row[["seconds_y", "author", "title", "month"]]))
            else:
                logger.info(
                    "'{book}' by '{author} for month {month}': old seconds ({old}) are bigger than the newer ({new}) ones".format(
                        book=row["title"],
                        author=row["author"],
                        old=row["seconds_y"],
                        new=row["seconds_x"],
                        month=row["month"],
                    )
                )
        else:
            to_add.append(tuple(row[["seconds_x", "author", "title", "month"]]))
    return to_add, to_update, unchanged


def update_audiobook_statistics(new_records):
    logger.info("start upadte_audiobook_statistics")
    connection = create_server_connection()
    old_records = pd.read_sql("SELECT seconds, author, title, month FROM audiobook_statistics", connection)
    to_add, to_update, unchanged = get_records_to_add_add_and_update(old_records, new_records)

    for record in to_add:
        try:
            with connection.cursor() as cursor:
                cursor.execute(SQL_INSERT, record)
                connection.commit()
        except pymysql.err.ProgrammingError as e:
            logger.error(e, record)
            continue
    for record in to_update:
        try:
            with connection.cursor() as cursor:
                cursor.execute(SQL_UPDATE, record)
                connection.commit()
        except pymysql.err.ProgrammingError as e:
            logger.error(e, record)
            continue
    close_server_connection(connection)
    done_message = "added {new} / updated {updated} / unchanged {unchanged} - from {total} in total".format(
        new=len(to_add),
        updated=len(to_update),
        unchanged=len(unchanged),
        total=len(new_records),
    )
    logger.info(done_message)
    logger.info("stop upadte_audiobook_statistics")
    return done_message


def read_audiobook_statistics(path):
    xml_data = open(path, "r", encoding="utf-8").read()  # Read file
    root = ET.XML(xml_data)  # Parse XML
    data = []
    for i, x in enumerate(root):
        for ii, y in enumerate(x):
            if y.tag == "path":
                path = y.text.split("/")
                author = path[0]
                if len(path) > 1:
                    title = path[1]
                else:
                    title = None
            elif y.tag == "time":
                time = y.text.split(" ")
                month = time[0]
                seconds_listened = time[1]
                data.append({"seconds": seconds_listened, "author": author, "title": title, "month": month})
    df = pd.DataFrame(data)
    df.dropna(inplace=True)
    return df
