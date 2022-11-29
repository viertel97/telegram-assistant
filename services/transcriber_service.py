import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

import speech_recognition as sr
from loguru import logger
from quarter_lib.file_helper import delete_files
from quarter_lib.transcriber import get_recognized_text
from telegram import Update
from telegram.ext import CallbackContext

from helper.config_helper import is_not_correct_chat_id
from services.todoist_service import (
    TODOIST_API,
    add_to_todoist_with_file,
    update_due_date,
)

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)

r = sr.Recognizer()

FILENAME = "temp.mp4"


async def separate(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return
    now = datetime.now()
    message = "* Next book - added on {date} at {time}".format(
        date=now.strftime("%d.%m.%Y"),
        time=now.strftime("%H:%M"),
    )
    await update.message.reply_text(message)
    due = {
        "date": (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "is_recurring": False,
        "lang": "en",
        "string": "tomorrow",
        "timezone": None,
    }
    item = TODOIST_API.add_task(message, project_id=2281154095, due=due)
    update_due_date(item.id, due=due, add_reminder=True)


async def video_to_text(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return
    logger.info("start: Video to text")
    file_id = update.message.video.file_id
    file = await context.bot.get_file(file_id)
    file_path = os.path.join(sys.path[0], FILENAME)
    await file.download(file_path)
    new_file_path = file_path + ".wav"
    wav_cmd = 'ffmpeg -y -i "' + file_path + '" -ar 48000 -ac 1 "' + new_file_path + '"'
    subprocess.call(wav_cmd, shell=True)
    r_file = sr.AudioFile(new_file_path)
    with r_file as source:
        audio = r.record(source)
    recognized_alternatives_de = r.recognize_google(audio, language="de-DE", show_all=True)
    recognized_alternatives_en = r.recognize_google(audio, language="en-US", show_all=True)
    recognized_text_de = recognized_alternatives_de["alternative"][0]
    recognized_text_en = recognized_alternatives_en["alternative"][0]
    now = datetime.now()
    message = 'DE: "{recognized_text_de}" ({recognized_text_de_confidence}%) \n\n EN: "{recognized_text_en}" ({recognized_text_en_confidence}%) \n\n on {date} at {time} - add highlight to Zotero'.format(
        recognized_text_de=recognized_text_de["transcript"],
        recognized_text_de_confidence=recognized_text_de["confidence"],
        recognized_text_en=recognized_text_en["transcript"],
        recognized_text_en_confidence=recognized_text_en["confidence"],
        date=now.strftime("%d.%m.%Y"),
        time=now.strftime("%H:%M"),
    )
    await update.message.reply_text(message)
    due = {
        "date": (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "is_recurring": False,
        "lang": "en",
        "string": "tomorrow",
        "timezone": None,
    }
    item = TODOIST_API.add_task(message, project_id=2281154095)
    update_due_date(item.id, due=due, add_reminder=True)

    delete_files([file_path, new_file_path])
    logger.info("end: Video to text")


async def voice_to_text(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return
    logger.info("start: Voice to text")
    file_name = (
        str(update.message.chat_id) + "_" + str(update.message.from_user.id) + str(update.message.message_id) + ".ogg"
    )
    file_id = update.message.voice.file_id
    file = await context.bot.get_file(file_id)
    file_path = os.path.join(sys.path[0], file_name)
    await file.download(file_path)
    print(file_path)

    modification_date = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%d.%m.%Y %H:%M")
    recognized_text, wav_converted_file_path = get_recognized_text(file_path)
    if "absatz" in recognized_text.lower():
        phrases = recognized_text.lower().split("absatz")
        for phrase in phrases:
            final_message = modification_date + " : " + phrase
            await update.message.reply_text(final_message)
            add_to_todoist_with_file(final_message, wav_converted_file_path)
    else:
        final_message = modification_date + " : " + recognized_text
        await update.message.reply_text(final_message)
        await add_to_todoist_with_file(final_message, wav_converted_file_path)
    delete_files([file_path, wav_converted_file_path])
    logger.info("end: Voice to text")
