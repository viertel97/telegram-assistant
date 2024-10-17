import re
from datetime import datetime

import requests
from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import CallbackContext

from helper.config_helper import is_not_correct_chat_id
from services.microsoft_service import get_file_list, get_access_token
from services.whisper_service import transcribe

logger = setup_logging(__file__)


async def handle_text(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return
    await update.message.reply_text("start handle_text")
    text = update.message.text
    try:
        file_info = extract_info(text)
        await update.message.reply_text(str(file_info))
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error")
        return
    token = get_access_token()
    files = get_file_list("Anwendungen/Call Recorder - SKVALEX", token)
    file = find_file(files, file_info["file_name"])
    if not file:
        await update.message.reply_text("File not found")
        return
    else:
        await update.message.reply_text("File found")
    with open("input.wav", "wb") as f:
        f.write(requests.get(file["@microsoft.graph.downloadUrl"]).content)
    await update.message.reply_text("done downloading - start transcribing")
    with open("input.wav", "rb") as f:
        await transcribe(f, file["name"], file_info['segment_counter'], update)


def find_file(file_list, file_name):
    for file in file_list[0]["value"]:
        if "@microsoft.graph.downloadUrl" in file.keys():
            if file_name in file["name"]:
                return file
    return None


def extract_info(log_string):
    # Extract date (first 12 digits)
    date_str = log_string[:12]
    if "@" in log_string:
        filename = log_string.split("@")[0]
        segment_counter = int(log_string.split("@")[1])
    else:
        filename = log_string
        segment_counter = 1
    date = datetime.strptime(date_str, "%Y%m%d%H%M")

    # Extract incoming/outgoing type
    call_type = "outgoing" if "outgoing" in log_string else "incoming"

    # Extract contact name (inside first set of brackets)
    name_match = re.search(r"\[(.*?)\]", log_string)
    contact_name = name_match.group(1) if name_match else None

    # Extract contact number (inside second set of brackets)
    number_match = re.findall(r"\[(.*?)\]", log_string)
    contact_number = number_match[-1] if len(number_match) > 1 else None

    return {
        "date": date,
        "call_type": call_type,
        "contact_name": contact_name,
        "contact_number": contact_number,
        "segment_counter": segment_counter,
        "file_name": filename,
    }
