import os

import numpy as np
import pandas as pd
from loguru import logger

from services.strong_service import update_strong_entries

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


async def handle_excel(file_path, file_name, update):
    logger.info(file_path)
    if "strong" in file_name:
        done_message = handle_strong(file_path)
        await update.message.reply_text(done_message)
    else:
        logger.error("unsupported handle_excel name: " + file_name)
        await update.message.reply_text("unsupported handle_excel name: " + file_name)


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
    df = df.replace({np.nan: None})
    return df.values.tolist(), len(df["Date"].unique())
