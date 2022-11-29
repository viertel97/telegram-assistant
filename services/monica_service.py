import os
from datetime import datetime
from uuid import uuid4

import pymysql.cursors
from loguru import logger
from quarter_lib.database import (
    close_server_connection,
    create_monica_server_connection,
)

DEFAULT_ACCOUNT_ID = 1
INBOX_CONTACT_ID = 52
MICROJOURNAL_CONTACT_ID = 58

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def add_todoist_dump_to_monica(data):
    connection = create_monica_server_connection()
    try:
        with connection.cursor() as cursor:
            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            happened_at = now.strftime("%Y-%m-%d")
            activities_values = tuple(
                (
                    uuid4(),
                    DEFAULT_ACCOUNT_ID,
                    "Todoist-Dump: {timestamp}".format(timestamp=timestamp),
                    data,
                    happened_at,
                    timestamp,
                    timestamp,
                )
            )
            cursor.execute(
                "INSERT INTO activities (uuid, account_id, summary, description, happened_at, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                activities_values,
            )
            connection.commit()
            last_row_id = cursor.lastrowid

            activity_contact_values = tuple((last_row_id, INBOX_CONTACT_ID, DEFAULT_ACCOUNT_ID))
            cursor.execute(
                "INSERT INTO activity_contact (activity_id, contact_id, account_id) VALUES (%s, %s, %s)",
                activity_contact_values,
            )
            connection.commit()
    except pymysql.err.IntegrityError as e:
        logger.error("IntegrityError: {error}".format(error=e))
    close_server_connection(connection)
    return timestamp
