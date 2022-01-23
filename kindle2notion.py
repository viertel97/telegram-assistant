import os
import re
import sys
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from loguru import logger
from telegram import Update
from telegram.ext import CallbackContext

from apis import TODOIST_API
from helper import is_not_correct_chat_id

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)

TELEGRAM_MAX_MESSAGE_LENGTH = 4096

FILENAME = "temp.html"


def clean_up_soup(soup_clean):
    soup_clean = re.sub(r"(.)(\s)(\,|\.|\;|\:|\—|\-|\–|\!|\?)", r"\1\3", soup_clean)
    soup_clean = re.sub(r"(.)(\s)(\,|\.|\;|\:|\—|\-|\–|\!|\?)", r"\1\3", soup_clean)
    soup_clean = re.sub(r"(\«|\‘|\“|\'|\")(\s)(.)", r"\1\3", soup_clean)
    return soup_clean.replace("\n", "")


def write_notes(book_title, diluted_soup):
    big_string = "# " + book_title + "\n\n"
    for item in diluted_soup:
        if item["class"][0] == "sectionHeading":
            temp = clean_up_soup(item.contents[0])
            big_string += "#### " + temp + "\n"
        elif item["class"][0] == "noteText":
            big_string += "> " + clean_up_soup(item.string) + "\n\n\n---\n"
        elif item["class"][0] == "noteHeading":
            note_heading_string = item.get_text(" ", strip=True)
            pages = re.compile(r"Page [0-9]+|Location [0-9]+")
            page_numbers = pages.findall(note_heading_string)
            big_string += " - ".join(page_numbers) + ":\n\n"
    return big_string


def kindle_2_md(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        update.message.reply_text("Nah")
        return
    file_id = update.message.document.file_id
    logger.info(update.message.document.file_name)
    file = context.bot.get_file(file_id)
    file.download(os.path.join(sys.path[0], FILENAME))
    soup = BeautifulSoup(
        open(
            os.path.join(
                sys.path[0],
                FILENAME,
            ),
            "r",
            encoding="utf-8",
        ),
        "html.parser",
    )
    book_title = re.sub("\n|\r", "", soup.find(True, {"class": ["bookTitle"]}).contents[0])
    logger.info(book_title)
    diluted_soup = soup.find_all(True, {"class": ["sectionHeading", "noteHeading", "noteText"]})
    big_string = write_notes(book_title, diluted_soup)
    message_length = len(big_string)
    if message_length > TELEGRAM_MAX_MESSAGE_LENGTH:
        n = TELEGRAM_MAX_MESSAGE_LENGTH
        splitted_message = [big_string[i : i + n] for i in range(0, len(big_string), n)]
        for message in splitted_message:
            update.message.reply_text(message)

    else:
        update.message.reply_text(big_string)
    due = {
        "date": (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "is_recurring": False,
        "lang": "en",
        "string": "tomorrow",
        "timezone": None,
    }
    TODOIST_API.items.add(
        '"{book_title}"-eBook nacharbeiten'.format(book_title=book_title), project_id=2281154095, due=due
    )
    TODOIST_API.items.add(
        "eBook-Variablen in Tasker zurücksetzen bzw. durch nächstes Buch ersetzen",
        project_id=2281154095,
        due={"string": "today"},
    )
    logger.info(TODOIST_API.queue)
    TODOIST_API.commit()
    os.remove(os.path.join(sys.path[0], FILENAME))
