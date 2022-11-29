import os
from datetime import datetime, timedelta
from uuid import uuid4

import pandas as pd
import pymysql.cursors
from loguru import logger

DB_HOST = os.environ["DB_HOST"]

DB_NAME = os.environ["DB_NAME"]
DB_USERNAME = os.environ["DB_USERNAME"]
DB_PASSWORD = os.environ["DB_PASSWORD"]

DB_NAME_MONICA = os.environ["DB_NAME_MONICA"]
DB_USERNAME_MONICA = os.environ["DB_USERNAME_MONICA"]
DB_PASSWORD_MONICA = os.environ["DB_PASSWORD_MONICA"]

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def create_server_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=3306,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
    )


def create_monica_server_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=3306,
        user=DB_USERNAME_MONICA,
        password=DB_PASSWORD_MONICA,
        database=DB_NAME_MONICA,
        cursorclass=pymysql.cursors.DictCursor,
    )


def close_server_connection(connection):
    connection.close()
