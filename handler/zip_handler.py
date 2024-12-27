import os
import shutil
import zipfile
from os import path

from loguru import logger

from services.audiobook_service import (
    read_audiobook_statistics,
    update_audiobook_statistics,
)
from services.sleep_as_android_service import read_sleep_csv, update_sleep_entries

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


async def handle_zip(file_path, file_name, update):
    folder = file_path[:-4]
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(folder)
    if path.exists(folder + "/sleep-export.csv"):
        await update.message.reply_text("Sleep as Android")
        records = read_sleep_csv(folder + "/sleep-export.csv")
        done_message = update_sleep_entries(records)
    elif path.exists(folder + "/!Smart AudioBook Player Statistics/statistics.xml"):
        await update.message.reply_text("Smart AudioBook Player")
        records = read_audiobook_statistics(
            folder + "/!Smart AudioBook Player Statistics/statistics.xml"
        )
        done_message = update_audiobook_statistics(records)
    os.remove(file_path)
    shutil.rmtree(folder)
    return done_message
