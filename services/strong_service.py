import os

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


def handle_strong(file_path):
    logger.info("start handle_strong")
    daily_record, unique_sessions = read_strong_excel(file_path)
    done_message = update_strong_entries(daily_record, unique_sessions)
    os.remove(file_path)
    logger.info("stop handle_strong")
    return done_message


def read_strong_excel(file_path):
    df = pd.read_csv(file_path, sep=";")
    df = df.where(pd.notnull(df), None)
    return df.values.tolist(), len(df["Date"].unique())


def update_strong_entries(records, unique_sessions):
    logger.info("start update_strong_entries")
    connection = create_server_connection()
    sql = """INSERT INTO `strong` (`Date`,`Workout Name`,`Exercise Name`,`Set Order`,`Weight`,`Weight Unit`,`Reps`,`RPE`,`Distance`,`Distance Unit`,`Seconds`,`Notes`,`Workout Notes`,`Workout Duration`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE strong")
            cursor.execute("ALTER TABLE strong AUTO_INCREMENT = 1")
            connection.commit()
            cursor.executemany(sql, records)
            connection.commit()
    except pymysql.err.IntegrityError as e:
        logger.error("IntegrityError: {error}".format(error=e))
    finally:
        close_server_connection(connection)
    done_message = "truncated table and added {individual} individual sessions with {new} records in total".format(
        individual=unique_sessions, new=len(records)
    )
    logger.info(done_message)
    logger.info("stop update_strong_entries")
    return done_message
