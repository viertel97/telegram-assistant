import os
import re
import sys
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from loguru import logger
from telegram import Update
from telegram.ext import CallbackContext

from helper.config_helper import CHAT_ID, is_not_correct_chat_id
from services.notion_service import TODOIST_API

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)

if os.name == "nt":
    DEBUG = True
else:
    DEBUG = False
logger.info("DEBUG MODE: " + str(DEBUG))

TELEGRAM_MAX_MESSAGE_LENGTH = 4096

INPUT_HTML_FILENAME = "temp.html"
INPUT_PDF_FILENAME = "temp.pdf"

LAST_FILE_INFORMATION_FILE = "last_file_information.json"
_RE_COMBINE_WHITESPACE = re.compile(r"\s+")


def clean_up_soup(soup_clean):
    soup_clean = re.sub(r"(.)(\s)(\,|\.|\;|\:|\—|\-|\–|\!|\?)", r"\1\3", soup_clean)
    soup_clean = re.sub(r"(.)(\s)(\,|\.|\;|\:|\—|\-|\–|\!|\?)", r"\1\3", soup_clean)
    soup_clean = re.sub(r"(\«|\‘|\“|\'|\")(\s)(.)", r"\1\3", soup_clean)
    soup_clean = soup_clean.replace("\n", "")
    soup_clean = _RE_COMBINE_WHITESPACE.sub(" ", soup_clean).strip()
    return soup_clean.strip()


def write_notes(book_title, diluted_soup):
    incoming_own_note = False

    big_string = "# " + book_title.strip() + "\n"
    for item in diluted_soup:
        item_class = item["class"][0]
        if item_class == "sectionHeading":
            temp = clean_up_soup(item.contents[0])
            big_string += "#### " + temp + "\n"

        elif item_class == "noteText":
            if incoming_own_note:
                # big_string = big_string[:-1]
                big_string += "> " + clean_up_soup(item.string)
                incoming_own_note = False
            else:
                big_string += "" + clean_up_soup(item.string)
            big_string += "\n"

        elif item_class == "noteHeading":
            note_heading_string = item.get_text(" ", strip=True)
            if "Note" in note_heading_string:
                incoming_own_note = True
            else:
                pages = re.compile(r"Page [0-9]+|Location [0-9]+")
                page_numbers = pages.findall(note_heading_string)
                big_string += "##### " + " - ".join(page_numbers) + ":\n"
    return big_string


def kindle_2_md(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        update.message.reply_text("Nah")
        return
    TODOIST_API.sync()
    file_id = update.message.document.file_id
    logger.info(update.message.document.file_name)
    file = context.bot.get_file(file_id)
    file.download(os.path.join(sys.path[0], INPUT_HTML_FILENAME))
    soup = BeautifulSoup(
        open(
            os.path.join(
                sys.path[0],
                INPUT_HTML_FILENAME,
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
    valid_filename = re.sub("[^a-zA-Z0-9\\.\\-]", "_", book_title) + ".md"
    with open(valid_filename, "w+", encoding="utf-8") as text_file:
        text_file.write(big_string)
    context.bot.sendDocument(
        chat_id=CHAT_ID, caption="Kindle-Notizen: " + book_title, document=open(valid_filename, "rb")
    )
    add_book_rework_to_todoist(book_title)
    if not DEBUG:
        TODOIST_API.commit()
        os.remove(os.path.join(sys.path[0], INPUT_HTML_FILENAME))


def add_book_rework_to_todoist(book_title):
    due = {
        "date": (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "is_recurring": False,
        "lang": "en",
        "string": "tomorrow",
        "timezone": None,
    }
    item = TODOIST_API.items.add(
        '"{book_title}"-eBook nacharbeiten'.format(book_title=book_title),
        project_id=2281154095,
        due=due,
    )
    TODOIST_API.reminders.add(item["id"], due=due)

    item = TODOIST_API.items.add(
        "eBook-Variablen in Tasker zurücksetzen bzw. durch nächstes Buch ersetzen",
        project_id=2281154095,
        due={"string": "today"},
    )
    TODOIST_API.reminders.add(item["id"], due=due)

    logger.info(TODOIST_API.queue)
