import os

import speech_recognition as sr
import todoist
from loguru import logger
from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

import bht
import helper
import kindle2notion
import transcriber
import wol

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

if os.name == "nt":
    bat_habit_file_path = "bad_habit.json"
    windows = True
else:
    bat_habit_file_path = "/home/pi/python/bad_habit.json"


logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def start(update: Update, context: CallbackContext):
    update.message.reply_text(text="Do Stuff.")


def add_bht_handler(list, dispatcher):
    for command in list:
        temp_handler = CommandHandler(str("bht_" + command), bht.bht)
        dispatcher.add_handler(temp_handler)


def main():

    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    start_handler = CommandHandler(str("start"), start)
    wol_handler = CommandHandler(str("wol"), wol.wol)

    bht_config = helper.get_config("bad_habit_config.json")
    bad_habit_list = [x["bad_habit"] for x in bht_config]
    add_bht_handler(bad_habit_list, dispatcher)

    oh_handler = MessageHandler(Filters.voice, transcriber.voice_to_text)
    dispatcher.add_handler(oh_handler)

    audiobook_to_notion_handler = MessageHandler(Filters.video, transcriber.video_to_text)
    dispatcher.add_handler(audiobook_to_notion_handler)

    k2md = MessageHandler(Filters.document, kindle2notion.kindle_2_md)
    change_language_handler = CommandHandler(str("change_language"), transcriber.change_video_language)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(wol_handler)
    dispatcher.add_handler(k2md)
    dispatcher.add_handler(change_language_handler)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()