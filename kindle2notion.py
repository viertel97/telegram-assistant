import json
import os
import re
import sys
from datetime import datetime, timedelta

import fitz
from bs4 import BeautifulSoup
from dateutil import parser
from loguru import logger
from telegram import Update
from telegram.ext import CallbackContext

from apis import TODOIST_API
from helper import CHAT_ID, is_not_correct_chat_id

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)

if os.name == "nt":
    DEBUG = False
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
    if not DEBUG:
        os.remove(os.path.join(sys.path[0], INPUT_HTML_FILENAME))
        # os.remove(os.path.join(sys.path[0], valid_filename))
    set_last_infos(valid_filename)


def set_last_infos(file_name):
    dict_to_save = {"file_name": file_name, "timestamp": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}
    with open(LAST_FILE_INFORMATION_FILE, "w", encoding="utf-8") as f:
        json.dump([dict_to_save], f, ensure_ascii=False, indent=4)


def get_last_infos():
    with open(LAST_FILE_INFORMATION_FILE, encoding="utf-8") as data_file:
        data = json.loads(data_file.read())
    return data[0]


def add_book_rework_to_todoist(book_title):
    due = {
        "date": (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "is_recurring": False,
        "lang": "en",
        "string": "tomorrow",
        "timezone": None,
    }
    TODOIST_API.items.add(
        '"{book_title}"-eBook nacharbeiten'.format(book_title=book_title),
        project_id=2281154095,
        due=due,
    )
    TODOIST_API.items.add(
        "eBook-Variablen in Tasker zurücksetzen bzw. durch nächstes Buch ersetzen",
        project_id=2281154095,
        due={"string": "today"},
    )
    logger.info(TODOIST_API.queue)


def do_highlighting(md_file_lines, pdf_file_name):
    doc = fitz.open(INPUT_PDF_FILENAME)
    single_word_annotation_list = []
    for line in md_file_lines:
        if line.startswith("#"):
            continue
        elif line.startswith("####"):
            continue
        elif line.startswith("#####"):
            continue
        elif line.startswith(">"):
            continue
        else:
            highlight(doc, line.strip(), single_word_annotation_list)
    doc.save(pdf_file_name, garbage=4, deflate=True, clean=True)


def annotate_pdf(update: Update, context: CallbackContext):
    last_infos = get_last_infos()
    if (
        is_not_correct_chat_id(update.message.chat_id)
        or (datetime.now() - parser.parse(last_infos["timestamp"])).seconds > 360
    ):
        update.message.reply_text("Nah")
        return
    else:
        update.message.reply_text("Could take a while")
    file_id = update.message.document.file_id
    logger.info(update.message.document.file_name)
    file = context.bot.get_file(file_id)
    file.download(os.path.join(sys.path[0], INPUT_PDF_FILENAME))
    with open(last_infos["file_name"], encoding="utf-8") as f:
        md_file_lines = f.readlines()

    pdf_file_name = last_infos["file_name"][:-3] + ".pdf"
    do_highlighting(md_file_lines, pdf_file_name)

    add_book_rework_to_todoist(last_infos["file_name"][:-3])

    if not DEBUG:
        TODOIST_API.commit()
        context.bot.sendDocument(
            chat_id=CHAT_ID, caption="Updated PDF", document=open(os.path.join(sys.path[0], pdf_file_name), "rb")
        )
        os.remove(os.path.join(sys.path[0], pdf_file_name))
        os.remove(os.path.join(sys.path[0], INPUT_PDF_FILENAME))
        os.remove(os.path.join(sys.path[0], last_infos["file_name"]))


def highlight(doc, text, single_word_annotation_list):
    for page in doc:
        text_instances = page.search_for(text, quads=True)
        if len(text_instances) > 0:
            if text not in single_word_annotation_list:
                highlight = page.add_highlight_annot(text_instances)
                highlight.update()
            if text.count(" ") == 0:
                single_word_annotation_list.append(text)
