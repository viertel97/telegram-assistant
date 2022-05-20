import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError

import speech_recognition as sr
from loguru import logger
from telegram import Update
from telegram.ext import CallbackContext

from apis import TODOIST_API
from helper import is_not_correct_chat_id

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

r = sr.Recognizer()

FILENAME = "temp.mp4"

VIDEO_TRANSCRIBE_LANGUAGE = "en-GB"


def change_video_language(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        update.message.reply_text("Nah")
        return
    global VIDEO_TRANSCRIBE_LANGUAGE
    if VIDEO_TRANSCRIBE_LANGUAGE == "de-DE":
        VIDEO_TRANSCRIBE_LANGUAGE = "en-GB"
    else:
        VIDEO_TRANSCRIBE_LANGUAGE = "de-DE"
    update.message.reply_text("New language: " + VIDEO_TRANSCRIBE_LANGUAGE)


def video_to_text(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        update.message.reply_text("Nah")
        return
    TODOIST_API.sync()
    file_id = update.message.video.file_id
    file = context.bot.get_file(file_id)
    file_path = os.path.join(sys.path[0], FILENAME)
    file.download(file_path)
    new_file_path = file_path + ".wav"
    wav_cmd = (
        'ffmpeg -y -i "'
        + file_path
        + '" -ar 48000 -ac 1 "'
        + new_file_path
        + '"'
    )
    subprocess.call(wav_cmd, shell=True)
    r_file = sr.AudioFile(new_file_path)
    with r_file as source:
        audio = r.record(source)
    recognized_text = r.recognize_google(
        audio, language=VIDEO_TRANSCRIBE_LANGUAGE
    )
    now = datetime.now()
    message = '"{recognized_text}" on {date} at {time}'.format(
        recognized_text=recognized_text,
        date=now.strftime("%d.%m.%Y"),
        time=now.strftime("%H:%M"),
    )
    update.message.reply_text(message)
    due = {
        "date": (datetime.today() + timedelta(days=1)).strftime(
            "%Y-%m-%d"
        ),
        "is_recurring": False,
        "lang": "en",
        "string": "tomorrow",
        "timezone": None,
    }
    item = TODOIST_API.items.add(message, project_id=2281154095, due=due)
    TODOIST_API.reminders.add(item["id"], due=due)

    logger.info(TODOIST_API.queue)
    TODOIST_API.commit()
    os.remove(file_path)
    os.remove(new_file_path)


def voice_to_text(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        update.message.reply_text("Nah")
        return
    TODOIST_API.sync()
    file_name = (
        str(update.message.chat_id)
        + "_"
        + str(update.message.from_user.id)
        + str(update.message.message_id)
        + ".ogg"
    )
    update.message.voice.get_file().download(file_name)
    file_path = os.path.abspath(file_name)
    print(file_path)

    modification_date = datetime.fromtimestamp(
        os.path.getmtime(file_path)
    ).strftime("%d.%m.%Y %H:%M")
    wav_converted_file_path = file_path + ".wav"
    wav_cmd = (
        'ffmpeg -i "'
        + file_path
        + '" -ar 48000 "'
        + wav_converted_file_path
        + '"'
    )
    subprocess.call(wav_cmd, shell=True)
    r_file = sr.AudioFile(wav_converted_file_path)
    with r_file as source:
        audio = r.record(source)
    recognized_text = r.recognize_google(audio, language="de-DE")
    if "absatz" in recognized_text.lower():
        phrases = recognized_text.lower().split("absatz")
        for phrase in phrases:
            final_message = modification_date + " : " + phrase
            update.message.reply_text(final_message)
            add_to_todoist(final_message, wav_converted_file_path)
    else:
        final_message = modification_date + " : " + recognized_text
        update.message.reply_text(final_message)
        add_to_todoist(final_message, wav_converted_file_path)
    TODOIST_API.commit()
    os.remove(file_name)
    os.remove(wav_converted_file_path)


def add_to_todoist(final_message, file_path):
    item = TODOIST_API.items.add(final_message)
    upload_file_to_todoist(item, file_path)


def upload_file_to_todoist(item, file_path):
    attachement = TODOIST_API.uploads.add(file_path)
    note = TODOIST_API.notes.add(
        item["id"], content="", file_attachment=attachement
    )
